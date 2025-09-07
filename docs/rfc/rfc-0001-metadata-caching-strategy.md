---
title: "RFC-0001: Metadata Caching Strategy"
status: draft
author: [H2OKing89]
reviewers: []
created: 2025-09-06
updated: 2025-09-06T19:14:05-05:00
tags: [RFC, design, metadata, caching, performance]
related:
  - ../core/metadata/06-engine-pipeline.md
  - ../adr/ADR-0001-choose-pydantic-for-schema-validation.md
---

## Summary

Implement a multi-layer caching strategy for metadata processing to reduce API calls to external services (Audnexus, etc.) and improve performance for repeated operations on the same audiobooks.

## Motivation

### Current Pain Points

- Repeated Audnexus API calls for the same books during development/testing
- Slow metadata resolution for large audiobook collections
- No persistence of expensive metadata operations between runs
- Rate limiting issues with external APIs

### Use Cases

- **Development**: Fast iteration without hitting API limits
- **Batch Processing**: Efficient handling of large audiobook libraries
- **Cross-Seeding**: Quick metadata lookup for existing content
- **Offline Operation**: Limited functionality without internet

## Detailed Design

### Cache Layers

#### L1: In-Memory Cache

- **Scope**: Single process lifetime
- **Technology**: Python `functools.lru_cache` + custom TTL wrapper
- **TTL**: 1 hour
- **Size**: 1000 entries max
- **Use Case**: Repeated operations within same session

#### L2: File-Based Cache

- **Scope**: Persistent across runs
- **Technology**: SQLite database with JSON fields
- **Location**: `~/.cache/mk_torrent/metadata.db`
- **TTL**: 7 days (configurable)
- **Schema**:

  ```sql
  CREATE TABLE metadata_cache (
    cache_key TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    data JSON NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```

#### L3: Shared Cache (Future)

- **Scope**: Team/CI shared cache
- **Technology**: Redis or similar
- **Use Case**: Shared development environment

### Cache Key Strategy

```python
def generate_cache_key(source: str, **params) -> str:
    """Generate deterministic cache key."""
    # Examples:
    # audnexus:search:q=dune&author=herbert
    # audnexus:book:asin=B002V1A0WE
    # pathinfo:path=/audiobooks/fantasy/dune
    param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"{source}:{param_str}"
```

### Cache Management

#### Invalidation

- **Time-based**: Automatic TTL expiration
- **Manual**: CLI command to clear cache
- **Version-based**: Cache schema versioning for safe upgrades

#### Configuration

```yaml
# config.yaml
cache:
  enabled: true
  file_ttl_days: 7
  memory_ttl_seconds: 3600
  max_memory_entries: 1000
  location: "~/.cache/mk_torrent"
```

### Integration Points

#### Audnexus Client

```python
@cached(ttl=3600)
async def search_books(query: str, author: str = None) -> List[Book]:
    cache_key = generate_cache_key("audnexus:search", q=query, author=author)
    # Implementation
```

#### Path Info Extractor

```python
@cached(ttl=3600)
def extract_path_info(path: Path) -> PathInfo:
    cache_key = generate_cache_key("pathinfo", path=str(path))
    # Implementation
```

## Drawbacks

- **Complexity**: Additional caching layer to maintain
- **Storage**: Disk space usage for cached metadata
- **Staleness**: Cached data may become outdated
- **Debugging**: Cached responses can mask upstream issues

## Rationale and Alternatives

### Why This Design

1. **Multi-layer approach** provides best of both worlds (speed + persistence)
2. **SQLite** is lightweight, reliable, and doesn't require external dependencies
3. **TTL-based expiration** balances freshness with performance
4. **Configurable** allows users to tune behavior

### Alternatives Considered

#### Simple File Cache

- **Pros**: Simpler implementation
- **Cons**: No query capabilities, harder to manage

#### Redis-Only

- **Pros**: High performance, advanced features
- **Cons**: External dependency, overkill for single-user case

#### No Caching

- **Pros**: Simple, always fresh data
- **Cons**: Poor performance, API rate limiting issues

## Implementation Plan

### Phase 1: Core Infrastructure

- [ ] Cache key generation utilities
- [ ] SQLite schema and basic operations
- [ ] Configuration integration
- [ ] Basic TTL management

### Phase 2: Integration

- [ ] Audnexus client caching
- [ ] Path info extraction caching
- [ ] Memory cache layer
- [ ] CLI cache management commands

### Phase 3: Advanced Features

- [ ] Cache statistics and monitoring
- [ ] Compression for large metadata
- [ ] Background cache warming
- [ ] Cache export/import for CI

## Unresolved Questions

1. **Cache warming strategy**: Should we pre-populate cache for common queries?
2. **Cache size limits**: How much disk space should we allow the cache to use?
3. **Cache sharing**: How to safely share cache between different versions of the tool?
4. **Partial cache hits**: How to handle cases where some fields are cached but others need fresh data?
