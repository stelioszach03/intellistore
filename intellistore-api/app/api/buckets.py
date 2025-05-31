"""
Bucket management API endpoints
"""

import time
from typing import List, Optional, Dict, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from app.api.auth import get_current_user, UserInfo
from app.services.raft_service import RaftService
from app.services.kafka_service import KafkaService

router = APIRouter()
logger = structlog.get_logger(__name__)


class BucketCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=63, pattern=r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$')
    description: Optional[str] = Field(None, max_length=500)
    acl: Optional[Dict[str, str]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)


class BucketResponse(BaseModel):
    name: str
    owner: str
    description: Optional[str]
    created_at: str
    object_count: int
    total_size: int
    hot_objects: int
    cold_objects: int
    acl: Dict[str, str]
    metadata: Dict[str, str]


class BucketListResponse(BaseModel):
    buckets: List[BucketResponse]
    total_count: int


class BucketUpdateRequest(BaseModel):
    description: Optional[str] = None
    acl: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, str]] = None


def get_raft_service(request: Request) -> RaftService:
    """Get Raft service from app state"""
    return request.app.state.raft_service


def get_kafka_service(request: Request) -> KafkaService:
    """Get Kafka service from app state"""
    return request.app.state.kafka_service


@router.post("", response_model=BucketResponse, status_code=status.HTTP_201_CREATED)
async def create_bucket(
    bucket_request: BucketCreateRequest,
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service),
    kafka_service: KafkaService = Depends(get_kafka_service)
):
    """Create a new bucket"""
    logger.info("Creating bucket", bucket_name=bucket_request.name, user=current_user.username)
    
    try:
        # Check if bucket already exists
        existing_bucket = await raft_service.get_bucket(bucket_request.name)
        if existing_bucket:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bucket '{bucket_request.name}' already exists"
            )
        
        # Prepare bucket data
        bucket_data = {
            "name": bucket_request.name,
            "owner": current_user.username,
            "description": bucket_request.description,
            "acl": bucket_request.acl or {current_user.username: "admin"},
            "metadata": bucket_request.metadata or {}
        }
        
        # Create bucket in Raft metadata store
        result = await raft_service.create_bucket(bucket_data)
        
        # Log access event to Kafka
        access_event = {
            "timestamp": time.time(),
            "user": current_user.username,
            "action": "create_bucket",
            "bucket": bucket_request.name,
            "success": True,
            "metadata": {
                "description": bucket_request.description,
                "acl_users": list(bucket_request.acl.keys()) if bucket_request.acl else []
            }
        }
        await kafka_service.publish_access_log(access_event)
        
        logger.info("Bucket created successfully", bucket_name=bucket_request.name)
        
        return BucketResponse(
            name=bucket_request.name,
            owner=current_user.username,
            description=bucket_request.description,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            object_count=0,
            total_size=0,
            hot_objects=0,
            cold_objects=0,
            acl=bucket_data["acl"],
            metadata=bucket_data["metadata"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create bucket", bucket_name=bucket_request.name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bucket"
        )


@router.get("", response_model=BucketListResponse)
async def list_buckets(
    limit: int = 100,
    offset: int = 0,
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service)
):
    """List buckets accessible to the current user"""
    logger.info("Listing buckets", user=current_user.username, limit=limit, offset=offset)
    
    try:
        # Get all buckets from Raft metadata store
        all_buckets = await raft_service.list_buckets()
        
        # Filter buckets based on user permissions
        accessible_buckets = []
        for bucket in all_buckets:
            # Check if user has access to this bucket
            if (bucket.get("owner") == current_user.username or 
                current_user.username in bucket.get("acl", {}) or
                "admin" in current_user.roles):
                
                # Get bucket statistics
                stats = await raft_service.get_bucket_stats(bucket["name"])
                
                accessible_buckets.append(BucketResponse(
                    name=bucket["name"],
                    owner=bucket["owner"],
                    description=bucket.get("description"),
                    created_at=bucket.get("created_at", ""),
                    object_count=stats.get("object_count", 0),
                    total_size=stats.get("total_size", 0),
                    hot_objects=stats.get("hot_objects", 0),
                    cold_objects=stats.get("cold_objects", 0),
                    acl=bucket.get("acl", {}),
                    metadata=bucket.get("metadata", {})
                ))
        
        # Apply pagination
        paginated_buckets = accessible_buckets[offset:offset + limit]
        
        return BucketListResponse(
            buckets=paginated_buckets,
            total_count=len(accessible_buckets)
        )
        
    except Exception as e:
        logger.error("Failed to list buckets", user=current_user.username, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list buckets"
        )


