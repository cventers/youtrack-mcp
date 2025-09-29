# YouTrack MCP Server - Unified Caching Implementation Plan
**Date:** 2025-01-29  
**Author:** Chase Venters / Claude  
**Status:** PROPOSED  
**Priority:** HIGH  

## Executive Summary

Based on the comprehensive caching analysis in `docs/caching.md`, this plan outlines the implementation of a unified, multiprocess-safe caching system for the YouTrack MCP server. The system will support multiple backends (memory, SQLite, Redis) with TTL enforcement, providing significant performance improvements for ID resolution and API operations.

## Current State

### Existing Infrastructure
- **6 separate cache implementations** using `cachetools` (already installed)
- **All memory-only** - data lost on restart
- **No unified strategy** - inconsistent TTL and size configurations
- **CacheConfig exists** but underutilized (`youtrack_mcp/config.py`)

### Key Problems to Solve
1. **ID Resolution Performance**: Every `project="ACC"` requires API lookup
2. **Process Isolation**: Caches not shared between processes/restarts
3. **No Redis Support**: Despite being a common enterprise requirement
4. **Fragmented Implementation**: 6 different caching patterns

## Proposed Architecture

### Cache Strategy Options

| Strategy | Description | Use Case |
|----------|-------------|----------|
| OFF | No caching | Testing/debugging |
| SQLITE_HYBRID | Memory (L1) + SQLite (L2) | Default for production |
| REDIS | Redis-only distributed cache | Enterprise/distributed systems |

## Implementation Plan

### Phase 1: Core Infrastructure

#### 1.1 Create Cache Package Structure
```
youtrack_mcp/cache/
├── __init__.py
├── manager.py         # Unified cache manager
├── backends/
│   ├── __init__.py
│   ├── base.py       # Abstract base class
│   ├── memory.py     # TTLCache backend
│   ├── sqlite.py     # SQLite backend
│   └── redis.py      # Redis backend (optional)
├── strategies.py      # Cache strategies (hybrid, tiered)
└── monitoring.py      # Cache metrics and analytics
```

#### 1.2 Abstract Cache Backend
**File:** `youtrack_mcp/cache/backends/base.py`

```python
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
import asyncio

class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Retrieve value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = "default") -> None:
        """Store value in cache with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete key from cache."""
        pass
    
    @abstractmethod
    async def clear(self, namespace: Optional[str] = None) -> int:
        """Clear cache, optionally by namespace."""
        pass
    
    @abstractmethod
    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        pass
```

#### 1.3 Memory Backend Implementation
**File:** `youtrack_mcp/cache/backends/memory.py`

```python
from cachetools import TTLCache
from typing import Any, Optional, Dict
import time
from .base import CacheBackend

class MemoryCacheBackend(CacheBackend):
    """In-memory cache using cachetools TTLCache."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.caches: Dict[str, TTLCache] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    def _get_cache(self, namespace: str) -> TTLCache:
        """Get or create cache for namespace."""
        if namespace not in self.caches:
            self.caches[namespace] = TTLCache(
                maxsize=self.max_size,
                ttl=self.default_ttl
            )
        return self.caches[namespace]
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        cache = self._get_cache(namespace)
        if key in cache:
            self.stats["hits"] += 1
            return cache[key]
        self.stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = "default") -> None:
        cache = self._get_cache(namespace)
        # TTLCache handles TTL internally
        cache[key] = value
        self.stats["sets"] += 1
```

#### 1.4 SQLite Backend Implementation
**File:** `youtrack_mcp/cache/backends/sqlite.py`

