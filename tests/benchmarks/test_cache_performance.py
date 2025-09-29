"""Benchmark to demonstrate SQLite cache performance improvements."""

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from youtrack_mcp.cache.backends.sqlite import SQLiteCacheBackend


@pytest.mark.asyncio
async def test_sqlite_performance():
    """Benchmark SQLite cache performance with optimizations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = SQLiteCacheBackend(db_path=Path(tmpdir) / "test.db")

        # Test data
        test_data = {"key": "value" * 100, "number": 42, "nested": {"data": list(range(100))}}

        print("\n=== SQLite Cache Performance Benchmark ===")

        # Write performance test
        start = time.perf_counter()
        write_tasks = []
        for i in range(1000):
            write_tasks.append(cache.set(f"key_{i}", test_data, ttl=3600))
        await asyncio.gather(*write_tasks)
        write_time = time.perf_counter() - start
        print(f"Write 1000 items: {write_time:.3f}s ({1000/write_time:.0f} ops/sec)")

        # Read performance test (cache hits)
        start = time.perf_counter()
        read_tasks = []
        for i in range(1000):
            read_tasks.append(cache.get(f"key_{i}"))
        results = await asyncio.gather(*read_tasks)
        read_time = time.perf_counter() - start
        print(f"Read 1000 items:  {read_time:.3f}s ({1000/read_time:.0f} ops/sec)")

        # Verify all reads successful
        assert all(r is not None for r in results)

        # Mixed read/write performance
        start = time.perf_counter()
        mixed_tasks = []
        for i in range(500):
            mixed_tasks.append(cache.get(f"key_{i}"))
            mixed_tasks.append(cache.set(f"new_key_{i}", test_data, ttl=3600))
        await asyncio.gather(*mixed_tasks)
        mixed_time = time.perf_counter() - start
        print(f"Mixed 1000 ops:   {mixed_time:.3f}s ({1000/mixed_time:.0f} ops/sec)")

        # Stats
        stats = await cache.get_stats()
        print(f"\nCache Stats:")
        print(f"  Total items: {stats['total_items']}")
        print(f"  DB size: {stats['db_size_bytes'] / 1024:.1f} KB")
        print(f"  Hits: {stats['hits']}")
        print(f"  Misses: {stats['misses']}")


if __name__ == "__main__":
    asyncio.run(test_sqlite_performance())