@router.get("/{bucket_name}", response_model=BucketResponse)
async def get_bucket(
    bucket_name: str,
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service)
):
    """Get bucket information"""
    logger.info("Getting bucket info", bucket_name=bucket_name, user=current_user.username)
    
    try:
        # Get bucket from Raft metadata store
        bucket = await raft_service.get_bucket(bucket_name)
        if not bucket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{bucket_name}' not found"
            )
        
        # Check permissions
        if (bucket.get("owner") != current_user.username and 
            current_user.username not in bucket.get("acl", {}) and
            "admin" not in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this bucket"
            )
        
        # Get bucket statistics
        stats = await raft_service.get_bucket_stats(bucket_name)
        
        return BucketResponse(
            name=bucket["name"],
            owner=bucket["owner"],
            description=bucket.get("description"),
            created_at=bucket.get("created_at", ""),
            object_count=stats.get("object_count", 0),
            total_size=stats.get("total_size", 0),
            hot_objects=stats.get("hot_objects", 0),
            cold_objects=stats.get("cold_objects", 0),
            acl=bucket.get("acl", {}),
            metadata=bucket.get("metadata", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get bucket", bucket_name=bucket_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bucket information"
        )


@router.patch("/{bucket_name}", response_model=BucketResponse)
async def update_bucket(
    bucket_name: str,
    update_request: BucketUpdateRequest,
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service),
    kafka_service: KafkaService = Depends(get_kafka_service)
):
    """Update bucket metadata"""
    logger.info("Updating bucket", bucket_name=bucket_name, user=current_user.username)
    
    try:
        # Get existing bucket
        bucket = await raft_service.get_bucket(bucket_name)
        if not bucket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{bucket_name}' not found"
            )
        
        # Check permissions (only owner or admin can update)
        if (bucket.get("owner") != current_user.username and 
            "admin" not in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only bucket owner or admin can update bucket"
            )
        
        # Prepare update data
        update_data = {}
        if update_request.description is not None:
            update_data["description"] = update_request.description
        if update_request.acl is not None:
            update_data["acl"] = update_request.acl
        if update_request.metadata is not None:
            update_data["metadata"] = update_request.metadata
        
        # Update bucket in Raft metadata store
        await raft_service.update_bucket(bucket_name, update_data)
        
        # Log access event
        access_event = {
            "timestamp": time.time(),
            "user": current_user.username,
            "action": "update_bucket",
            "bucket": bucket_name,
            "success": True,
            "metadata": update_data
        }
        await kafka_service.publish_access_log(access_event)
        
        # Get updated bucket info
        updated_bucket = await raft_service.get_bucket(bucket_name)
        stats = await raft_service.get_bucket_stats(bucket_name)
        
        logger.info("Bucket updated successfully", bucket_name=bucket_name)
        
        return BucketResponse(
            name=updated_bucket["name"],
            owner=updated_bucket["owner"],
            description=updated_bucket.get("description"),
            created_at=updated_bucket.get("created_at", ""),
            object_count=stats.get("object_count", 0),
            total_size=stats.get("total_size", 0),
            hot_objects=stats.get("hot_objects", 0),
            cold_objects=stats.get("cold_objects", 0),
            acl=updated_bucket.get("acl", {}),
            metadata=updated_bucket.get("metadata", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update bucket", bucket_name=bucket_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bucket"
        )


@router.delete("/{bucket_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bucket(
    bucket_name: str,
    force: bool = False,
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service),
    kafka_service: KafkaService = Depends(get_kafka_service)
):
    """Delete a bucket"""
    logger.info("Deleting bucket", bucket_name=bucket_name, user=current_user.username, force=force)
    
    try:
        # Get bucket
        bucket = await raft_service.get_bucket(bucket_name)
        if not bucket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{bucket_name}' not found"
            )
        
        # Check permissions (only owner or admin can delete)
        if (bucket.get("owner") != current_user.username and 
            "admin" not in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only bucket owner or admin can delete bucket"
            )
        
        # Check if bucket is empty (unless force=True)
        if not force:
            stats = await raft_service.get_bucket_stats(bucket_name)
            if stats.get("object_count", 0) > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Bucket is not empty. Use force=true to delete non-empty bucket"
                )
        
        # Delete bucket from Raft metadata store
        await raft_service.delete_bucket(bucket_name, force=force)
        
        # Log access event
        access_event = {
            "timestamp": time.time(),
            "user": current_user.username,
            "action": "delete_bucket",
            "bucket": bucket_name,
            "success": True,
            "metadata": {"force": force}
        }
        await kafka_service.publish_access_log(access_event)
        
        logger.info("Bucket deleted successfully", bucket_name=bucket_name)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete bucket", bucket_name=bucket_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete bucket"
        )