```python
import sqlite3
import json
import time
import asyncio
from pathlib import Path
from typing import Any, Optional, Dict
from .base import CacheBackend

class SQLiteCacheBackend(CacheBackend):
    """SQLite-based persistent cache with multiprocess support."""
    
    def __init__(self, db_path: Optional[Path] = None, default_ttl: int = 300):
        self.db_path = db_path or Path.home() / ".youtrack-mcp" / "cache.db"
        self.default_ttl = default_ttl
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database with WAL mode for multiprocess access."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")  # Enable Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance speed and safety
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                PRIMARY KEY (namespace, key)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace ON cache(namespace)")
        conn.commit()
        conn.close()
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Retrieve value from cache with TTL check."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "SELECT value, expires_at FROM cache WHERE namespace = ? AND key = ?",
                (namespace, key)
            )
            row = cursor.fetchone()
            
            if row:
                value_json, expires_at = row
                if expires_at > time.time():
                    return json.loads(value_json)
                else:
                    # Expired, delete it
                    conn.execute(
                        "DELETE FROM cache WHERE namespace = ? AND key = ?",
                        (namespace, key)
                    )
                    conn.commit()
            return None
        finally:
            conn.close()
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = "default") -> None:
        """Store value in cache with TTL."""
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl
        value_json = json.dumps(value)
        
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "INSERT OR REPLACE INTO cache (namespace, key, value, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (namespace, key, value_json, time.time(), expires_at)
            )
            conn.commit()
        finally:
            conn.close()
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries from database."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "DELETE FROM cache WHERE expires_at < ?",
                (time.time(),)
            )
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()
```

#### 1.5 Redis Backend Implementation
**File:** `youtrack_mcp/cache/backends/redis.py`

```python
import json
import asyncio
from typing import Any, Optional, Dict
from .base import CacheBackend

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class RedisCacheBackend(CacheBackend):
    """Redis-based distributed cache backend."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 300,
        key_prefix: str = "youtrack_mcp"
    ):
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis support requires 'redis' package. "
                "Install with: uv add redis[hiredis]"
            )
        
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
    
    def _make_key(self, key: str, namespace: str) -> str:
        """Create namespaced Redis key."""
        return f"{self.key_prefix}:{namespace}:{key}"
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Retrieve value from Redis."""
        redis_key = self._make_key(key, namespace)
        value = await self.client.get(redis_key)
        if value:
            return json.loads(value)
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = "default") -> None:
        """Store value in Redis with TTL."""
        redis_key = self._make_key(key, namespace)
        value_json = json.dumps(value)
        ttl = ttl or self.default_ttl
        await self.client.setex(redis_key, ttl, value_json)
    
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete key from Redis."""
        redis_key = self._make_key(key, namespace)
        return await self.client.delete(redis_key) > 0
    
    async def clear(self, namespace: Optional[str] = None) -> int:
        """Clear cache by namespace or all."""
        pattern = f"{self.key_prefix}:{namespace}:*" if namespace else f"{self.key_prefix}:*"
        keys = await self.client.keys(pattern)
        if keys:
            return await self.client.delete(*keys)
        return 0
    
    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists."""
        redis_key = self._make_key(key, namespace)
        return await self.client.exists(redis_key) > 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get basic Redis stats."""
        info = await self.client.info("stats")
        return {
            "connected": True,
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0)
        }
    
    async def cleanup_expired(self) -> int:
        """Redis handles expiration automatically."""
        return 0
    
    async def close(self):
        """Close Redis connection."""
        await self.client.close()
```

#### 1.6 Unified Cache Manager
**File:** `youtrack_mcp/cache/manager.py`

