"""Cache backends package."""

from .base import CacheBackend
from .memory import MemoryCacheBackend
from .sqlite import SQLiteCacheBackend

__all__ = ["CacheBackend", "MemoryCacheBackend", "SQLiteCacheBackend"]

try:
    from .redis import RedisCacheBackend
    __all__.append("RedisCacheBackend")
except ImportError:
    pass