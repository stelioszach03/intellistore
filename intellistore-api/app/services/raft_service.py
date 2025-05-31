"""
Raft metadata service client
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)


class RaftService:
    """Service for interacting with Raft metadata cluster"""
    
    def __init__(self, leader_addr: str, storage_nodes: List[str], timeout: int = 10):
        self.leader_addr = leader_addr
        self.storage_nodes = storage_nodes
        self.timeout = timeout
        self.client = None
        self._initialized = False
        self._current_leader = None
    
    async def initialize(self):
        """Initialize HTTP client and discover leader"""
        try:
            # Create HTTP client
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
            )
            
            # Discover current leader
            await self._discover_leader()
            
            self._initialized = True
            logger.info("Raft service initialized successfully", 
                       leader=self._current_leader,
                       storage_nodes=len(self.storage_nodes))
            
        except Exception as e:
            logger.error("Failed to initialize Raft service", error=str(e))
            raise
    
    async def _discover_leader(self):
        """Discover the current Raft leader"""
        try:
            # Try the configured leader address first
            leader_url = f"http://{self.leader_addr}/cluster/leader"
            
            response = await self.client.get(leader_url)
            if response.status_code == 200:
                data = response.json()
                self._current_leader = data.get("leader", self.leader_addr)
                logger.debug("Leader discovered", leader=self._current_leader)
                return
            
            # If that fails, try to find leader from cluster status
            status_url = f"http://{self.leader_addr}/cluster/status"
            response = await self.client.get(status_url)
            if response.status_code == 200:
                data = response.json()
                if data.get("state") == "Leader":
                    self._current_leader = self.leader_addr
                else:
                    self._current_leader = data.get("leader", self.leader_addr)
                logger.debug("Leader found from status", leader=self._current_leader)
                return
            
            # Fallback to configured address
            self._current_leader = self.leader_addr
            logger.warning("Could not discover leader, using configured address", 
                          leader=self._current_leader)
            
        except Exception as e:
            logger.error("Failed to discover leader", error=str(e))
            self._current_leader = self.leader_addr
    
    async def _make_request(self, method: str, path: str, data: Optional[Dict] = None, retries: int = 3):
        """Make HTTP request to Raft cluster with leader discovery"""
        if not self._initialized:
            raise Exception("Raft service not initialized")
        
        for attempt in range(retries):
            try:
                url = f"http://{self._current_leader}{path}"
                
                if method.upper() == "GET":
                    response = await self.client.get(url)
                elif method.upper() == "POST":
                    response = await self.client.post(url, json=data)
                elif method.upper() == "PATCH":
                    response = await self.client.patch(url, json=data)
                elif method.upper() == "DELETE":
                    response = await self.client.delete(url)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Handle redirects to leader
                if response.status_code == 307:  # Temporary Redirect
                    new_leader = response.headers.get("Location", "").replace("http://", "").split("/")[0]
                    if new_leader:
                        self._current_leader = new_leader
                        logger.info("Redirected to new leader", leader=new_leader)
                        continue
                
                # Check for success
                if response.status_code < 400:
                    return response
                
                # Handle errors
                if response.status_code >= 500:
                    logger.warning("Server error, retrying", 
                                 status=response.status_code, 
                                 attempt=attempt + 1)
                    if attempt < retries - 1:
                        await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                        continue
                
                # Client error, don't retry
                response.raise_for_status()
                
            except httpx.ConnectError:
                logger.warning("Connection error, trying to discover new leader", 
                             attempt=attempt + 1)
                if attempt < retries - 1:
                    await self._discover_leader()
                    await asyncio.sleep(1)
                    continue
                raise
            except Exception as e:
                if attempt < retries - 1:
                    logger.warning("Request failed, retrying", 
                                 error=str(e), 
                                 attempt=attempt + 1)
                    await asyncio.sleep(1)
                    continue
                raise
        
        raise Exception(f"Failed to complete request after {retries} attempts")
    
    # Bucket operations
    async def create_bucket(self, bucket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new bucket"""
        try:
            response = await self._make_request("POST", "/buckets", bucket_data)
            return response.json()
        except Exception as e:
            logger.error("Failed to create bucket", bucket=bucket_data.get("name"), error=str(e))
            raise
    
    async def get_bucket(self, bucket_name: str) -> Optional[Dict[str, Any]]:
        """Get bucket metadata"""
        try:
            response = await self._make_request("GET", f"/buckets/{bucket_name}")
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error("Failed to get bucket", bucket=bucket_name, error=str(e))
            raise
    
    async def list_buckets(self) -> List[Dict[str, Any]]:
        """List all buckets"""
        try:
            response = await self._make_request("GET", "/buckets")
            return response.json()
        except Exception as e:
            logger.error("Failed to list buckets", error=str(e))
            raise
    
    async def update_bucket(self, bucket_name: str, update_data: Dict[str, Any]):
        """Update bucket metadata"""
        try:
            response = await self._make_request("PATCH", f"/buckets/{bucket_name}", update_data)
            return response.json()
        except Exception as e:
            logger.error("Failed to update bucket", bucket=bucket_name, error=str(e))
            raise
    
    async def delete_bucket(self, bucket_name: str, force: bool = False):
        """Delete a bucket"""
        try:
            path = f"/buckets/{bucket_name}"
            if force:
                path += "?force=true"
            await self._make_request("DELETE", path)
        except Exception as e:
            logger.error("Failed to delete bucket", bucket=bucket_name, error=str(e))
            raise
    
    async def get_bucket_stats(self, bucket_name: str) -> Dict[str, Any]:
        """Get bucket statistics"""
        try:
            # This would be a custom endpoint for bucket stats
            response = await self._make_request("GET", f"/buckets/{bucket_name}/stats")
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"object_count": 0, "total_size": 0, "hot_objects": 0, "cold_objects": 0}
            raise
        except Exception as e:
            logger.error("Failed to get bucket stats", bucket=bucket_name, error=str(e))
            # Return default stats on error
            return {"object_count": 0, "total_size": 0, "hot_objects": 0, "cold_objects": 0}
    
    # Object operations
    async def create_object(self, object_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create object metadata"""
        try:
            bucket_name = object_data["bucket_name"]
            response = await self._make_request("POST", f"/buckets/{bucket_name}/objects", object_data)
            return response.json()
        except Exception as e:
            logger.error("Failed to create object", 
                        bucket=object_data.get("bucket_name"),
                        object=object_data.get("object_key"),
                        error=str(e))
            raise
    
    async def get_object(self, bucket_name: str, object_key: str) -> Optional[Dict[str, Any]]:
        """Get object metadata"""
        try:
            response = await self._make_request("GET", f"/buckets/{bucket_name}/objects/{object_key}")
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error("Failed to get object", 
                        bucket=bucket_name, 
                        object=object_key, 
                        error=str(e))
            raise
    
    async def list_objects(self, 
                          bucket_name: str, 
                          prefix: Optional[str] = None,
                          limit: int = 100,
                          continuation_token: Optional[str] = None) -> Dict[str, Any]:
        """List objects in a bucket"""
        try:
            params = {"limit": limit}
            if prefix:
                params["prefix"] = prefix
            if continuation_token:
                params["continuation_token"] = continuation_token
            
            # Build query string
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            path = f"/buckets/{bucket_name}/objects?{query_string}"
            
            response = await self._make_request("GET", path)
            return response.json()
        except Exception as e:
            logger.error("Failed to list objects", bucket=bucket_name, error=str(e))
            raise
    
    async def update_object(self, bucket_name: str, object_key: str, update_data: Dict[str, Any]):
        """Update object metadata"""
        try:
            response = await self._make_request("PATCH", f"/buckets/{bucket_name}/objects/{object_key}", update_data)
            return response.json()
        except Exception as e:
            logger.error("Failed to update object", 
                        bucket=bucket_name, 
                        object=object_key, 
                        error=str(e))
            raise
    
    async def delete_object(self, bucket_name: str, object_key: str):
        """Delete object metadata"""
        try:
            await self._make_request("DELETE", f"/buckets/{bucket_name}/objects/{object_key}")
        except Exception as e:
            logger.error("Failed to delete object", 
                        bucket=bucket_name, 
                        object=object_key, 
                        error=str(e))
            raise
    
    async def update_object_access_time(self, bucket_name: str, object_key: str):
        """Update object last accessed time"""
        try:
            update_data = {"last_accessed": time.time()}
            await self.update_object(bucket_name, object_key, update_data)
        except Exception as e:
            logger.error("Failed to update object access time", 
                        bucket=bucket_name, 
                        object=object_key, 
                        error=str(e))
            # Don't raise - this is not critical
    
    # Storage node operations
    async def get_storage_nodes(self, tier: Optional[str] = None) -> List[str]:
        """Get list of available storage nodes"""
        try:
            # Filter by tier if specified
            if tier:
                # In a real implementation, this would query the metadata service
                # for nodes of a specific tier
                return [node for node in self.storage_nodes if tier in node]
            return self.storage_nodes.copy()
        except Exception as e:
            logger.error("Failed to get storage nodes", tier=tier, error=str(e))
            raise
    
    async def register_storage_node(self, node_id: str, node_addr: str, tier: str):
        """Register a new storage node"""
        try:
            node_data = {
                "node_id": node_id,
                "node_addr": node_addr,
                "tier": tier,
                "registered_at": time.time()
            }
            response = await self._make_request("POST", "/storage-nodes", node_data)
            return response.json()
        except Exception as e:
            logger.error("Failed to register storage node", 
                        node_id=node_id, 
                        error=str(e))
            raise
    
    async def unregister_storage_node(self, node_id: str):
        """Unregister a storage node"""
        try:
            await self._make_request("DELETE", f"/storage-nodes/{node_id}")
        except Exception as e:
            logger.error("Failed to unregister storage node", 
                        node_id=node_id, 
                        error=str(e))
            raise
    
    # Cluster operations
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        try:
            response = await self._make_request("GET", "/cluster/status")
            return response.json()
        except Exception as e:
            logger.error("Failed to get cluster status", error=str(e))
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Raft service health"""
        try:
            if not self.client:
                return {"status": "unhealthy", "error": "Client not initialized"}
            
            # Try to get cluster status
            status = await self.get_cluster_status()
            
            return {
                "status": "healthy",
                "leader": self._current_leader,
                "cluster_status": status,
                "storage_nodes": len(self.storage_nodes)
            }
            
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self):
        """Close Raft service"""
        if self.client:
            await self.client.aclose()
            self.client = None
        self._initialized = False
        logger.info("Raft service closed")