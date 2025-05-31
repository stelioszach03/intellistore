"""
HashiCorp Vault service for encryption key management
"""

import asyncio
import base64
import json
from typing import Dict, Any, Optional

import hvac
import structlog
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = structlog.get_logger(__name__)


class VaultService:
    """Service for interacting with HashiCorp Vault"""
    
    def __init__(self, vault_url: str, vault_token: str, mount_point: str = "intellistore"):
        self.vault_url = vault_url
        self.vault_token = vault_token
        self.mount_point = mount_point
        self.client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Vault client and setup"""
        try:
            # Create Vault client
            self.client = hvac.Client(
                url=self.vault_url,
                token=self.vault_token
            )
            
            # Verify authentication
            if not self.client.is_authenticated():
                raise Exception("Failed to authenticate with Vault")
            
            # Setup transit engine for encryption
            await self._setup_transit_engine()
            
            # Setup KV engine for metadata
            await self._setup_kv_engine()
            
            self._initialized = True
            logger.info("Vault service initialized successfully", vault_url=self.vault_url)
            
        except Exception as e:
            logger.error("Failed to initialize Vault service", error=str(e))
            raise
    
    async def _setup_transit_engine(self):
        """Setup transit engine for encryption operations"""
        try:
            # Enable transit engine if not already enabled
            engines = self.client.sys.list_auth_methods()
            if f"{self.mount_point}-transit/" not in engines:
                self.client.sys.enable_secrets_engine(
                    backend_type="transit",
                    path=f"{self.mount_point}-transit"
                )
                logger.info("Transit engine enabled", path=f"{self.mount_point}-transit")
            
            # Create encryption key for data encryption
            key_name = "data-encryption-key"
            try:
                self.client.secrets.transit.create_key(
                    name=key_name,
                    mount_point=f"{self.mount_point}-transit"
                )
                logger.info("Data encryption key created", key_name=key_name)
            except hvac.exceptions.InvalidRequest:
                # Key already exists
                logger.debug("Data encryption key already exists", key_name=key_name)
                
        except Exception as e:
            logger.error("Failed to setup transit engine", error=str(e))
            raise
    
    async def _setup_kv_engine(self):
        """Setup KV engine for storing metadata"""
        try:
            # Enable KV v2 engine if not already enabled
            engines = self.client.sys.list_auth_methods()
            if f"{self.mount_point}-kv/" not in engines:
                self.client.sys.enable_secrets_engine(
                    backend_type="kv",
                    path=f"{self.mount_point}-kv",
                    options={"version": "2"}
                )
                logger.info("KV engine enabled", path=f"{self.mount_point}-kv")
                
        except Exception as e:
            logger.error("Failed to setup KV engine", error=str(e))
            raise
    
    async def get_data_key(self, bucket_name: str, object_key: str) -> str:
        """Get or create a data encryption key for an object"""
        if not self._initialized:
            raise Exception("Vault service not initialized")
        
        try:
            # Generate a unique key name for this object
            key_path = f"data-keys/{bucket_name}/{object_key}"
            
            # Try to get existing key
            try:
                response = self.client.secrets.kv.v2.read_secret_version(
                    path=key_path,
                    mount_point=f"{self.mount_point}-kv"
                )
                return response["data"]["data"]["key"]
            except hvac.exceptions.InvalidPath:
                # Key doesn't exist, create new one
                pass
            
            # Generate new data key using transit engine
            response = self.client.secrets.transit.generate_data_key(
                name="data-encryption-key",
                key_type="plaintext",
                mount_point=f"{self.mount_point}-transit"
            )
            
            plaintext_key = response["data"]["plaintext"]
            ciphertext_key = response["data"]["ciphertext"]
            
            # Store the encrypted key in KV store
            self.client.secrets.kv.v2.create_or_update_secret(
                path=key_path,
                secret={
                    "key": plaintext_key,
                    "encrypted_key": ciphertext_key,
                    "bucket": bucket_name,
                    "object": object_key,
                    "created_at": str(asyncio.get_event_loop().time())
                },
                mount_point=f"{self.mount_point}-kv"
            )
            
            logger.debug("Data key generated", bucket=bucket_name, object=object_key)
            return plaintext_key
            
        except Exception as e:
            logger.error("Failed to get data key", 
                        bucket=bucket_name, 
                        object=object_key, 
                        error=str(e))
            raise
    
    async def encrypt_data(self, data: bytes, key: str) -> bytes:
        """Encrypt data using the provided key"""
        try:
            # Decode the base64 key
            key_bytes = base64.b64decode(key.encode())
            
            # Create Fernet cipher
            fernet = Fernet(base64.urlsafe_b64encode(key_bytes[:32]))
            
            # Encrypt data
            encrypted_data = fernet.encrypt(data)
            
            logger.debug("Data encrypted", size=len(data), encrypted_size=len(encrypted_data))
            return encrypted_data
            
        except Exception as e:
            logger.error("Failed to encrypt data", error=str(e))
            raise
    
    async def decrypt_data(self, encrypted_data: bytes, key: str) -> bytes:
        """Decrypt data using the provided key"""
        try:
            # Decode the base64 key
            key_bytes = base64.b64decode(key.encode())
            
            # Create Fernet cipher
            fernet = Fernet(base64.urlsafe_b64encode(key_bytes[:32]))
            
            # Decrypt data
            decrypted_data = fernet.decrypt(encrypted_data)
            
            logger.debug("Data decrypted", encrypted_size=len(encrypted_data), size=len(decrypted_data))
            return decrypted_data
            
        except Exception as e:
            logger.error("Failed to decrypt data", error=str(e))
            raise
    
    async def delete_data_key(self, bucket_name: str, object_key: str):
        """Delete a data encryption key"""
        if not self._initialized:
            raise Exception("Vault service not initialized")
        
        try:
            key_path = f"data-keys/{bucket_name}/{object_key}"
            
            # Delete the key from KV store
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=key_path,
                mount_point=f"{self.mount_point}-kv"
            )
            
            logger.debug("Data key deleted", bucket=bucket_name, object=object_key)
            
        except Exception as e:
            logger.error("Failed to delete data key", 
                        bucket=bucket_name, 
                        object=object_key, 
                        error=str(e))
            raise
    
    async def create_bucket_policy(self, bucket_name: str, owner: str, acl: Dict[str, str]):
        """Create Vault policy for bucket access"""
        if not self._initialized:
            raise Exception("Vault service not initialized")
        
        try:
            # Create policy for bucket access
            policy_name = f"bucket-{bucket_name}"
            
            # Build policy rules
            rules = []
            
            # Owner has full access
            rules.append(f'''
path "{self.mount_point}-kv/data/data-keys/{bucket_name}/*" {{
  capabilities = ["create", "read", "update", "delete", "list"]
}}
''')
            
            # Add rules for ACL users
            for user, permission in acl.items():
                if permission in ["read", "write", "admin"]:
                    capabilities = ["read"]
                    if permission in ["write", "admin"]:
                        capabilities.extend(["create", "update", "delete"])
                    if permission == "admin":
                        capabilities.append("list")
                    
                    rules.append(f'''
path "{self.mount_point}-kv/data/data-keys/{bucket_name}/*" {{
  capabilities = {json.dumps(capabilities)}
}}
''')
            
            policy_content = "\n".join(rules)
            
            # Create the policy
            self.client.sys.create_or_update_policy(
                name=policy_name,
                policy=policy_content
            )
            
            logger.info("Bucket policy created", bucket=bucket_name, policy=policy_name)
            
        except Exception as e:
            logger.error("Failed to create bucket policy", 
                        bucket=bucket_name, 
                        error=str(e))
            raise
    
    async def delete_bucket_policy(self, bucket_name: str):
        """Delete Vault policy for bucket"""
        if not self._initialized:
            raise Exception("Vault service not initialized")
        
        try:
            policy_name = f"bucket-{bucket_name}"
            
            # Delete the policy
            self.client.sys.delete_policy(name=policy_name)
            
            logger.info("Bucket policy deleted", bucket=bucket_name, policy=policy_name)
            
        except Exception as e:
            logger.error("Failed to delete bucket policy", 
                        bucket=bucket_name, 
                        error=str(e))
            raise
    
    async def get_bucket_keys(self, bucket_name: str) -> list:
        """List all data keys for a bucket"""
        if not self._initialized:
            raise Exception("Vault service not initialized")
        
        try:
            key_path = f"data-keys/{bucket_name}"
            
            response = self.client.secrets.kv.v2.list_secrets(
                path=key_path,
                mount_point=f"{self.mount_point}-kv"
            )
            
            return response["data"]["keys"]
            
        except hvac.exceptions.InvalidPath:
            return []
        except Exception as e:
            logger.error("Failed to list bucket keys", 
                        bucket=bucket_name, 
                        error=str(e))
            raise
    
    async def cleanup_bucket_keys(self, bucket_name: str):
        """Delete all data keys for a bucket"""
        if not self._initialized:
            raise Exception("Vault service not initialized")
        
        try:
            # Get all keys for the bucket
            keys = await self.get_bucket_keys(bucket_name)
            
            # Delete each key
            for key in keys:
                await self.delete_data_key(bucket_name, key)
            
            logger.info("Bucket keys cleaned up", bucket=bucket_name, count=len(keys))
            
        except Exception as e:
            logger.error("Failed to cleanup bucket keys", 
                        bucket=bucket_name, 
                        error=str(e))
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Vault service health"""
        try:
            if not self.client:
                return {"status": "unhealthy", "error": "Client not initialized"}
            
            # Check if authenticated
            if not self.client.is_authenticated():
                return {"status": "unhealthy", "error": "Not authenticated"}
            
            # Check if sealed
            seal_status = self.client.sys.read_seal_status()
            if seal_status["sealed"]:
                return {"status": "unhealthy", "error": "Vault is sealed"}
            
            return {
                "status": "healthy",
                "vault_url": self.vault_url,
                "mount_point": self.mount_point,
                "seal_status": seal_status
            }
            
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self):
        """Close Vault service"""
        if self.client:
            # Vault client doesn't need explicit closing
            self.client = None
        self._initialized = False
        logger.info("Vault service closed")