```python
from enum import Enum
from typing import Any, Optional, Dict, List
import asyncio
from .backends import MemoryCacheBackend, SQLiteCacheBackend, RedisCacheBackend
from .backends.base import CacheBackend

class CacheStrategy(str, Enum):
    OFF = "off"
    SQLITE_HYBRID = "sqlite_hybrid"
    REDIS = "redis"

class UnifiedCacheManager:
    """Unified cache manager with multiple backend support."""
    
    def __init__(
        self,
        strategy: CacheStrategy = CacheStrategy.SQLITE_HYBRID,
        memory_config: Optional[Dict] = None,
        sqlite_config: Optional[Dict] = None,
        redis_config: Optional[Dict] = None
    ):
        self.strategy = strategy
        self.backends: List[CacheBackend] = []
        
        # Initialize backends based on strategy
        if strategy == CacheStrategy.OFF:
            # No caching
            pass
        elif strategy == CacheStrategy.SQLITE_HYBRID:
            self.memory = MemoryCacheBackend(**(memory_config or {}))
            self.sqlite = SQLiteCacheBackend(**(sqlite_config or {}))
            self.backends = [self.memory, self.sqlite]
        elif strategy == CacheStrategy.REDIS:
            self.redis = RedisCacheBackend(**(redis_config or {}))
            self.backends = [self.redis]
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get value from cache, checking each backend in order."""
        if self.strategy == CacheStrategy.OFF:
            return None
            
        for i, backend in enumerate(self.backends):
            value = await backend.get(key, namespace)
            if value is not None:
                # Populate faster caches (backfill) for SQLITE_HYBRID
                if self.strategy == CacheStrategy.SQLITE_HYBRID and i > 0:
                    for j in range(i):
                        await self.backends[j].set(key, value, namespace=namespace)
                return value
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default",
        backends: Optional[List[str]] = None
    ) -> None:
        """Set value in cache."""
        if self.strategy == CacheStrategy.OFF:
            return
            
        tasks = []
        for backend in self.backends:
            tasks.append(backend.set(key, value, ttl, namespace))
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete key from all backends."""
        if self.strategy == CacheStrategy.OFF:
            return False
            
        results = await asyncio.gather(
            *[backend.delete(key, namespace) for backend in self.backends]
        )
        return any(results)
    
    async def clear(self, namespace: Optional[str] = None) -> int:
        """Clear cache across all backends."""
        if self.strategy == CacheStrategy.OFF:
            return 0
            
        results = await asyncio.gather(
            *[backend.clear(namespace) for backend in self.backends]
        )
        return sum(results)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics from all backends."""
        if self.strategy == CacheStrategy.OFF:
            return {"strategy": "off", "caching_disabled": True}
            
        stats = {"strategy": self.strategy.value}
        for backend in self.backends:
            backend_name = backend.__class__.__name__.replace("CacheBackend", "").lower()
            stats[backend_name] = await backend.get_stats()
        return stats
    
    async def cleanup_expired(self) -> Dict[str, int]:
        """Cleanup expired entries from all backends."""
        if self.strategy == CacheStrategy.OFF:
            return {}
            
        results = {}
        for backend in self.backends:
            backend_name = backend.__class__.__name__.replace("CacheBackend", "").lower()
            results[backend_name] = await backend.cleanup_expired()
        return results
```

### Phase 2: Configuration Integration

#### 2.1 Enhanced Cache Configuration
**Update:** `youtrack_mcp/config.py`

```python
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, Field

class CacheStrategy(str, Enum):
    OFF = "off"
    SQLITE_HYBRID = "sqlite_hybrid"
    REDIS = "redis"

class CacheConfig(BaseSettings):
    """Enhanced caching configuration with multi-backend support."""
    
    model_config = ConfigDict(
        env_prefix="CACHE_",
        case_sensitive=False,
    )
    
    # General settings
    enabled: bool = Field(True, description="Enable caching")
    strategy: CacheStrategy = Field(CacheStrategy.SQLITE_HYBRID, description="Caching strategy")
    
    # Memory cache settings (for SQLITE_HYBRID)
    memory_size: int = Field(1000, ge=1, description="Memory cache size")
    memory_ttl: int = Field(300, ge=0, description="Memory cache TTL in seconds")
    
    # SQLite settings (for SQLITE_HYBRID)
    sqlite_path: Optional[Path] = Field(None, description="SQLite cache file path")
    sqlite_ttl: int = Field(3600, ge=0, description="SQLite cache TTL in seconds")
    
    # Redis settings (for REDIS strategy)
    redis_host: str = Field("localhost", description="Redis host")
    redis_port: int = Field(6379, description="Redis port")
    redis_db: int = Field(0, description="Redis database number")
    redis_password: Optional[str] = Field(None, description="Redis password")
    redis_ttl: int = Field(3600, ge=0, description="Redis cache TTL in seconds")
    
    # Monitoring
    enable_stats: bool = Field(True, description="Enable cache statistics")
    cleanup_interval: int = Field(3600, description="Cleanup interval in seconds")
```

