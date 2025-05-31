"""
Object management API endpoints
"""

import asyncio
import hashlib
import time
from typing import List, Optional, Dict, Any
from io import BytesIO

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.auth import get_current_user, UserInfo
from app.services.raft_service import RaftService
from app.services.kafka_service import KafkaService
from app.services.vault_service import VaultService
from app.services.storage_service import StorageService

router = APIRouter()
logger = structlog.get_logger(__name__)


class ObjectResponse(BaseModel):
    bucket_name: str
    object_key: str
    size: int
    tier: str
    created_at: str
    last_accessed: str
    content_type: str
    checksum: str
    metadata: Dict[str, str]


class ObjectListResponse(BaseModel):
    objects: List[ObjectResponse]
    total_count: int
    continuation_token: Optional[str] = None


class ObjectUploadResponse(BaseModel):
    bucket_name: str
    object_key: str
    size: int
    checksum: str
    tier: str
    shards: List[Dict[str, Any]]
    message: str


class ObjectUpdateRequest(BaseModel):
    tier: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


def get_raft_service(request: Request) -> RaftService:
    """Get Raft service from app state"""
    return request.app.state.raft_service


def get_kafka_service(request: Request) -> KafkaService:
    """Get Kafka service from app state"""
    return request.app.state.kafka_service


def get_vault_service(request: Request) -> VaultService:
    """Get Vault service from app state"""
    return request.app.state.vault_service


