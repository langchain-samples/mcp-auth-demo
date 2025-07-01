"""
Secret management system for storing and retrieving user tokens.

This module provides a secure way to store and retrieve user credentials
for various MCP servers (GitHub, Jira, etc.).
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import aiohttp
import hashlib
import base64

logger = logging.getLogger(__name__)


@dataclass
class UserTokens:
    """Container for user's service tokens."""
    
    github_token: Optional[str] = None
    expiry_time: Optional[datetime] = None
    refresh_token: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "github_token": self.github_token,
            "expiry_time": self.expiry_time.isoformat() if self.expiry_time else None,
            "refresh_token": self.refresh_token
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserTokens":
        """Create from dictionary."""
        expiry_str = data.get("expiry_time")
        expiry_time = datetime.fromisoformat(expiry_str) if expiry_str else None
        
        return cls(
            github_token=data.get("github_token"),
            expiry_time=expiry_time,
            refresh_token=data.get("refresh_token")
        )


class SecretStore:
    """
    Secure secret storage interface.
    
    In production, this would integrate with services like:
    - AWS Secrets Manager
    - HashiCorp Vault
    - Azure Key Vault
    - Google Secret Manager
    """
    
    def __init__(self, url: Optional[str] = None, token: Optional[str] = None):
        """
        Initialize secret store.
        
        Args:
            url: URL of the secret store service
            token: Authentication token for secret store
        """
        self.url = url or "https://mock-secret-store.example.com"
        self.token = token
        self.session = None
        
        # Mock storage for demo (use real secret store in production)
        self._mock_storage: Dict[str, UserTokens] = {}
        self._initialize_demo_tokens()
    
    def _initialize_demo_tokens(self):
        """Initialize demo tokens for testing."""
        demo_users = {
            "user_123": UserTokens(
                github_token="ghp_demo_token_123",
                expiry_time=datetime.utcnow() + timedelta(hours=24),
                refresh_token="refresh_demo_123"
            ),
            "user_456": UserTokens(
                github_token="ghp_demo_token_456",
                expiry_time=datetime.utcnow() + timedelta(hours=12)
            ),
            "user_789": UserTokens(
                github_token="ghp_demo_token_789",
                expiry_time=datetime.utcnow() + timedelta(hours=48)
            )
        }
        
        self._mock_storage.update(demo_users)
        logger.info(f"Initialized demo tokens for {len(demo_users)} users")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if not self.session:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            
            self.session = aiohttp.ClientSession(headers=headers)
        
        return self.session
    
    async def get_user_tokens(self, user_id: str) -> Optional[UserTokens]:
        """
        Retrieve user tokens from secure storage.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserTokens object or None if not found
        """
        try:
            # For demo, use mock storage
            if user_id in self._mock_storage:
                tokens = self._mock_storage[user_id]
                logger.info(f"Retrieved tokens for user {user_id}")
                return tokens
            
            # In production, make API call to secret store
            session = await self._get_session()
            
            async with session.get(f"{self.url}/users/{user_id}/tokens") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tokens = UserTokens.from_dict(data)
                    logger.info(f"Retrieved tokens for user {user_id} from secret store")
                    return tokens
                elif resp.status == 404:
                    logger.warning(f"No tokens found for user {user_id}")
                    return None
                else:
                    logger.error(f"Error retrieving tokens: {resp.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error retrieving tokens for user {user_id}: {e}")
            return None
    
    async def store_user_tokens(self, user_id: str, tokens: UserTokens) -> bool:
        """
        Store user tokens securely.
        
        Args:
            user_id: User identifier
            tokens: UserTokens to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # For demo, use mock storage
            self._mock_storage[user_id] = tokens
            logger.info(f"Stored tokens for user {user_id}")
            
            # In production, make API call to secret store
            session = await self._get_session()
            
            payload = {
                "user_id": user_id,
                "tokens": tokens.to_dict(),
                "encrypted": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            async with session.put(
                f"{self.url}/users/{user_id}/tokens",
                json=payload
            ) as resp:
                if resp.status in [200, 201]:
                    logger.info(f"Successfully stored tokens for user {user_id}")
                    return True
                else:
                    logger.error(f"Error storing tokens: {resp.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error storing tokens for user {user_id}: {e}")
            return False
    
    async def refresh_user_tokens(self, user_id: str) -> Optional[UserTokens]:
        """
        Refresh user tokens using refresh token.
        
        Args:
            user_id: User identifier
            
        Returns:
            New UserTokens or None if refresh failed
        """
        try:
            current_tokens = await self.get_user_tokens(user_id)
            if not current_tokens or not current_tokens.refresh_token:
                logger.warning(f"No refresh token available for user {user_id}")
                return None
            
            # Mock token refresh for demo
            new_tokens = UserTokens(
                github_token=f"ghp_refreshed_{user_id}_{int(datetime.utcnow().timestamp())}",
                expiry_time=datetime.utcnow() + timedelta(hours=24),
                refresh_token=f"refresh_new_{user_id}_{int(datetime.utcnow().timestamp())}"
            )
            
            # Store new tokens
            if await self.store_user_tokens(user_id, new_tokens):
                logger.info(f"Successfully refreshed tokens for user {user_id}")
                return new_tokens
            
            return None
            
        except Exception as e:
            logger.error(f"Error refreshing tokens for user {user_id}: {e}")
            return None
    
    async def delete_user_tokens(self, user_id: str) -> bool:
        """
        Delete user tokens from storage.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove from mock storage
            if user_id in self._mock_storage:
                del self._mock_storage[user_id]
            
            # In production, make API call to secret store
            session = await self._get_session()
            
            async with session.delete(f"{self.url}/users/{user_id}/tokens") as resp:
                if resp.status in [200, 204]:
                    logger.info(f"Successfully deleted tokens for user {user_id}")
                    return True
                else:
                    logger.error(f"Error deleting tokens: {resp.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting tokens for user {user_id}: {e}")
            return False
    
    async def list_users_with_tokens(self) -> List[str]:
        """
        List all users who have stored tokens.
        
        Returns:
            List of user IDs
        """
        try:
            # Return mock storage users for demo
            return list(self._mock_storage.keys())
            
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    async def validate_token(self, service: str, token: str) -> bool:
        """
        Validate a token against its service.
        
        Args:
            service: Service name (github, jira, etc.)
            token: Token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            validation_urls = {
                "github": "https://api.github.com/user"
            }
            
            url = validation_urls.get(service)
            if not url:
                logger.warning(f"No validation URL for service: {service}")
                return False
            
            session = await self._get_session()
            headers = {"Authorization": f"Bearer {token}"}
            
            async with session.get(url, headers=headers) as resp:
                is_valid = resp.status == 200
                logger.info(f"Token validation for {service}: {'valid' if is_valid else 'invalid'}")
                return is_valid
                
        except Exception as e:
            logger.error(f"Error validating {service} token: {e}")
            return False
    
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())


class SecretEncryption:
    """Utility class for encrypting/decrypting secrets."""
    
    @staticmethod
    def encrypt_token(token: str, key: str) -> str:
        """
        Encrypt a token (simplified for demo).
        
        In production, use proper encryption libraries like:
        - cryptography.fernet
        - AWS KMS
        - Azure Key Vault encryption
        """
        # Simple base64 encoding for demo (NOT secure for production)
        combined = f"{key}:{token}"
        encoded = base64.b64encode(combined.encode()).decode()
        return encoded
    
    @staticmethod
    def decrypt_token(encrypted_token: str, key: str) -> str:
        """
        Decrypt a token (simplified for demo).
        """
        try:
            decoded = base64.b64decode(encrypted_token.encode()).decode()
            stored_key, token = decoded.split(":", 1)
            if stored_key == key:
                return token
            else:
                raise ValueError("Invalid decryption key")
        except Exception:
            raise ValueError("Failed to decrypt token")
    
    @staticmethod
    def hash_user_id(user_id: str) -> str:
        """Create a hash of user ID for indexing."""
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]


# Factory function for different secret store backends
def create_secret_store(backend: str = "demo", **kwargs) -> SecretStore:
    """
    Create a secret store instance.
    
    Args:
        backend: Backend type (demo, vault, aws, azure, gcp)
        **kwargs: Backend-specific configuration
        
    Returns:
        SecretStore instance
    """
    if backend == "demo":
        return SecretStore(**kwargs)
    elif backend == "vault":
        # Integration with HashiCorp Vault
        return VaultSecretStore(**kwargs)
    elif backend == "aws":
        # Integration with AWS Secrets Manager
        return AWSSecretStore(**kwargs)
    else:
        raise ValueError(f"Unknown secret store backend: {backend}")


# Placeholder classes for production integrations
class VaultSecretStore(SecretStore):
    """HashiCorp Vault integration (placeholder)."""
    pass


class AWSSecretStore(SecretStore):
    """AWS Secrets Manager integration (placeholder)."""
    pass