### Phase 3: ID Resolution Integration

#### 3.1 ID Resolver with Unified Cache
**File:** `youtrack_mcp/utils/id_resolver.py`

```python
from typing import Optional, Dict
import re
from youtrack_mcp.cache.manager import UnifiedCacheManager

class IDResolver:
    """Resolves human-friendly IDs to YouTrack internal IDs with caching."""
    
    # TTL configuration per entity type
    TTL_CONFIG = {
        "projects": 3600,    # 1 hour - projects rarely change
        "users": 3600,       # 1 hour - users relatively stable
        "issues": 1800,      # 30 minutes - issues more dynamic
        "bundles": 7200,     # 2 hours - bundle elements very stable
    }
    
    def __init__(self, client, cache_manager: UnifiedCacheManager):
        self.client = client
        self.cache = cache_manager
        
        # Regex patterns for ID detection
        self.patterns = {
            "numeric_project": re.compile(r'^\d+-\d+$'),
            "readable_issue": re.compile(r'^[A-Z]+-\d+$'),
            "user_login": re.compile(r'^[a-z][a-z0-9._-]*$')
        }
    
    async def resolve_project_id(self, project_ref: str) -> str:
        """Resolve project reference to numeric ID."""
        # Check if already numeric
        if self.patterns["numeric_project"].match(project_ref):
            return project_ref
        
        # Check cache
        cache_key = f"project:{project_ref}"
        cached_id = await self.cache.get(cache_key, namespace="id_resolution")
        if cached_id:
            return cached_id
        
        # Perform API lookup
        try:
            projects = await self.client.projects.search_projects(query=project_ref)
            for project in projects:
                if project.get("shortName") == project_ref:
                    internal_id = project.get("id")
                    # Cache the result
                    await self.cache.set(
                        cache_key,
                        internal_id,
                        ttl=self.TTL_CONFIG["projects"],
                        namespace="id_resolution"
                    )
                    return internal_id
            
            raise ValueError(f"Project not found: {project_ref}")
        except Exception as e:
            raise ValueError(f"Failed to resolve project '{project_ref}': {str(e)}")
    
    async def resolve_user_id(self, user_ref: str) -> str:
        """Resolve user reference to internal ID."""
        cache_key = f"user:{user_ref}"
        cached_id = await self.cache.get(cache_key, namespace="id_resolution")
        if cached_id:
            return cached_id
        
        # Search for user
        users = await self.client.users.search_users(query=user_ref)
        for user in users:
            if user.get("login") == user_ref or user.get("email") == user_ref:
                internal_id = user.get("id")
                await self.cache.set(
                    cache_key,
                    internal_id,
                    ttl=self.TTL_CONFIG["users"],
                    namespace="id_resolution"
                )
                return internal_id
        
        raise ValueError(f"User not found: {user_ref}")
    
    async def warm_cache(self) -> Dict[str, int]:
        """Pre-populate cache with common data."""
        counts = {"projects": 0, "users": 0}
        
        # Warm project cache
        projects = await self.client.projects.get_projects(limit=100)
        for project in projects:
            cache_key = f"project:{project['shortName']}"
            await self.cache.set(
                cache_key,
                project["id"],
                ttl=self.TTL_CONFIG["projects"],
                namespace="id_resolution"
            )
            counts["projects"] += 1
        
        # Warm user cache (top active users)
        users = await self.client.users.get_users(limit=50)
        for user in users:
            cache_key = f"user:{user['login']}"
            await self.cache.set(
                cache_key,
                user["id"],
                ttl=self.TTL_CONFIG["users"],
                namespace="id_resolution"
            )
            counts["users"] += 1
        
        return counts
```

### Phase 4: Migration Strategy

