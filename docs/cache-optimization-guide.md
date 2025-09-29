# Cache SQLite Optimization Guide

## Overview

The YouTrack MCP cache system provides configurable SQLite optimization modes to balance performance, durability, and safety based on your specific needs. Since cache data can be rebuilt, you can choose more aggressive optimizations for better performance.

## Optimization Modes

### 1. Performance Mode (Fastest)
**Use when:** Maximum speed is critical, cache can be easily rebuilt
```bash
export CACHE_SQLITE_OPTIMIZATION_MODE=performance
```

**Settings:**
- `PRAGMA synchronous=OFF` - No waiting for disk writes
- `PRAGMA cache_size=10MB` - Large in-memory page cache
- `PRAGMA mmap_size=30MB` - Aggressive memory-mapped I/O
- `PRAGMA temp_store=MEMORY` - All temp operations in RAM
- `PRAGMA page_size=8192` - Larger pages for bulk operations

**Performance:** ~1,600-2,000 ops/sec
**Trade-offs:** Risk of corruption on crash (acceptable for cache)

### 2. Balanced Mode (Default)
**Use when:** Good performance with reasonable safety
```bash
export CACHE_SQLITE_OPTIMIZATION_MODE=balanced
```

**Settings:**
- `PRAGMA synchronous=NORMAL` - Waits for critical writes
- `PRAGMA cache_size=5MB` - Moderate page cache
- `PRAGMA mmap_size=10MB` - Conservative memory mapping
- `PRAGMA temp_store=DEFAULT` - System decides temp storage
- `PRAGMA page_size=4096` - Standard page size

**Performance:** ~1,000-1,500 ops/sec
**Trade-offs:** Good balance for most use cases

### 3. Safe Mode (Most Durable)
**Use when:** Cache persistence is important, slower rebuilds
```bash
export CACHE_SQLITE_OPTIMIZATION_MODE=safe
```

**Settings:**
- `PRAGMA synchronous=FULL` - Wait for all disk writes
- `PRAGMA cache_size=2MB` - Conservative cache
- `PRAGMA mmap_size=0` - No memory mapping
- `PRAGMA temp_store=FILE` - Temp data on disk
- `PRAGMA page_size=4096` - Standard page size

**Performance:** ~500-800 ops/sec
**Trade-offs:** Slowest but most durable

## Configuration

### Basic Configuration
Set the optimization mode via environment variable:
```bash
# Choose one of: performance, balanced, safe
export CACHE_SQLITE_OPTIMIZATION_MODE=balanced
```

### Advanced Tuning
Override individual pragma settings for fine-grained control:

```bash
# Start with balanced mode but override specific settings
export CACHE_SQLITE_OPTIMIZATION_MODE=balanced
export CACHE_SQLITE_SYNCHRONOUS=OFF           # Override sync mode
export CACHE_SQLITE_CACHE_SIZE_KB=15000       # 15MB cache
export CACHE_SQLITE_MMAP_SIZE_MB=50           # 50MB mmap
export CACHE_SQLITE_TEMP_STORE=MEMORY         # RAM for temp
export CACHE_SQLITE_PAGE_SIZE=8192            # 8KB pages
export CACHE_SQLITE_BUSY_TIMEOUT_MS=10000     # 10s timeout
```

### Python Configuration
Configure directly in Python code:
```python
from youtrack_mcp.cache import UnifiedCacheManager, CacheStrategy

# Using optimization mode
cache = UnifiedCacheManager(
    strategy=CacheStrategy.SQLITE_HYBRID,
    sqlite_config={
        "optimization_mode": "performance",
        "db_path": Path("./cache.db"),
        "default_ttl": 3600
    }
)

# With custom overrides
cache = UnifiedCacheManager(
    strategy=CacheStrategy.SQLITE_HYBRID,
    sqlite_config={
        "optimization_mode": "balanced",
        "sqlite_synchronous": "OFF",  # Override specific pragma
        "sqlite_cache_size_kb": 20000,  # 20MB cache
        "db_path": Path("./cache.db")
    }
)
```

## Performance Benchmarks

| Mode | Write (ops/sec) | Read (ops/sec) | Durability |
|------|-----------------|----------------|------------|
| Performance | ~1,642 | ~2,046 | Low (cache-safe) |
| Balanced | ~1,100 | ~1,400 | Medium |
| Safe | ~600 | ~800 | High |

*Benchmarks on typical hardware with mixed JSON payloads*

## Choosing the Right Mode

### Use Performance Mode When:
- Cache can be easily rebuilt from source
- Maximum throughput is critical
- Running on reliable infrastructure
- Frequent cache operations (>1000/sec)

### Use Balanced Mode When:
- Default choice for most applications
- Good performance is needed
- Some crash resilience desired
- Mixed read/write workloads

### Use Safe Mode When:
- Cache rebuild is expensive/slow
- Running on unreliable hardware
- Data consistency is important
- Lower operation volume (<100/sec)

## Multi-Process Considerations

All modes use WAL (Write-Ahead Logging) for safe concurrent access:
- Multiple readers can work simultaneously
- Single writer at a time (SQLite limitation)
- Readers don't block writers and vice versa

## Monitoring and Tuning

### Check Current Settings
```python
# Get cache statistics including optimization mode
stats = await cache.get_stats()
print(f"SQLite optimization: {stats['backends']['sqlite']['optimization_mode']}")
```

### Performance Monitoring
```python
import time

# Measure operation performance
start = time.perf_counter()
for i in range(1000):
    await cache.set(f"key_{i}", data)
elapsed = time.perf_counter() - start
print(f"Write performance: {1000/elapsed:.0f} ops/sec")
```

### Troubleshooting

**Slow Performance:**
1. Check optimization mode: `echo $CACHE_SQLITE_OPTIMIZATION_MODE`
2. Consider switching to "performance" mode
3. Increase cache size: `export CACHE_SQLITE_CACHE_SIZE_KB=20000`
4. Enable memory mapping: `export CACHE_SQLITE_MMAP_SIZE_MB=50`

**Database Locked Errors:**
1. Increase busy timeout: `export CACHE_SQLITE_BUSY_TIMEOUT_MS=10000`
2. Ensure WAL mode is enabled (default for all modes)
3. Check for long-running transactions

**High Memory Usage:**
1. Reduce cache size: `export CACHE_SQLITE_CACHE_SIZE_KB=2000`
2. Disable memory mapping: `export CACHE_SQLITE_MMAP_SIZE_MB=0`
3. Use "safe" mode for lower memory footprint

## Best Practices

1. **Start with Balanced Mode**: It's the default for a reason
2. **Monitor Performance**: Measure before optimizing
3. **Test Under Load**: Verify settings with realistic workloads
4. **Document Changes**: Record custom pragma overrides
5. **Regular Cleanup**: Run `cleanup_expired()` periodically

## Security Note

These optimizations are safe for cache usage because:
- Cache data is not critical (can be rebuilt)
- WAL mode maintains ACID properties for operations
- Multiprocess safety is preserved
- Worst case: cache rebuild after crash

For primary data storage, always use more conservative settings.