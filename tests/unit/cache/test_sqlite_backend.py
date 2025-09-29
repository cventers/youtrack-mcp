"""Unit tests for SQLite cache backend."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from youtrack_mcp.cache.backends.sqlite import SQLiteCacheBackend


@pytest.mark.asyncio
class TestSQLiteBackend:
    """Test SQLite cache backend."""

    async def test_basic_operations(self):
        """Test basic cache operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCacheBackend(db_path=Path(tmpdir) / "test.db", default_ttl=60)

            # Test set and get
            await cache.set("key1", "value1")
            assert await cache.get("key1") == "value1"

            # Test missing key
            assert await cache.get("missing") is None

            # Test delete
            assert await cache.delete("key1") is True
            assert await cache.get("key1") is None

            # Test delete missing key
            assert await cache.delete("missing") is False

    async def test_persistence(self):
        """Test data persistence across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create cache and set value
            cache1 = SQLiteCacheBackend(db_path=db_path, default_ttl=60)
            await cache1.set("key", "value")
            await cache1.set("dict", {"data": "test"})

            # Create new instance and verify persistence
            cache2 = SQLiteCacheBackend(db_path=db_path)
            assert await cache2.get("key") == "value"
            assert await cache2.get("dict") == {"data": "test"}

    async def test_namespaces(self):
        """Test namespace isolation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCacheBackend(db_path=Path(tmpdir) / "test.db")

            # Set same key in different namespaces
            await cache.set("key", "value1", namespace="ns1")
            await cache.set("key", "value2", namespace="ns2")

            # Values should be isolated by namespace
            assert await cache.get("key", "ns1") == "value1"
            assert await cache.get("key", "ns2") == "value2"
            assert await cache.get("key", "default") is None

    async def test_ttl_expiration(self):
        """Test TTL expiration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCacheBackend(db_path=Path(tmpdir) / "test.db", default_ttl=10)

            # Set with 2 second TTL to ensure it's not immediately expired
            await cache.set("expired", "value", ttl=2)

            # Should still be available immediately
            result = await cache.get("expired")
            assert result == "value", f"Expected 'value' but got {result}"

            # Wait for expiration
            await asyncio.sleep(2.5)

            # Should now be expired
            result = await cache.get("expired")
            assert result is None, f"Expected None but got {result}"

    async def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCacheBackend(db_path=Path(tmpdir) / "test.db")

            # Set with different TTLs
            await cache.set("expired1", "value", ttl=0.1)
            await cache.set("expired2", "value", ttl=0.1)
            await cache.set("valid", "value", ttl=60)

            await asyncio.sleep(0.15)

            # Cleanup and verify
            deleted = await cache.cleanup_expired()
            assert deleted == 2
            assert await cache.get("expired1") is None
            assert await cache.get("expired2") is None
            assert await cache.get("valid") == "value"

    async def test_exists(self):
        """Test existence check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCacheBackend(db_path=Path(tmpdir) / "test.db")

            await cache.set("key", "value", ttl=60)
            assert await cache.exists("key") is True
            assert await cache.exists("missing") is False

            # Test with expired key
            await cache.set("expired", "value", ttl=0.1)
            await asyncio.sleep(0.15)
            assert await cache.exists("expired") is False

    async def test_clear(self):
        """Test cache clearing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCacheBackend(db_path=Path(tmpdir) / "test.db")

            # Set values in multiple namespaces
            await cache.set("key1", "value1", namespace="ns1")
            await cache.set("key2", "value2", namespace="ns1")
            await cache.set("key3", "value3", namespace="ns2")

            # Clear specific namespace
            count = await cache.clear("ns1")
            assert count == 2
            assert await cache.get("key1", "ns1") is None
            assert await cache.get("key2", "ns1") is None
            assert await cache.get("key3", "ns2") == "value3"

            # Clear all
            await cache.set("key4", "value4", namespace="ns3")
            count = await cache.clear()
            assert count == 2  # ns2 and ns3
            assert await cache.get("key3", "ns2") is None
            assert await cache.get("key4", "ns3") is None

    async def test_stats(self):
        """Test statistics tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            cache = SQLiteCacheBackend(db_path=db_path)

            # Set some data
            await cache.set("key1", "value1", namespace="ns1")
            await cache.set("key2", "value2", namespace="ns1")
            await cache.set("key3", "value3", namespace="ns2")
            await cache.set("expired", "value", ttl=0.1)

            await asyncio.sleep(0.15)

            # Get stats
            stats = await cache.get_stats()
            assert stats["total_items"] == 4
            assert stats["expired_items"] == 1
            # Should have 3 namespaces: ns1, ns2, and default (for expired)
            assert stats["namespaces"] == 3
            assert stats["db_path"] == str(db_path)
            assert stats["db_size_bytes"] > 0

    async def test_complex_values(self):
        """Test storing complex data types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCacheBackend(db_path=Path(tmpdir) / "test.db")

            # Store different types
            await cache.set("dict", {"key": "value", "number": 42})
            await cache.set("list", [1, 2, 3])
            await cache.set("nested", {"data": {"items": [1, 2, 3]}})
            await cache.set("unicode", "Hello 世界 🌍")

            # Retrieve and verify
            assert await cache.get("dict") == {"key": "value", "number": 42}
            assert await cache.get("list") == [1, 2, 3]
            assert await cache.get("nested") == {"data": {"items": [1, 2, 3]}}
            assert await cache.get("unicode") == "Hello 世界 🌍"

    async def test_concurrent_access(self):
        """Test concurrent access to cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCacheBackend(db_path=Path(tmpdir) / "test.db")

            # Concurrent writes
            async def write_task(i):
                await cache.set(f"key{i}", f"value{i}")

            await asyncio.gather(*[write_task(i) for i in range(10)])

            # Concurrent reads
            async def read_task(i):
                return await cache.get(f"key{i}")

            results = await asyncio.gather(*[read_task(i) for i in range(10)])
            for i, result in enumerate(results):
                assert result == f"value{i}"