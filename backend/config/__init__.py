"""
Configuration module for Family Album Backend

Provides environment-specific configuration for:
- Database settings
- File storage paths
- Upload limits and restrictions
"""

from .storage import storage_config, get_storage_config, StorageConfig

__all__ = ["storage_config", "get_storage_config", "StorageConfig"]