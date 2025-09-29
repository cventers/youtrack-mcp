"""Integration tests for unified cache manager."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from youtrack_mcp.cache.manager import CacheStrategy, UnifiedCacheManager


@pytest.mark.asyncio
class TestUnifiedCacheManager:
    """Test unified cache manager."""

    async def test_off_strategy(self):
        """Test OFF strategy (no caching)."""
        manager = UnifiedCacheManager(strategy=CacheStrategy.OFF)

        # All operations should be no-ops
        await manager.set("key", "value")
        assert await manager.get("key") is None
        assert await manager.exists("key") is False
        assert await manager.delete("key") is False
        assert await manager.clear() == 0

        stats = await manager.get_stats()
        assert stats["strategy"] == "off"
        assert stats["caching_disabled"] is True

    async def test_memory_strategy(self):
        """Test MEMORY strategy."""
        manager = UnifiedCacheManager(
            strategy=CacheStrategy.MEMORY, memory_config={"max_size": 10, "default_ttl": 60}
        )

        # Basic operations
        await manager.set("key", "value")
        assert await manager.get("key") == "value"
        assert await manager.exists("key") is True

        # Delete
        assert await manager.delete("key") is True
        assert await manager.get("key") is None

        # Stats
        stats = await manager.get_stats()
        assert stats["strategy"] == "memory"
        assert "memory" in stats["backends"]

    async def test_sqlite_strategy(self):
        """Test SQLITE strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UnifiedCacheManager(
                strategy=CacheStrategy.SQLITE,
                sqlite_config={"db_path": Path(tmpdir) / "cache.db", "default_ttl": 60},
            )

            # Basic operations
            await manager.set("key", {"data": "test"})
            assert await manager.get("key") == {"data": "test"}
            assert await manager.exists("key") is True

            # Persistence check - create new manager
            manager2 = UnifiedCacheManager(
                strategy=CacheStrategy.SQLITE,
                sqlite_config={"db_path": Path(tmpdir) / "cache.db"},
            )
            assert await manager2.get("key") == {"data": "test"}

    async def test_sqlite_hybrid_strategy(self):
        """Test SQLITE_HYBRID strategy (memory + SQLite)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UnifiedCacheManager(
                strategy=CacheStrategy.SQLITE_HYBRID,
                memory_config={"max_size": 10, "default_ttl": 30},
                sqlite_config={"db_path": Path(tmpdir) / "cache.db", "default_ttl": 60},
            )

            # Set value (should go to both backends)
            await manager.set("test_key", {"data": "test"})

            # Should retrieve from memory (fast)
            value = await manager.get("test_key")
            assert value == {"data": "test"}

            # Check both backends have the value
            memory_value = await manager.memory.get("test_key")
            sqlite_value = await manager.sqlite.get("test_key")
            assert memory_value == {"data": "test"}
            assert sqlite_value == {"data": "test"}

            # Clear memory cache
            await manager.memory.clear()
            memory_value = await manager.memory.get("test_key")
            assert memory_value is None

            # Should still retrieve from SQLite and backfill memory
            value = await manager.get("test_key")
            assert value == {"data": "test"}

            # Check memory was backfilled
            memory_value = await manager.memory.get("test_key")
            assert memory_value == {"data": "test"}

    async def test_cache_backfill(self):
        """Test cache backfill in hybrid strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UnifiedCacheManager(
                strategy=CacheStrategy.SQLITE_HYBRID,
                sqlite_config={"db_path": Path(tmpdir) / "cache.db"},
            )

            # Set only in SQLite (simulate memory miss)
            await manager.sqlite.set("key", {"value": "from_sqlite"}, ttl=60)

            # Memory should not have it yet
            assert await manager.memory.get("key") is None

            # Get should retrieve from SQLite and backfill memory
            value = await manager.get("key")
            assert value == {"value": "from_sqlite"}

            # Now memory should have it
            assert await manager.memory.get("key") == {"value": "from_sqlite"}

    async def test_namespace_operations(self):
        """Test namespace operations across strategies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UnifiedCacheManager(
                strategy=CacheStrategy.SQLITE_HYBRID,
                sqlite_config={"db_path": Path(tmpdir) / "cache.db"},
            )

            # Set in different namespaces
            await manager.set("key", "value1", namespace="ns1")
            await manager.set("key", "value2", namespace="ns2")

            # Get from different namespaces
            assert await manager.get("key", "ns1") == "value1"
            assert await manager.get("key", "ns2") == "value2"
            assert await manager.get("key", "default") is None

            # Clear specific namespace
            count = await manager.clear("ns1")
            assert count > 0
            assert await manager.get("key", "ns1") is None
            assert await manager.get("key", "ns2") == "value2"

    async def test_concurrent_operations(self):
        """Test concurrent cache operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UnifiedCacheManager(
                strategy=CacheStrategy.SQLITE_HYBRID,
                sqlite_config={"db_path": Path(tmpdir) / "cache.db"},
            )

            # Concurrent writes
            async def write_task(i):
                await manager.set(f"key{i}", f"value{i}")

            await asyncio.gather(*[write_task(i) for i in range(20)])

            # Concurrent reads
            async def read_task(i):
                return await manager.get(f"key{i}")

            results = await asyncio.gather(*[read_task(i) for i in range(20)])
            for i, result in enumerate(results):
                assert result == f"value{i}"

    async def test_cleanup_expired(self):
        """Test cleanup of expired entries in SQLite backend.

        Note: Memory backend (TTLCache) doesn't support per-item TTL,
        so we test SQLite-only strategy here for accurate TTL behavior.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UnifiedCacheManager(
                strategy=CacheStrategy.SQLITE,  # Use SQLite-only for accurate TTL
                sqlite_config={"db_path": Path(tmpdir) / "cache.db"},
            )

            # Set with 1 second TTL
            await manager.set("expired", "value", ttl=1)
            await manager.set("valid", "value", ttl=60)

            await asyncio.sleep(1.5)

            # Cleanup
            results = await manager.cleanup_expired()
            assert "sqlite" in results
            assert results["sqlite"] >= 1  # At least one expired entry cleaned

            # Expired should be gone, valid should remain
            assert await manager.get("expired") is None
            assert await manager.get("valid") == "value"

    async def test_stats_aggregation(self):
        """Test statistics aggregation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UnifiedCacheManager(
                strategy=CacheStrategy.SQLITE_HYBRID,
                sqlite_config={"db_path": Path(tmpdir) / "cache.db"},
            )

            # Perform some operations
            await manager.set("key1", "value1")
            await manager.set("key2", "value2")
            await manager.get("key1")
            await manager.get("missing")
            await manager.delete("key2")

            # Get aggregated stats
            stats = await manager.get_stats()
            assert stats["strategy"] == "sqlite_hybrid"
            assert "backends" in stats
            assert "memory" in stats["backends"]
            assert "sqlite" in stats["backends"]

            # Both backends should have stats
            memory_stats = stats["backends"]["memory"]
            sqlite_stats = stats["backends"]["sqlite"]
            assert memory_stats["sets"] >= 2
            assert sqlite_stats["sets"] >= 2

    async def test_context_manager(self):
        """Test async context manager support."""
        with tempfile.TemporaryDirectory() as tmpdir:
            async with UnifiedCacheManager(
                strategy=CacheStrategy.SQLITE_HYBRID,
                sqlite_config={"db_path": Path(tmpdir) / "cache.db"},
            ) as manager:
                await manager.set("key", "value")
                assert await manager.get("key") == "value"

            # Manager should be closed after context exit
            # (No direct way to test this without accessing internals)

    async def test_backend_filtering(self):
        """Test setting values in specific backends only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UnifiedCacheManager(
                strategy=CacheStrategy.SQLITE_HYBRID,
                sqlite_config={"db_path": Path(tmpdir) / "cache.db"},
            )

            # Set only in memory backend
            await manager.set("memory_only", "value", backends=["memory"])

            # Check it's only in memory
            assert await manager.memory.get("memory_only") == "value"
            assert await manager.sqlite.get("memory_only") is None

            # Set only in SQLite backend
            await manager.set("sqlite_only", "value", backends=["sqlite"])

            # Check it's only in SQLite
            assert await manager.memory.get("sqlite_only") is None
            assert await manager.sqlite.get("sqlite_only") == "value"