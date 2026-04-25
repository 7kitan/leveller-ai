"""
Redis Session Encryption Module

Provides encryption/decryption for sensitive data stored in Redis.
"""
import os
import logging
from cryptography.fernet import Fernet
from typing import Optional
import base64
import hashlib

logger = logging.getLogger(__name__)


class RedisEncryption:
    """
    Handles encryption/decryption of Redis data using Fernet (symmetric encryption).
    """
    
    def __init__(self):
        # Get encryption key from environment or generate one
        encryption_key = os.getenv("REDIS_ENCRYPTION_KEY")
        
        if not encryption_key:
            logger.critical("=" * 80)
            logger.critical("SECURITY WARNING: REDIS_ENCRYPTION_KEY not set!")
            logger.critical("Session data will be stored in plaintext.")
            logger.critical("Generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
            logger.critical("=" * 80)
            
            # In production, refuse to start
            if os.getenv("ENVIRONMENT", "development").lower() == "production":
                logger.critical("FATAL: Cannot start in production without REDIS_ENCRYPTION_KEY!")
                import sys
                sys.exit(1)
            
            # For development, use a deterministic key (NOT SECURE)
            logger.warning("Using development encryption key (NOT SECURE)")
            encryption_key = base64.urlsafe_b64encode(hashlib.sha256(b"dev_key_not_secure").digest()).decode()
        
        try:
            self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
            logger.info("Redis encryption initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt string data.
        
        Args:
            data: Plain text string
            
        Returns:
            Encrypted string (base64 encoded)
        """
        try:
            encrypted_bytes = self.cipher.encrypt(data.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """
        Decrypt encrypted string data.
        
        Args:
            encrypted_data: Encrypted string (base64 encoded)
            
        Returns:
            Decrypted plain text string, or None if decryption fails
        """
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_data.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def encrypt_if_enabled(self, data: str) -> str:
        """
        Encrypt data if encryption is enabled, otherwise return as-is.
        Safe wrapper for backward compatibility.
        """
        if self.cipher:
            return self.encrypt(data)
        return data
    
    def decrypt_if_enabled(self, data: str) -> Optional[str]:
        """
        Decrypt data if encryption is enabled, otherwise return as-is.
        Safe wrapper for backward compatibility.
        """
        if self.cipher:
            return self.decrypt(data)
        return data


# Global encryption instance
try:
    redis_encryption = RedisEncryption()
except Exception as e:
    logger.error(f"Failed to initialize Redis encryption: {e}")
    redis_encryption = None


def encrypt_session_data(data: str) -> str:
    """Encrypt session data before storing in Redis."""
    if redis_encryption:
        return redis_encryption.encrypt(data)
    return data


def decrypt_session_data(encrypted_data: str) -> Optional[str]:
    """Decrypt session data retrieved from Redis."""
    if redis_encryption:
        return redis_encryption.decrypt(encrypted_data)
    return encrypted_data