#### 4.1 Direct Updates to Existing Cache Implementations

Update all 6 existing cache implementations to use the new unified cache API:

##### 4.1.1 ErrorHandler Update
**File:** `youtrack_mcp/utils/__init__.py`

```python
# OLD CODE
class ErrorHandler:
    def __init__(self):
        self.error_cache = TTLCache(maxsize=500, ttl=1800)  # 30 minutes

# NEW CODE
class ErrorHandler:
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache = cache_manager
        self.cache_namespace = "errors"
        self.cache_ttl = 1800  # 30 minutes
    
    async def get_cached_error(self, error_key: str) -> Optional[Any]:
        return await self.cache.get(error_key, namespace=self.cache_namespace)
    
    async def cache_error(self, error_key: str, enhanced_error: Any) -> None:
        await self.cache.set(error_key, enhanced_error, ttl=self.cache_ttl, namespace=self.cache_namespace)
```

##### 4.1.2 AdvancedSearchTools Update
**File:** `youtrack_mcp/tools/search_advanced.py`

```python
# OLD CODE
def __init__(self):
    self.query_cache = TTLCache(maxsize=100, ttl=300)  # 5 minute TTL
    self.suggestion_cache = LRUCache(maxsize=50)

# NEW CODE
def __init__(self, cache_manager: UnifiedCacheManager):
    self.cache = cache_manager
    self.query_namespace = "search_queries"
    self.suggestion_namespace = "search_suggestions"
    self.query_ttl = 300  # 5 minutes
    self.suggestion_ttl = 600  # 10 minutes

async def get_cached_query(self, query: str, limit: int) -> Optional[dict]:
    cache_key = f"{query}:{limit}"
    return await self.cache.get(cache_key, namespace=self.query_namespace)

async def cache_query_result(self, query: str, limit: int, result: dict) -> None:
    cache_key = f"{query}:{limit}"
    await self.cache.set(cache_key, result, ttl=self.query_ttl, namespace=self.query_namespace)
```

##### 4.1.3 AIService Update
**File:** `youtrack_mcp/ai/service.py`

```python
# OLD CODE
def __init__(self, llm_client, ...):
    self.query_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour
    self.error_cache = TTLCache(maxsize=500, ttl=1800)  # 30 minutes

# NEW CODE
def __init__(self, llm_client, cache_manager: UnifiedCacheManager, ...):
    self.cache = cache_manager
    self.llm_client = llm_client
    # ... other initialization

async def translate_nl_to_yql(self, natural_query: str, project_context: Optional[str] = None):
    # Check cache
    cache_key = f"{natural_query}:{project_context}"
    cached_response = await self.cache.get(cache_key, namespace="ai_yql_translation")
    if cached_response:
        logger.debug("Using cached YQL translation", query=natural_query[:50])
        return cached_response
    
    # ... perform translation ...
    
    # Cache result
    await self.cache.set(cache_key, response, ttl=3600, namespace="ai_yql_translation")
    return response
```

##### 4.1.4 MCPResources Update
**File:** `youtrack_mcp/mcp_resources.py`

```python
# OLD CODE
def __init__(self):
    self._cache = {}
    self._cache_ttl = 300  # 5 minutes cache

def _is_cache_valid(self, key: str) -> bool:
    # Manual TTL validation

# NEW CODE
def __init__(self, cache_manager: UnifiedCacheManager):
    self.cache = cache_manager
    self.cache_ttl = 300  # 5 minutes
    self.cache_namespace = "mcp_resources"

async def get_cached_resource(self, resource_key: str) -> Optional[dict]:
    return await self.cache.get(resource_key, namespace=self.cache_namespace)

async def cache_resource(self, resource_key: str, data: dict) -> None:
    await self.cache.set(resource_key, data, ttl=self.cache_ttl, namespace=self.cache_namespace)
```

##### 4.1.5 Dependency Injection Updates
**File:** `main.py` or initialization module

