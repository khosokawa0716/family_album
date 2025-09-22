"""
Configuration module for Family Album Backend

Provides environment-specific configuration for:
- Database settings
- File storage paths
- Upload limits and restrictions
"""

import os

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

from .storage import storage_config, get_storage_config, StorageConfig

__all__ = ["SECRET_KEY", "ALGORITHM", "ACCESS_TOKEN_EXPIRE_MINUTES", "storage_config", "get_storage_config", "StorageConfig"]