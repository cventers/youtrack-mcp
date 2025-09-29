"""SQLite-based persistent cache with multiprocess support."""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .base import CacheBackend


class SQLiteCacheBackend(CacheBackend):
    """SQLite-based persistent cache with multiprocess support."""

    def __init__(self, db_path: Optional[Path] = None, default_ttl: int = 300):
        """Initialize SQLite cache backend.

        Args:
            db_path: Path to SQLite database file
            default_ttl: Default TTL in seconds
        """
        self.db_path = db_path or Path.home() / ".youtrack-mcp" / "cache.db"
        self.default_ttl = default_ttl
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "clears": 0}

    def _init_db(self):
        """Initialize database with WAL mode for multiprocess access."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            # Enable Write-Ahead Logging for better multiprocess support
            conn.execute("PRAGMA journal_mode=WAL")
            # Balance speed and safety
            conn.execute("PRAGMA synchronous=NORMAL")
            # Create cache table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    PRIMARY KEY (namespace, key)
                )
            """
            )
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace ON cache(namespace)")
            conn.commit()
        finally:
            conn.close()

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value)

    def _deserialize(self, value_json: str) -> Any:
        """Deserialize JSON string to value."""
        return json.loads(value_json)

    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Retrieve value from cache with TTL check."""
        conn = sqlite3.connect(str(self.db_path))
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

        conn = sqlite3.connect(str(self.db_path))
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
        conn = sqlite3.connect(str(self.db_path))
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
        conn = sqlite3.connect(str(self.db_path))
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
        conn = sqlite3.connect(str(self.db_path))
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
        conn = sqlite3.connect(str(self.db_path))
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
        conn = sqlite3.connect(str(self.db_path))
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