```python
from youtrack_mcp.cache.manager import UnifiedCacheManager, CacheStrategy
from youtrack_mcp.config import config

# Initialize unified cache based on configuration
cache_config = config.cache
cache_manager = UnifiedCacheManager(
    strategy=cache_config.strategy,
    memory_config={
        "max_size": cache_config.memory_size,
        "default_ttl": cache_config.memory_ttl
    },
    sqlite_config={
        "db_path": cache_config.sqlite_path,
        "default_ttl": cache_config.sqlite_ttl
    },
    redis_config={
        "host": cache_config.redis_host,
        "port": cache_config.redis_port,
        "password": cache_config.redis_password,
        "default_ttl": cache_config.redis_ttl
    } if cache_config.strategy in [CacheStrategy.REDIS, CacheStrategy.TIERED] else None
)

# Pass cache_manager to all components that need caching
error_handler = ErrorHandler(cache_manager=cache_manager)
search_tools = AdvancedSearchTools(cache_manager=cache_manager)
ai_service = AIService(llm_client=llm_client, cache_manager=cache_manager)
mcp_resources = MCPResources(cache_manager=cache_manager)
```

#### 4.2 Removal of Old Cache Code

After updating all cache consumers, remove the old caching code:

1. Remove direct `TTLCache` and `LRUCache` imports from modules
2. Remove manual cache validation methods
3. Remove cache timestamp tracking code
4. Update tests to use the new async cache API

### Phase 5: Testing Strategy

#### 5.1 Unit Tests
**File:** `tests/unit/test_cache_backends.py`

```python
import pytest
import asyncio
import tempfile
from pathlib import Path
from youtrack_mcp.cache.backends import MemoryCacheBackend, SQLiteCacheBackend

class TestMemoryBackend:
    @pytest.mark.asyncio
    async def test_basic_operations(self):
        cache = MemoryCacheBackend(max_size=10, default_ttl=60)
        
        # Test set and get
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"
        
        # Test missing key
        assert await cache.get("missing") is None
        
        # Test delete
        await cache.delete("key1")
        assert await cache.get("key1") is None
    
    @pytest.mark.asyncio
    async def test_namespaces(self):
        cache = MemoryCacheBackend()
        
        await cache.set("key", "value1", namespace="ns1")
        await cache.set("key", "value2", namespace="ns2")
        
        assert await cache.get("key", "ns1") == "value1"
        assert await cache.get("key", "ns2") == "value2"
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        cache = MemoryCacheBackend(default_ttl=1)
        
        await cache.set("key", "value")
        assert await cache.get("key") == "value"
        
        await asyncio.sleep(1.1)
        assert await cache.get("key") is None

class TestSQLiteBackend:
    @pytest.mark.asyncio
    async def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Create cache and set value
            cache1 = SQLiteCacheBackend(db_path=db_path)
            await cache1.set("key", "value", ttl=60)
            
            # Create new instance and verify persistence
            cache2 = SQLiteCacheBackend(db_path=db_path)
            assert await cache2.get("key") == "value"
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCacheBackend(db_path=Path(tmpdir) / "test.db")
            
            # Set with very short TTL
            await cache.set("expired", "value", ttl=1)
            await cache.set("valid", "value", ttl=60)
            
            await asyncio.sleep(1.1)
            
            # Cleanup and verify
            deleted = await cache.cleanup_expired()
            assert deleted == 1
            assert await cache.get("expired") is None
            assert await cache.get("valid") == "value"
```

#### 5.2 Integration Tests
**File:** `tests/integration/test_unified_cache.py`

