"""Unit tests for memory cache backend."""

import asyncio

import pytest

from youtrack_mcp.cache.backends.memory import MemoryCacheBackend


@pytest.mark.asyncio
class TestMemoryBackend:
    """Test memory cache backend."""

    async def test_basic_operations(self):
        """Test basic cache operations."""
        cache = MemoryCacheBackend(max_size=10, default_ttl=60)

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

    async def test_namespaces(self):
        """Test namespace isolation."""
        cache = MemoryCacheBackend()

        # Set same key in different namespaces
        await cache.set("key", "value1", namespace="ns1")
        await cache.set("key", "value2", namespace="ns2")

        # Values should be isolated by namespace
        assert await cache.get("key", "ns1") == "value1"
        assert await cache.get("key", "ns2") == "value2"
        assert await cache.get("key", "default") is None

    async def test_exists(self):
        """Test existence check."""
        cache = MemoryCacheBackend()

        await cache.set("key", "value")
        assert await cache.exists("key") is True
        assert await cache.exists("missing") is False

    async def test_clear(self):
        """Test cache clearing."""
        cache = MemoryCacheBackend()

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
        cache = MemoryCacheBackend()

        # Initial stats
        stats = await cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["sets"] == 0
        assert stats["deletes"] == 0

        # Perform operations
        await cache.set("key", "value")
        await cache.get("key")  # hit
        await cache.get("missing")  # miss
        await cache.delete("key")

        # Check updated stats
        stats = await cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["deletes"] == 1

    async def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = MemoryCacheBackend(default_ttl=0.1)  # 100ms TTL

        await cache.set("key", "value")
        assert await cache.get("key") == "value"

        # Wait for expiration
        await asyncio.sleep(0.15)
        assert await cache.get("key") is None

    async def test_max_size(self):
        """Test cache size limit."""
        cache = MemoryCacheBackend(max_size=2, default_ttl=60)

        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # Both should be retrievable
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"

        # Add third item (should evict oldest)
        await cache.set("key3", "value3")

        # One of the first two should be evicted (LRU behavior)
        # Note: TTLCache uses LRU when at capacity
        assert await cache.get("key3") == "value3"

    async def test_complex_values(self):
        """Test storing complex data types."""
        cache = MemoryCacheBackend()

        # Store different types
        await cache.set("dict", {"key": "value", "number": 42})
        await cache.set("list", [1, 2, 3])
        await cache.set("nested", {"data": {"items": [1, 2, 3]}})

        # Retrieve and verify
        assert await cache.get("dict") == {"key": "value", "number": 42}
        assert await cache.get("list") == [1, 2, 3]
        assert await cache.get("nested") == {"data": {"items": [1, 2, 3]}}