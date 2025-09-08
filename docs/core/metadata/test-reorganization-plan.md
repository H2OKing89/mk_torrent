# Test Suite Organization Plan

## Proposed Clean Structure

```
tests/
├── conftest.py                     # Global test configuration
├── readme.md                       # Test documentation
├── integration/                    # Integration tests (LEAVE UNTOUCHED)
│   ├── test_bbcode_output.py
│   ├── test_metadata_engine.py
│   ├── test_red_api.py
│   ├── test_red_integration.py
│   ├── test_red_upload.py
│   └── test_template_integration.py
├── samples/                        # Test data and fixtures
│   ├── audiobook/
│   ├── tmp/
│   └── torrent_files/
├── utils/                          # Test utilities
│   ├── __init__.py
│   └── real_data_helpers.py
└── unit/                          # Unit tests organized by module
    ├── api/
    │   └── test_qbittorrent.py
    ├── core/
    │   ├── metadata/
    │   │   ├── exceptions/
    │   │   │   ├── __init__.py
    │   │   │   └── test_exceptions.py
    │   │   ├── services/
    │   │   │   ├── __init__.py
    │   │   │   └── test_merge_audiobook.py
    │   │   ├── sources/
    │   │   │   ├── test_embedded_source_real.py
    │   │   │   ├── test_pathinfo_source_real.py
    │   │   │   └── test_three_source_integration.py
    │   │   ├── test_audnexus_source.py
    │   │   ├── test_base.py
    │   │   ├── test_engine.py
    │   │   ├── test_enhanced_fields.py
    │   │   ├── test_entities.py
    │   │   └── test_real_audiobook_enhanced.py
    │   ├── test_secure_credentials.py
    │   └── test_upload_queue.py
    └── test_real_data_comprehensive.py  # Comprehensive integration-style unit tests
```

## Rationale

### 1. **Clear Separation**

- `unit/` - Fast, isolated tests for individual components
- `integration/` - End-to-end tests with real data/services (UNTOUCHED)
- `samples/` - Test data and fixtures
- `utils/` - Test helpers and utilities

### 2. **Hierarchical Organization**

- Tests mirror the source code structure
- Easy to find tests for specific modules
- Clear responsibility boundaries

### 3. **Logical Grouping**

- API tests under `unit/api/`
- Core functionality under `unit/core/`
- Metadata system properly nested under `unit/core/metadata/`

### 4. **Maintained Functionality**

- All existing integration tests remain untouched
- All test functionality preserved
- Improved discoverability and maintenance

## Implementation Steps

1. Create directory structure
2. Move files to appropriate locations
3. Update import paths if needed
4. Verify all tests still run correctly
5. Update documentation