```python
import pytest
from youtrack_mcp.cache.manager import UnifiedCacheManager, CacheStrategy

class TestUnifiedCacheManager:
    @pytest.mark.asyncio
    async def test_hybrid_strategy(self):
        """Test memory + SQLite hybrid caching."""
        manager = UnifiedCacheManager(strategy=CacheStrategy.HYBRID)
        
        # Set value
        await manager.set("test_key", {"data": "test"}, ttl=60)
        
        # Should retrieve from memory (fast)
        value = await manager.get("test_key")
        assert value == {"data": "test"}
        
        # Check both backends have the value
        memory_stats = await manager.memory.get_stats()
        assert memory_stats["sets"] == 1
        
        # Clear memory cache
        await manager.memory.clear()
        
        # Should still retrieve from SQLite
        value = await manager.get("test_key")
        assert value == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_cache_backfill(self):
        """Test that cache backfills faster layers."""
        manager = UnifiedCacheManager(strategy=CacheStrategy.HYBRID)
        
        # Set only in SQLite
        await manager.sqlite.set("key", "value", ttl=60)
        
        # Get should retrieve from SQLite and backfill memory
        value = await manager.get("key")
        assert value == "value"
        
        # Now should be in memory
        assert await manager.memory.get("key") == "value"
```

#### 5.3 Performance Tests
**File:** `tests/performance/test_cache_performance.py`

```python
import pytest
import asyncio
import time
from youtrack_mcp.cache.manager import UnifiedCacheManager, CacheStrategy

class TestCachePerformance:
    @pytest.mark.asyncio
    async def test_memory_speed(self):
        """Benchmark memory cache performance."""
        manager = UnifiedCacheManager(strategy=CacheStrategy.MEMORY)
        
        # Write performance
        start = time.time()
        for i in range(1000):
            await manager.set(f"key_{i}", f"value_{i}")
        write_time = time.time() - start
        
        # Read performance
        start = time.time()
        for i in range(1000):
            await manager.get(f"key_{i}")
        read_time = time.time() - start
        
        print(f"Memory - Write: {write_time:.3f}s, Read: {read_time:.3f}s")
        assert write_time < 1.0  # Should be very fast
        assert read_time < 0.5
    
    @pytest.mark.asyncio
    async def test_sqlite_speed(self):
        """Benchmark SQLite cache performance."""
        manager = UnifiedCacheManager(strategy=CacheStrategy.SQLITE)
        
        # Batch write performance
        start = time.time()
        tasks = []
        for i in range(100):
            tasks.append(manager.set(f"key_{i}", f"value_{i}"))
        await asyncio.gather(*tasks)
        write_time = time.time() - start
        
        print(f"SQLite - Batch write 100 items: {write_time:.3f}s")
        assert write_time < 5.0  # Reasonable for disk I/O
```

### Phase 6: Linting and Code Quality

#### 6.1 Linting Configuration
**File:** `.flake8`
```ini
[flake8]
max-line-length = 120
exclude = .git,__pycache__,build,dist,.venv
ignore = E203,W503  # Black compatibility
```

**File:** `pyproject.toml` (additions)
```toml
[tool.black]
line-length = 120
target-version = ['py310']

[tool.isort]
profile = "black"
line_length = 120

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

#### 6.2 Pre-commit Hooks
**File:** `.pre-commit-config.yaml`
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
        args: [--line-length=120]
  
  - repo: https://github.com/pycqa/isort
    rev: 5.13.0
    hooks:
      - id: isort
        args: [--profile=black, --line-length=120]
  
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=120, --ignore=E203,W503]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-redis, types-cachetools]
```

#### 6.3 CI/CD Integration
**File:** `.github/workflows/quality.yml`
```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          uv sync --all-extras
          uv add redis pytest-cov
      
      - name: Run black
        run: black --check youtrack_mcp tests
      
      - name: Run isort
        run: isort --check youtrack_mcp tests
      
      - name: Run flake8
        run: flake8 youtrack_mcp tests
      
      - name: Run mypy
        run: mypy youtrack_mcp
  
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          uv sync --all-extras
          uv add redis pytest-cov
      
      - name: Run tests with coverage
        run: |
          pytest --cov=youtrack_mcp/cache --cov-report=xml tests/
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Phase 7: Documentation

#### 7.1 Cache Usage Guide
**File:** `docs/cache-usage.md`

```markdown
# Cache Usage Guide

## Quick Start

