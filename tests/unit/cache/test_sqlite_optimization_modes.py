"""Test SQLite optimization modes."""

import asyncio
import sqlite3
import tempfile
from pathlib import Path

import pytest

from youtrack_mcp.cache.backends.sqlite import SQLiteCacheBackend


@pytest.mark.asyncio
class TestSQLiteOptimizationModes:
    """Test different SQLite optimization modes."""

    async def test_performance_mode(self):
        """Test performance optimization mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCacheBackend(
                db_path=Path(tmpdir) / "test.db",
                optimization_mode="performance"
            )

            # Check that performance settings were applied
            assert cache.optimization_mode == "performance"
            assert cache.pragma_settings["synchronous"] == "OFF"
            assert cache.pragma_settings["cache_size_kb"] == 10000
            assert cache.pragma_settings["mmap_size_mb"] == 30
            assert cache.pragma_settings["temp_store"] == "MEMORY"

            # Test basic operations still work
            await cache.set("key", "value")
            assert await cache.get("key") == "value"

            # Verify pragmas were applied to database using cache's connection method
            conn = cache._get_connection()
            cursor = conn.execute("PRAGMA synchronous")
            assert cursor.fetchone()[0] == 0  # OFF = 0
            conn.close()

    async def test_balanced_mode(self):
        """Test balanced optimization mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCacheBackend(
                db_path=Path(tmpdir) / "test.db",
                optimization_mode="balanced"
            )

            # Check that balanced settings were applied
            assert cache.optimization_mode == "balanced"
            assert cache.pragma_settings["synchronous"] == "NORMAL"
            assert cache.pragma_settings["cache_size_kb"] == 5000
            assert cache.pragma_settings["mmap_size_mb"] == 10
            assert cache.pragma_settings["temp_store"] == "DEFAULT"

            # Test operations
            await cache.set("key", {"data": "test"})
            assert await cache.get("key") == {"data": "test"}

    async def test_safe_mode(self):
        """Test safe optimization mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCacheBackend(
                db_path=Path(tmpdir) / "test.db",
                optimization_mode="safe"
            )

            # Check that safe settings were applied
            assert cache.optimization_mode == "safe"
            assert cache.pragma_settings["synchronous"] == "FULL"
            assert cache.pragma_settings["cache_size_kb"] == 2000
            assert cache.pragma_settings["mmap_size_mb"] == 0  # Disabled
            assert cache.pragma_settings["temp_store"] == "FILE"

            # Test operations
            await cache.set("key", "safe_value")
            assert await cache.get("key") == "safe_value"

            # Verify pragmas using cache's connection method
            conn = cache._get_connection()
            cursor = conn.execute("PRAGMA synchronous")
            assert cursor.fetchone()[0] == 2  # FULL = 2
            conn.close()

    async def test_pragma_overrides(self):
        """Test manual pragma overrides."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Start with balanced mode but override specific settings
            cache = SQLiteCacheBackend(
                db_path=Path(tmpdir) / "test.db",
                optimization_mode="balanced",
                sqlite_synchronous="OFF",
                sqlite_cache_size_kb=15000,
                sqlite_mmap_size_mb=50
            )

            # Check overrides were applied
            assert cache.optimization_mode == "balanced"
            assert cache.pragma_settings["synchronous"] == "OFF"  # Overridden
            assert cache.pragma_settings["cache_size_kb"] == 15000  # Overridden
            assert cache.pragma_settings["mmap_size_mb"] == 50  # Overridden
            assert cache.pragma_settings["temp_store"] == "DEFAULT"  # From balanced

            # Test operations
            await cache.set("key", "override_value")
            assert await cache.get("key") == "override_value"

    async def test_performance_comparison(self):
        """Compare performance between modes."""
        results = {}

        for mode in ["performance", "balanced", "safe"]:
            with tempfile.TemporaryDirectory() as tmpdir:
                cache = SQLiteCacheBackend(
                    db_path=Path(tmpdir) / "test.db",
                    optimization_mode=mode
                )

                # Measure write performance
                import time
                start = time.perf_counter()
                for i in range(100):
                    await cache.set(f"key_{i}", {"data": f"value_{i}"})
                write_time = time.perf_counter() - start

                # Measure read performance
                start = time.perf_counter()
                for i in range(100):
                    await cache.get(f"key_{i}")
                read_time = time.perf_counter() - start

                results[mode] = {
                    "write_ops_per_sec": 100 / write_time,
                    "read_ops_per_sec": 100 / read_time
                }

        # Performance mode should be fastest
        assert results["performance"]["write_ops_per_sec"] >= results["balanced"]["write_ops_per_sec"]
        assert results["balanced"]["write_ops_per_sec"] >= results["safe"]["write_ops_per_sec"]

        print(f"\nPerformance Results:")
        for mode, perf in results.items():
            print(f"  {mode:12} - Write: {perf['write_ops_per_sec']:.0f} ops/sec, "
                  f"Read: {perf['read_ops_per_sec']:.0f} ops/sec")

    async def test_concurrent_safety(self):
        """Test that all modes handle concurrent access safely."""
        for mode in ["performance", "balanced", "safe"]:
            with tempfile.TemporaryDirectory() as tmpdir:
                cache = SQLiteCacheBackend(
                    db_path=Path(tmpdir) / "test.db",
                    optimization_mode=mode
                )

                # Concurrent writes
                async def write_task(i):
                    await cache.set(f"key_{i}", f"value_{i}")

                await asyncio.gather(*[write_task(i) for i in range(10)])

                # Verify all writes succeeded
                for i in range(10):
                    assert await cache.get(f"key_{i}") == f"value_{i}"