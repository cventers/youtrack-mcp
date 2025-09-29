"""SQLite-based persistent cache with multiprocess support."""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from .base import CacheBackend


class SQLiteCacheBackend(CacheBackend):
    """SQLite-based persistent cache with multiprocess support."""

    # Optimization presets
    OPTIMIZATION_PRESETS = {
        "performance": {
            "synchronous": "OFF",
            "journal_mode": "WAL",
            "cache_size_kb": 10000,  # 10MB
            "mmap_size_mb": 30,  # 30MB
            "temp_store": "MEMORY",
            "page_size": 8192,
            "busy_timeout_ms": 5000,
        },
        "balanced": {
            "synchronous": "NORMAL",
            "journal_mode": "WAL",
            "cache_size_kb": 5000,  # 5MB
            "mmap_size_mb": 10,  # 10MB
            "temp_store": "DEFAULT",
            "page_size": 4096,
            "busy_timeout_ms": 3000,
        },
        "safe": {
            "synchronous": "FULL",
            "journal_mode": "WAL",
            "cache_size_kb": 2000,  # 2MB
            "mmap_size_mb": 0,  # Disabled
            "temp_store": "FILE",
            "page_size": 4096,
            "busy_timeout_ms": 1000,
        },
    }

    def __init__(
        self,
        db_path: Optional[Path] = None,
        default_ttl: int = 300,
        optimization_mode: Literal["performance", "balanced", "safe"] = "balanced",
        **pragma_overrides,
    ):
        """Initialize SQLite cache backend.

        Args:
            db_path: Path to SQLite database file
            default_ttl: Default TTL in seconds
            optimization_mode: Optimization preset to use
            **pragma_overrides: Override specific pragma settings
        """
        self.db_path = db_path or Path.home() / ".youtrack-mcp" / "cache.db"
        self.default_ttl = default_ttl
        self.optimization_mode = optimization_mode

        # Get base settings from preset
        self.pragma_settings = self.OPTIMIZATION_PRESETS[optimization_mode].copy()

        # Apply any overrides
        for key, value in pragma_overrides.items():
            if key.startswith("sqlite_") and value is not None:
                pragma_key = key.replace("sqlite_", "")
                self.pragma_settings[pragma_key] = value

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "clears": 0}

    def _init_db(self):
        """Initialize database with configurable optimizations."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            # Apply journal mode (WAL for concurrency)
            conn.execute(f"PRAGMA journal_mode={self.pragma_settings['journal_mode']}")

            # Apply synchronous setting
            conn.execute(f"PRAGMA synchronous={self.pragma_settings['synchronous']}")

            # Set page cache size
            cache_kb = self.pragma_settings["cache_size_kb"]
            if cache_kb > 0:
                conn.execute(f"PRAGMA cache_size=-{cache_kb}")

            # Set memory-mapped I/O
            mmap_mb = self.pragma_settings["mmap_size_mb"]
            if mmap_mb > 0:
                conn.execute(f"PRAGMA mmap_size={mmap_mb * 1024 * 1024}")

            # Set temp store location
            if self.pragma_settings["temp_store"] != "DEFAULT":
                conn.execute(f"PRAGMA temp_store={self.pragma_settings['temp_store']}")

            # Set page size (only works on new databases)
            conn.execute(f"PRAGMA page_size={self.pragma_settings['page_size']}")

            # Set busy timeout
            conn.execute(f"PRAGMA busy_timeout={self.pragma_settings['busy_timeout_ms']}")

            # Standard optimizations for all modes
            conn.execute("PRAGMA optimize")
            conn.execute("PRAGMA automatic_index=ON")
            conn.execute("PRAGMA locking_mode=NORMAL")

            # Create cache table with optimizations
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    PRIMARY KEY (namespace, key)
                ) WITHOUT ROWID  -- More efficient for our use case
            """
            )

            # Create optimized indexes
            # Covering index for expiration queries
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires_covering ON cache(expires_at, namespace, key)"
            )
            # Index for namespace queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace ON cache(namespace, key)")

            conn.commit()
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get an optimized database connection.

        Returns a connection with performance pragmas applied.
        Each connection needs its own pragmas set.
        """
        conn = sqlite3.connect(str(self.db_path))
        # Apply per-connection optimizations based on configuration
        conn.execute(f"PRAGMA synchronous={self.pragma_settings['synchronous']}")

        cache_kb = self.pragma_settings["cache_size_kb"]
        if cache_kb > 0:
            conn.execute(f"PRAGMA cache_size=-{cache_kb}")

        if self.pragma_settings["temp_store"] != "DEFAULT":
            conn.execute(f"PRAGMA temp_store={self.pragma_settings['temp_store']}")

        mmap_mb = self.pragma_settings["mmap_size_mb"]
        if mmap_mb > 0:
            conn.execute(f"PRAGMA mmap_size={mmap_mb * 1024 * 1024}")

        conn.execute(f"PRAGMA busy_timeout={self.pragma_settings['busy_timeout_ms']}")
        return conn

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value)

    def _deserialize(self, value_json: str) -> Any:
        """Deserialize JSON string to value."""
        return json.loads(value_json)

    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Retrieve value from cache with TTL check."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT value, expires_at FROM cache WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            row = cursor.fetchone()

            if row:
                value_json, expires_at = row
                if expires_at > time.time():
                    self.stats["hits"] += 1
                    return self._deserialize(value_json)
                else:
                    # Expired, delete it
                    conn.execute(
                        "DELETE FROM cache WHERE namespace = ? AND key = ?", (namespace, key)
                    )
                    conn.commit()
                    self.stats["misses"] += 1
            else:
                self.stats["misses"] += 1
            return None
        finally:
            conn.close()

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = "default"
    ) -> None:
        """Store value in cache with TTL."""
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl
        value_json = self._serialize(value)

        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO cache (namespace, key, value, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (namespace, key, value_json, time.time(), expires_at),
            )
            conn.commit()
            self.stats["sets"] += 1
        finally:
            conn.close()

    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete key from cache."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM cache WHERE namespace = ? AND key = ?", (namespace, key)
            )
            deleted = cursor.rowcount > 0
            conn.commit()
            if deleted:
                self.stats["deletes"] += 1
            return deleted
        finally:
            conn.close()

    async def clear(self, namespace: Optional[str] = None) -> int:
        """Clear cache, optionally by namespace."""
        conn = self._get_connection()
        try:
            if namespace:
                cursor = conn.execute("DELETE FROM cache WHERE namespace = ?", (namespace,))
            else:
                cursor = conn.execute("DELETE FROM cache")
            deleted = cursor.rowcount
            conn.commit()
            self.stats["clears"] += 1
            return deleted
        finally:
            conn.close()

    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in cache."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM cache WHERE namespace = ? AND key = ? AND expires_at > ?",
                (namespace, key, time.time()),
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        conn = self._get_connection()
        try:
            # Count total items
            cursor = conn.execute("SELECT COUNT(*) FROM cache")
            total_items = cursor.fetchone()[0]

            # Count namespaces
            cursor = conn.execute("SELECT COUNT(DISTINCT namespace) FROM cache")
            namespace_count = cursor.fetchone()[0]

            # Count expired items
            cursor = conn.execute("SELECT COUNT(*) FROM cache WHERE expires_at <= ?", (time.time(),))
            expired_items = cursor.fetchone()[0]

            # Get database file size
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

            return {
                **self.stats,
                "total_items": total_items,
                "expired_items": expired_items,
                "namespaces": namespace_count,
                "db_path": str(self.db_path),
                "db_size_bytes": db_size,
                "default_ttl": self.default_ttl,
            }
        finally:
            conn.close()

    async def cleanup_expired(self) -> int:
        """Remove expired entries from database."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))
            deleted = cursor.rowcount
            conn.commit()
            # Also run VACUUM occasionally to reclaim space
            if deleted > 100:  # Only vacuum if we deleted many entries
                conn.execute("VACUUM")
            return deleted
        finally:
            conn.close()