async def check_bucket_access(bucket_name: str, user: UserInfo, raft_service: RaftService, required_permission: str = "read"):
    """Check if user has access to bucket"""
    bucket = await raft_service.get_bucket(bucket_name)
    if not bucket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bucket '{bucket_name}' not found"
        )
    
    # Check permissions
    user_permission = bucket.get("acl", {}).get(user.username)
    is_owner = bucket.get("owner") == user.username
    is_admin = "admin" in user.roles
    
    if not (is_owner or is_admin or user_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this bucket"
        )
    
    # Check specific permission level
    if required_permission == "write" and not (is_owner or is_admin or user_permission in ["write", "admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied to this bucket"
        )
    
    return bucket


@router.post("/{bucket_name}/objects", response_model=ObjectUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_object(
    bucket_name: str,
    object_key: str = Form(...),
    tier: str = Form(default="hot"),
    content_type: str = Form(default="application/octet-stream"),
    metadata: str = Form(default="{}"),
    file: UploadFile = File(...),
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service),
    kafka_service: KafkaService = Depends(get_kafka_service),
    vault_service: VaultService = Depends(get_vault_service)
):
    """Upload an object to a bucket"""
    logger.info("Starting object upload", 
                bucket_name=bucket_name, 
                object_key=object_key, 
                user=current_user.username,
                tier=tier,
                content_type=content_type)
    
    try:
        # Check bucket access
        await check_bucket_access(bucket_name, current_user, raft_service, "write")
        
        # Parse metadata
        import json
        try:
            object_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            object_metadata = {}
        
        # Read file data
        file_data = await file.read()
        file_size = len(file_data)
        
        # Calculate checksum
        checksum = hashlib.sha256(file_data).hexdigest()
        
        logger.info("File read successfully", 
                   object_key=object_key, 
                   size=file_size, 
                   checksum=checksum)
        
        # Get encryption key from Vault
        encryption_key = await vault_service.get_data_key(bucket_name, object_key)
        
        # Encrypt data
        encrypted_data = await vault_service.encrypt_data(file_data, encryption_key)
        
        # Create storage service instance
        storage_service = StorageService(raft_service)
        
        # Encode data into shards using Reed-Solomon
        shards_info = await storage_service.encode_and_store_shards(
            bucket_name=bucket_name,
            object_key=object_key,
            data=encrypted_data,
            tier=tier
        )
        
        # Create object metadata
        object_data = {
            "bucket_name": bucket_name,
            "object_key": object_key,
            "size": file_size,
            "tier": tier,
            "content_type": content_type,
            "checksum": checksum,
            "encryption_key": encryption_key,
            "shards": shards_info,
            "metadata": object_metadata,
            "owner": current_user.username
        }
        
        # Store metadata in Raft
        await raft_service.create_object(object_data)
        
        # Log access event to Kafka
        access_event = {
            "timestamp": time.time(),
            "user": current_user.username,
            "action": "upload_object",
            "bucket": bucket_name,
            "object": object_key,
            "size": file_size,
            "tier": tier,
            "success": True,
            "metadata": {
                "content_type": content_type,
                "checksum": checksum,
                "shard_count": len(shards_info)
            }
        }
        await kafka_service.publish_access_log(access_event)
        
        # Trigger ML tiering analysis
        tiering_event = {
            "timestamp": time.time(),
            "bucket_name": bucket_name,
            "object_key": object_key,
            "size": file_size,
            "current_tier": tier,
            "user": current_user.username,
            "content_type": content_type
        }
        await kafka_service.publish_tiering_request(tiering_event)
        
        logger.info("Object uploaded successfully", 
                   bucket_name=bucket_name, 
                   object_key=object_key,
                   size=file_size,
                   shards=len(shards_info))
        
        return ObjectUploadResponse(
            bucket_name=bucket_name,
            object_key=object_key,
            size=file_size,
            checksum=checksum,
            tier=tier,
            shards=shards_info,
            message="Object uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload object", 
                    bucket_name=bucket_name, 
                    object_key=object_key, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload object"
        )


@router.get("/{bucket_name}/objects/{object_key}")
async def download_object(
    bucket_name: str,
    object_key: str,
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service),
    kafka_service: KafkaService = Depends(get_kafka_service),
    vault_service: VaultService = Depends(get_vault_service)
):
    """Download an object from a bucket"""
    logger.info("Starting object download", 
                bucket_name=bucket_name, 
                object_key=object_key, 
                user=current_user.username)
    
    try:
        # Check bucket access
        await check_bucket_access(bucket_name, current_user, raft_service, "read")
        
        # Get object metadata
        object_metadata = await raft_service.get_object(bucket_name, object_key)
        if not object_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object '{object_key}' not found in bucket '{bucket_name}'"
            )
        
        # Create storage service instance
        storage_service = StorageService(raft_service)
        
        # Retrieve and reconstruct shards
        encrypted_data = await storage_service.retrieve_and_reconstruct_shards(
            bucket_name=bucket_name,
            object_key=object_key,
            shards_info=object_metadata["shards"]
        )
        
        # Decrypt data
        decrypted_data = await vault_service.decrypt_data(
            encrypted_data, 
            object_metadata["encryption_key"]
        )
        
        # Update last accessed time
        await raft_service.update_object_access_time(bucket_name, object_key)
        
        # Log access event
        access_event = {
            "timestamp": time.time(),
            "user": current_user.username,
            "action": "download_object",
            "bucket": bucket_name,
            "object": object_key,
            "size": object_metadata["size"],
            "tier": object_metadata["tier"],
            "success": True
        }
        await kafka_service.publish_access_log(access_event)
        
        logger.info("Object downloaded successfully", 
                   bucket_name=bucket_name, 
                   object_key=object_key,
                   size=len(decrypted_data))
        
        # Return streaming response
        def generate():
            yield decrypted_data
        
        return StreamingResponse(
            generate(),
            media_type=object_metadata.get("content_type", "application/octet-stream"),
            headers={
                "Content-Disposition": f"attachment; filename={object_key}",
                "Content-Length": str(object_metadata["size"]),
                "X-Object-Tier": object_metadata["tier"],
                "X-Object-Checksum": object_metadata["checksum"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download object", 
                    bucket_name=bucket_name, 
                    object_key=object_key, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download object"
        )


@router.get("/{bucket_name}/objects", response_model=ObjectListResponse)
async def list_objects(
    bucket_name: str,
    prefix: Optional[str] = None,
    limit: int = 100,
    continuation_token: Optional[str] = None,
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service)
):
    """List objects in a bucket"""
    logger.info("Listing objects", 
                bucket_name=bucket_name, 
                user=current_user.username,
                prefix=prefix,
                limit=limit)
    
    try:
        # Check bucket access
        await check_bucket_access(bucket_name, current_user, raft_service, "read")
        
        # Get objects from Raft metadata store
        objects_data = await raft_service.list_objects(
            bucket_name=bucket_name,
            prefix=prefix,
            limit=limit,
            continuation_token=continuation_token
        )
        
        objects = []
        for obj_data in objects_data.get("objects", []):
            objects.append(ObjectResponse(
                bucket_name=obj_data["bucket_name"],
                object_key=obj_data["object_key"],
                size=obj_data["size"],
                tier=obj_data["tier"],
                created_at=obj_data.get("created_at", ""),
                last_accessed=obj_data.get("last_accessed", ""),
                content_type=obj_data.get("content_type", "application/octet-stream"),
                checksum=obj_data["checksum"],
                metadata=obj_data.get("metadata", {})
            ))
        
        return ObjectListResponse(
            objects=objects,
            total_count=objects_data.get("total_count", len(objects)),
            continuation_token=objects_data.get("next_continuation_token")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list objects", 
                    bucket_name=bucket_name, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list objects"
        )


@router.get("/{bucket_name}/objects/{object_key}/info", response_model=ObjectResponse)
async def get_object_info(
    bucket_name: str,
    object_key: str,
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service)
):
    """Get object metadata"""
    logger.info("Getting object info", 
                bucket_name=bucket_name, 
                object_key=object_key, 
                user=current_user.username)
    
    try:
        # Check bucket access
        await check_bucket_access(bucket_name, current_user, raft_service, "read")
        
        # Get object metadata
        object_metadata = await raft_service.get_object(bucket_name, object_key)
        if not object_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object '{object_key}' not found in bucket '{bucket_name}'"
            )
        
        return ObjectResponse(
            bucket_name=object_metadata["bucket_name"],
            object_key=object_metadata["object_key"],
            size=object_metadata["size"],
            tier=object_metadata["tier"],
            created_at=object_metadata.get("created_at", ""),
            last_accessed=object_metadata.get("last_accessed", ""),
            content_type=object_metadata.get("content_type", "application/octet-stream"),
            checksum=object_metadata["checksum"],
            metadata=object_metadata.get("metadata", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get object info", 
                    bucket_name=bucket_name, 
                    object_key=object_key, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get object information"
        )


@router.patch("/{bucket_name}/objects/{object_key}", response_model=ObjectResponse)
async def update_object(
    bucket_name: str,
    object_key: str,
    update_request: ObjectUpdateRequest,
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service),
    kafka_service: KafkaService = Depends(get_kafka_service)
):
    """Update object metadata or tier"""
    logger.info("Updating object", 
                bucket_name=bucket_name, 
                object_key=object_key, 
                user=current_user.username)
    
    try:
        # Check bucket access
        await check_bucket_access(bucket_name, current_user, raft_service, "write")
        
        # Get existing object
        object_metadata = await raft_service.get_object(bucket_name, object_key)
        if not object_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object '{object_key}' not found in bucket '{bucket_name}'"
            )
        
        # Prepare update data
        update_data = {}
        if update_request.tier is not None:
            update_data["tier"] = update_request.tier
        if update_request.metadata is not None:
            update_data["metadata"] = update_request.metadata
        
        # Update object in Raft metadata store
        await raft_service.update_object(bucket_name, object_key, update_data)
        
        # If tier changed, trigger migration
        if update_request.tier and update_request.tier != object_metadata["tier"]:
            migration_event = {
                "timestamp": time.time(),
                "bucket_name": bucket_name,
                "object_key": object_key,
                "from_tier": object_metadata["tier"],
                "to_tier": update_request.tier,
                "user": current_user.username,
                "size": object_metadata["size"]
            }
            await kafka_service.publish_tier_migration_request(migration_event)
        
        # Log access event
        access_event = {
            "timestamp": time.time(),
            "user": current_user.username,
            "action": "update_object",
            "bucket": bucket_name,
            "object": object_key,
            "success": True,
            "metadata": update_data
        }
        await kafka_service.publish_access_log(access_event)
        
        # Get updated object info
        updated_object = await raft_service.get_object(bucket_name, object_key)
        
        logger.info("Object updated successfully", 
                   bucket_name=bucket_name, 
                   object_key=object_key)
        
        return ObjectResponse(
            bucket_name=updated_object["bucket_name"],
            object_key=updated_object["object_key"],
            size=updated_object["size"],
            tier=updated_object["tier"],
            created_at=updated_object.get("created_at", ""),
            last_accessed=updated_object.get("last_accessed", ""),
            content_type=updated_object.get("content_type", "application/octet-stream"),
            checksum=updated_object["checksum"],
            metadata=updated_object.get("metadata", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update object", 
                    bucket_name=bucket_name, 
                    object_key=object_key, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update object"
        )


@router.delete("/{bucket_name}/objects/{object_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    bucket_name: str,
    object_key: str,
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service),
    kafka_service: KafkaService = Depends(get_kafka_service)
):
    """Delete an object from a bucket"""
    logger.info("Deleting object", 
                bucket_name=bucket_name, 
                object_key=object_key, 
                user=current_user.username)
    
    try:
        # Check bucket access
        await check_bucket_access(bucket_name, current_user, raft_service, "write")
        
        # Get object metadata
        object_metadata = await raft_service.get_object(bucket_name, object_key)
        if not object_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object '{object_key}' not found in bucket '{bucket_name}'"
            )
        
        # Create storage service instance
        storage_service = StorageService(raft_service)
        
        # Delete shards from storage nodes
        await storage_service.delete_shards(
            bucket_name=bucket_name,
            object_key=object_key,
            shards_info=object_metadata["shards"]
        )
        
        # Delete object metadata from Raft
        await raft_service.delete_object(bucket_name, object_key)
        
        # Log access event
        access_event = {
            "timestamp": time.time(),
            "user": current_user.username,
            "action": "delete_object",
            "bucket": bucket_name,
            "object": object_key,
            "size": object_metadata["size"],
            "tier": object_metadata["tier"],
            "success": True
        }
        await kafka_service.publish_access_log(access_event)
        
        logger.info("Object deleted successfully", 
                   bucket_name=bucket_name, 
                   object_key=object_key)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete object", 
                    bucket_name=bucket_name, 
                    object_key=object_key, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete object"
        )