### Basic Usage
```python
from youtrack_mcp.cache.manager import UnifiedCacheManager, CacheStrategy

# Initialize with sqlite_hybrid strategy (recommended)
cache = UnifiedCacheManager(strategy=CacheStrategy.SQLITE_HYBRID)

# Store value
await cache.set("my_key", {"data": "value"}, ttl=300, namespace="my_namespace")

# Retrieve value
value = await cache.get("my_key", namespace="my_namespace")

# Delete value
await cache.delete("my_key", namespace="my_namespace")
```

### Configuration via Environment Variables
```bash
# Cache strategy
export CACHE_STRATEGY=sqlite_hybrid  # off, sqlite_hybrid, redis

# Memory cache (for sqlite_hybrid)
export CACHE_MEMORY_SIZE=1000
export CACHE_MEMORY_TTL=300

# SQLite cache (for sqlite_hybrid)
export CACHE_SQLITE_PATH=/path/to/cache.db
export CACHE_SQLITE_TTL=3600

# Redis cache (for redis strategy)
export CACHE_REDIS_HOST=localhost
export CACHE_REDIS_PORT=6379
export CACHE_REDIS_PASSWORD=secret
export CACHE_REDIS_TTL=3600
```

### ID Resolution with Caching
```python
from youtrack_mcp.utils.id_resolver import IDResolver

# Initialize resolver with cache
resolver = IDResolver(client, cache_manager)

# Resolve project short name to ID (cached)
project_id = await resolver.resolve_project_id("ACC")  # Returns "63-13"

# Warm cache on startup
counts = await resolver.warm_cache()
print(f"Warmed cache with {counts['projects']} projects, {counts['users']} users")
```

## Cache Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| OFF | No caching | Testing/debugging |
| SQLITE_HYBRID | Memory + SQLite | Default production |
| REDIS | Redis only | Distributed systems |

## Monitoring

```python
# Get cache statistics
stats = await cache.get_stats()
print(f"Strategy: {stats['strategy']}")

# Cleanup expired entries
deleted = await cache.cleanup_expired()
print(f"Cleaned up {deleted} expired entries")
```

## Implementation Checklist

- [ ] Create cache package structure
- [ ] Implement abstract base backend class
- [ ] Implement memory backend with TTLCache
- [ ] Implement SQLite backend with WAL mode
- [ ] Implement Redis backend (optional dependency)
- [ ] Create unified cache manager
- [ ] Update configuration classes
- [ ] Integrate ID resolver with cache
- [ ] Migrate existing cache implementations
- [ ] Write unit tests for all backends
- [ ] Write integration tests for unified manager
- [ ] Write performance benchmarks
- [ ] Configure linting tools (black, flake8, mypy)
- [ ] Set up pre-commit hooks
- [ ] Configure CI/CD pipeline
- [ ] Write usage documentation
- [ ] Deploy to staging environment
- [ ] Monitor performance metrics
- [ ] Production rollout

## Success Metrics

1. **Functional Targets**
   - Caching works across process restarts (SQLite/Redis)
   - ID resolution uses caching effectively
   - Significant reduction in YouTrack API calls
   - All existing cache consumers migrated to unified system

2. **Reliability Targets**
   - Zero data loss on process restart with persistent backends
   - Automatic expired entry cleanup
   - Graceful handling when cache backend unavailable

3. **Code Quality Targets**
   - All code passes linting (black, flake8, mypy)
   - Comprehensive test coverage for cache package

## Risk Mitigation

1. **Redis Unavailability**: Make Redis an optional dependency with runtime detection
2. **SQLite Lock Contention**: Use WAL mode and connection pooling
3. **Memory Leaks**: Enforce max size limits and TTL on all caches
4. **Migration Issues**: Update all cache consumers directly to the new API with comprehensive testing

## Conclusion

This comprehensive caching implementation will provide the YouTrack MCP server with a robust, multiprocess-safe caching system supporting multiple backends. The hybrid approach (Memory + SQLite) offers the best balance for most deployments, while Redis support enables enterprise-scale distributed caching when needed.