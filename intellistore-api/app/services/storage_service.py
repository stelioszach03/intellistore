"""
Storage service for managing shards across storage nodes
"""

import asyncio
import hashlib
import io
import time
from typing import Dict, Any, List, Optional, Tuple

import httpx
import structlog

logger = structlog.get_logger(__name__)


class StorageService:
    """Service for managing data storage across storage nodes"""
    
    def __init__(self, raft_service, data_shards: int = 6, parity_shards: int = 3):
        self.raft_service = raft_service
        self.data_shards = data_shards
        self.parity_shards = parity_shards
        self.total_shards = data_shards + parity_shards
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
    
    async def encode_and_store_shards(self, 
                                    bucket_name: str, 
                                    object_key: str, 
                                    data: bytes, 
                                    tier: str = "hot") -> List[Dict[str, Any]]:
        """Encode data into shards and store across storage nodes"""
        try:
            logger.info("Starting shard encoding and storage", 
                       bucket=bucket_name, 
                       object=object_key, 
                       size=len(data),
                       tier=tier)
            
            # Encode data into shards using Reed-Solomon
            shards = await self._encode_data(data)
            
            # Get available storage nodes for the tier
            storage_nodes = await self.raft_service.get_storage_nodes(tier)
            if len(storage_nodes) < self.total_shards:
                raise Exception(f"Insufficient storage nodes: need {self.total_shards}, have {len(storage_nodes)}")
            
            # Store shards across nodes
            shard_infos = []
            tasks = []
            
            for i, shard_data in enumerate(shards):
                node_addr = storage_nodes[i % len(storage_nodes)]
                shard_id = f"{bucket_name}-{object_key}-{i}"
                shard_type = "data" if i < self.data_shards else "parity"
                
                task = self._store_shard(
                    node_addr=node_addr,
                    shard_id=shard_id,
                    bucket_name=bucket_name,
                    object_key=object_key,
                    shard_data=shard_data,
                    shard_type=shard_type,
                    index=i
                )
                tasks.append(task)
            
            # Execute all shard uploads in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for failures
            failed_shards = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_shards.append(i)
                    logger.error("Failed to store shard", 
                               shard_index=i, 
                               error=str(result))
                else:
                    shard_infos.append(result)
            
            # Check if we have enough successful shards
            if len(failed_shards) > self.parity_shards:
                raise Exception(f"Too many shard failures: {len(failed_shards)} failed, can only tolerate {self.parity_shards}")
            
            logger.info("Shards stored successfully", 
                       bucket=bucket_name, 
                       object=object_key,
                       successful_shards=len(shard_infos),
                       failed_shards=len(failed_shards))
            
            return shard_infos
            
        except Exception as e:
            logger.error("Failed to encode and store shards", 
                        bucket=bucket_name, 
                        object=object_key, 
                        error=str(e))
            raise
    
    async def retrieve_and_reconstruct_shards(self, 
                                            bucket_name: str, 
                                            object_key: str, 
                                            shards_info: List[Dict[str, Any]]) -> bytes:
        """Retrieve shards and reconstruct original data"""
        try:
            logger.info("Starting shard retrieval and reconstruction", 
                       bucket=bucket_name, 
                       object=object_key,
                       total_shards=len(shards_info))
            
            # Retrieve shards in parallel
            tasks = []
            for shard_info in shards_info:
                task = self._retrieve_shard(
                    node_addr=shard_info["node_addr"],
                    shard_id=shard_info["shard_id"],
                    bucket_name=bucket_name,
                    object_key=object_key
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect successful shard data
            shard_data = [None] * len(shards_info)
            successful_shards = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning("Failed to retrieve shard", 
                                 shard_index=i, 
                                 shard_id=shards_info[i]["shard_id"],
                                 error=str(result))
                else:
                    shard_data[i] = result
                    successful_shards += 1
            
            # Check if we have enough shards for reconstruction
            if successful_shards < self.data_shards:
                raise Exception(f"Insufficient shards for reconstruction: need {self.data_shards}, have {successful_shards}")
            
            # Reconstruct original data
            reconstructed_data = await self._decode_shards(shard_data)
            
            logger.info("Data reconstructed successfully", 
                       bucket=bucket_name, 
                       object=object_key,
                       reconstructed_size=len(reconstructed_data),
                       shards_used=successful_shards)
            
            return reconstructed_data
            
        except Exception as e:
            logger.error("Failed to retrieve and reconstruct shards", 
                        bucket=bucket_name, 
                        object=object_key, 
                        error=str(e))
            raise
    
    async def delete_shards(self, 
                          bucket_name: str, 
                          object_key: str, 
                          shards_info: List[Dict[str, Any]]):
        """Delete shards from storage nodes"""
        try:
            logger.info("Starting shard deletion", 
                       bucket=bucket_name, 
                       object=object_key,
                       shard_count=len(shards_info))
            
            # Delete shards in parallel
            tasks = []
            for shard_info in shards_info:
                task = self._delete_shard(
                    node_addr=shard_info["node_addr"],
                    shard_id=shard_info["shard_id"],
                    bucket_name=bucket_name,
                    object_key=object_key
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log results
            successful_deletions = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning("Failed to delete shard", 
                                 shard_id=shards_info[i]["shard_id"],
                                 error=str(result))
                else:
                    successful_deletions += 1
            
            logger.info("Shard deletion completed", 
                       bucket=bucket_name, 
                       object=object_key,
                       successful_deletions=successful_deletions,
                       total_shards=len(shards_info))
            
        except Exception as e:
            logger.error("Failed to delete shards", 
                        bucket=bucket_name, 
                        object=object_key, 
                        error=str(e))
            raise
    
    async def migrate_shards(self, 
                           bucket_name: str, 
                           object_key: str, 
                           shards_info: List[Dict[str, Any]], 
                           from_tier: str, 
                           to_tier: str) -> List[Dict[str, Any]]:
        """Migrate shards from one tier to another"""
        try:
            logger.info("Starting shard migration", 
                       bucket=bucket_name, 
                       object=object_key,
                       from_tier=from_tier,
                       to_tier=to_tier)
            
            # Get target storage nodes for the new tier
            target_nodes = await self.raft_service.get_storage_nodes(to_tier)
            if len(target_nodes) < len(shards_info):
                raise Exception(f"Insufficient target nodes: need {len(shards_info)}, have {len(target_nodes)}")
            
            # Retrieve data from source shards
            reconstructed_data = await self.retrieve_and_reconstruct_shards(
                bucket_name, object_key, shards_info
            )
            
            # Store to new tier
            new_shard_infos = await self.encode_and_store_shards(
                bucket_name, object_key, reconstructed_data, to_tier
            )
            
            # Delete old shards
            await self.delete_shards(bucket_name, object_key, shards_info)
            
            logger.info("Shard migration completed", 
                       bucket=bucket_name, 
                       object=object_key,
                       from_tier=from_tier,
                       to_tier=to_tier)
            
            return new_shard_infos
            
        except Exception as e:
            logger.error("Failed to migrate shards", 
                        bucket=bucket_name, 
                        object=object_key, 
                        from_tier=from_tier,
                        to_tier=to_tier,
                        error=str(e))
            raise
    
    async def _encode_data(self, data: bytes) -> List[bytes]:
        """Encode data into Reed-Solomon shards"""
        try:
            # Simple sharding for demo - in production use proper Reed-Solomon
            shard_size = (len(data) + self.data_shards - 1) // self.data_shards
            shards = []
            
            # Create data shards
            for i in range(self.data_shards):
                start = i * shard_size
                end = min(start + shard_size, len(data))
                shard = data[start:end]
                
                # Pad shard to consistent size
                if len(shard) < shard_size:
                    shard += b'\x00' * (shard_size - len(shard))
                
                shards.append(shard)
            
            # Create parity shards (simplified XOR for demo)
            for i in range(self.parity_shards):
                parity_shard = bytearray(shard_size)
                for j in range(self.data_shards):
                    for k in range(shard_size):
                        if k < len(shards[j]):
                            parity_shard[k] ^= shards[j][k]
                shards.append(bytes(parity_shard))
            
            return shards
            
        except Exception as e:
            logger.error("Failed to encode data", error=str(e))
            raise
    
    async def _decode_shards(self, shard_data: List[Optional[bytes]]) -> bytes:
        """Decode shards back to original data"""
        try:
            # Simple reconstruction for demo - in production use proper Reed-Solomon
            available_data_shards = []
            
            for i in range(self.data_shards):
                if i < len(shard_data) and shard_data[i] is not None:
                    available_data_shards.append(shard_data[i])
            
            if len(available_data_shards) < self.data_shards:
                # In a real implementation, we would use parity shards to reconstruct
                # missing data shards. For demo, we'll just concatenate available ones.
                logger.warning("Missing data shards, reconstruction may be incomplete")
            
            # Concatenate data shards
            reconstructed = b''.join(available_data_shards)
            
            # Remove padding
            reconstructed = reconstructed.rstrip(b'\x00')
            
            return reconstructed
            
        except Exception as e:
            logger.error("Failed to decode shards", error=str(e))
            raise
    
    async def _store_shard(self, 
                         node_addr: str, 
                         shard_id: str, 
                         bucket_name: str, 
                         object_key: str, 
                         shard_data: bytes, 
                         shard_type: str, 
                         index: int) -> Dict[str, Any]:
        """Store a single shard on a storage node"""
        try:
            url = f"http://{node_addr}/shard/upload"
            
            # Calculate checksum
            checksum = hashlib.sha256(shard_data).hexdigest()
            
            # Prepare multipart form data
            files = {
                'shard': (f"{shard_id}.shard", io.BytesIO(shard_data), 'application/octet-stream')
            }
            
            data = {
                'shardId': shard_id,
                'bucketName': bucket_name,
                'objectKey': object_key,
                'shardType': shard_type,
                'index': str(index),
                'totalShards': str(self.total_shards)
            }
            
            response = await self.client.post(url, files=files, data=data)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "shard_id": shard_id,
                "node_id": node_addr,
                "node_addr": node_addr,
                "shard_type": shard_type,
                "index": index,
                "size": len(shard_data),
                "checksum": checksum
            }
            
        except Exception as e:
            logger.error("Failed to store shard", 
                        node_addr=node_addr, 
                        shard_id=shard_id, 
                        error=str(e))
            raise
    
    async def _retrieve_shard(self, 
                            node_addr: str, 
                            shard_id: str, 
                            bucket_name: str, 
                            object_key: str) -> bytes:
        """Retrieve a single shard from a storage node"""
        try:
            url = f"http://{node_addr}/shard/download/{shard_id}"
            params = {
                'bucket': bucket_name,
                'object': object_key
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            return response.content
            
        except Exception as e:
            logger.error("Failed to retrieve shard", 
                        node_addr=node_addr, 
                        shard_id=shard_id, 
                        error=str(e))
            raise
    
    async def _delete_shard(self, 
                          node_addr: str, 
                          shard_id: str, 
                          bucket_name: str, 
                          object_key: str):
        """Delete a single shard from a storage node"""
        try:
            url = f"http://{node_addr}/shard/delete/{shard_id}"
            params = {
                'bucket': bucket_name,
                'object': object_key
            }
            
            response = await self.client.delete(url, params=params)
            response.raise_for_status()
            
        except Exception as e:
            logger.error("Failed to delete shard", 
                        node_addr=node_addr, 
                        shard_id=shard_id, 
                        error=str(e))
            raise
    
    async def get_shard_health(self, node_addr: str) -> Dict[str, Any]:
        """Get health status of a storage node"""
        try:
            url = f"http://{node_addr}/health"
            response = await self.client.get(url)
            response.raise_for_status()
            
            return {
                "node_addr": node_addr,
                "status": "healthy",
                "response_time": response.elapsed.total_seconds()
            }
            
        except Exception as e:
            return {
                "node_addr": node_addr,
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def update_object_tier(self, bucket_name: str, object_key: str, new_tier: str) -> bool:
        """Update object tier in metadata"""
        try:
            logger.info("Updating object tier", 
                       bucket=bucket_name, 
                       object=object_key, 
                       new_tier=new_tier)
            
            # Get current metadata
            metadata = await self.get_object_metadata(bucket_name, object_key)
            if not metadata:
                raise Exception("Object not found")
            
            # Update tier in metadata
            metadata["tier"] = new_tier
            metadata["tier_updated_at"] = str(int(time.time()))
            
            # Store updated metadata via Raft
            await self.raft_service.store_object_metadata(bucket_name, object_key, metadata)
            
            logger.info("Object tier updated successfully", 
                       bucket=bucket_name, 
                       object=object_key, 
                       new_tier=new_tier)
            
            return True
            
        except Exception as e:
            logger.error("Failed to update object tier", 
                        bucket=bucket_name, 
                        object=object_key, 
                        new_tier=new_tier, 
                        error=str(e))
            raise
    
    async def close(self):
        """Close storage service"""
        if self.client:
            await self.client.aclose()
        logger.info("Storage service closed")