# Metadata Core Refactor & Modularization

This document describes the comprehensive refactoring of the metadata system from a monolithic design to a modular, extensible architecture based on dependency injection and clean separation of concerns.

## 🎯 Goals & Benefits

### Primary Objectives
- **Modular Architecture**: Replace monolithic metadata engine with composable components
- **Dependency Injection**: Enable easy testing, mocking, and component swapping
- **Protocol-Based Design**: Use Python protocols for clean interfaces without heavy inheritance
- **Type Safety**: Leverage modern Python typing for better developer experience
- **Zero-Dependency Core**: Keep core interfaces free of external dependencies
- **Backward Compatibility**: Maintain existing API through compatibility shims

### Key Benefits
- ✅ **Testable**: Clean separation enables comprehensive unit testing
- ✅ **Extensible**: Easy to add new content types, trackers, and data sources
- ✅ **Maintainable**: Clear interfaces and single responsibility principle
- ✅ **Type-Safe**: Full typing support with modern Python features
- ✅ **Performance**: Lightweight core with optional enhancement modules
- ✅ **Migration-Friendly**: Gradual migration path from legacy system

## 🏗️ Architecture Overview

### New Directory Structure

```
src/mk_torrent/core/metadata/
├── __init__.py              # Clean public exports
├── base.py                  # Core protocols and AudiobookMeta dataclass
├── engine.py               # Main orchestration engine with DI
├── exceptions.py           # Typed exception hierarchy
├── processors/             # Content-type specific processing
│   ├── __init__.py
│   ├── audiobook.py        # Audiobook processing logic
│   ├── music.py           # Music processing logic
│   └── video.py           # Video processing logic
├── sources/                # Data extraction sources
│   ├── __init__.py
│   ├── audnexus.py        # AudNexus API integration
│   ├── embedded.py        # Embedded metadata extraction
│   └── pathinfo.py        # Filename/path parsing
├── services/               # Utility services
│   ├── __init__.py
│   ├── format_detector.py  # File format detection
│   ├── html_cleaner.py    # HTML sanitization
│   ├── image_finder.py    # Cover art location
│   ├── merge.py           # Metadata merging strategies
│   └── tag_normalizer.py  # Tag standardization
├── validators/             # Validation logic
│   ├── __init__.py
│   ├── audiobook_validator.py
│   └── common.py
├── mappers/               # Tracker-specific formatting
│   ├── __init__.py
│   └── red.py             # RED tracker mappings
└── schemas/               # Optional Pydantic models
    ├── __init__.py
    └── audiobook.py
```

### Core Components

#### 1. Base Protocols (`base.py`)
- **`AudiobookMeta`**: Core dataclass for audiobook metadata
- **`MetadataProcessor`**: Protocol for content-type specific processing
- **`MetadataSource`**: Protocol for data extraction sources
- **`MetadataService`**: Protocol for utility services
- **`MetadataValidator`**: Protocol for validation logic
- **`MetadataMapper`**: Protocol for tracker-specific formatting

#### 2. Metadata Engine (`engine.py`)
- Central orchestration with dependency injection
- Registry pattern for processors and mappers
- Content type detection and routing
- Full pipeline processing with validation

#### 3. Exception Hierarchy (`exceptions.py`)
- Typed exceptions with context information
- Clear error handling and debugging support

## 🚀 Usage Examples

### Basic Usage

```python
from mk_torrent.core.metadata import MetadataEngine, AudiobookMeta

# Create engine
engine = MetadataEngine()

# Register components (processors/mappers would be registered here)
# engine.register_processor("audiobook", my_processor)
# engine.register_mapper("red", my_mapper)

# Extract metadata
metadata = engine.extract_metadata("audiobook.m4b")

# Convert to typed object
audiobook = AudiobookMeta.from_dict(metadata)
print(f"{audiobook.title} by {audiobook.author}")
```

### Full Pipeline Processing

```python
# Run complete pipeline with validation
result = engine.process_full_pipeline(
    "audiobook.m4b",
    tracker_name="red",
    validate=True
)

print(f"Success: {result['success']}")
print(f"Valid: {result['validation']['valid']}")
print(f"Completeness: {result['validation']['completeness']:.1%}")
```

### Custom Processor Implementation

```python
from mk_torrent.core.metadata.base import MetadataProcessor

class MyAudiobookProcessor:
    def extract(self, source):
        # Extract basic metadata
        return {"title": "...", "author": "..."}

    def validate(self, metadata):
        # Return ValidationResult
        pass

    def enhance(self, metadata):
        # Add derived fields
        return metadata

# Register with engine
engine.register_processor("audiobook", MyAudiobookProcessor())
```

## 🔧 Migration Guide

### For Existing Code

The refactor maintains backward compatibility through compatibility shims in `features/__init__.py`:

```python
# This still works unchanged
from mk_torrent.features import MetadataEngine

# Old code continues to function
engine = MetadataEngine()
result = engine.process_audiobook("file.m4b")
```

### Gradual Migration Path

1. **Phase 1**: Use new core with compatibility layer
2. **Phase 2**: Migrate to new interfaces gradually
3. **Phase 3**: Remove legacy code once fully migrated

## 🧪 Testing Strategy

### Comprehensive Test Suite

- **Unit Tests**: Individual component testing with mocks
- **Integration Tests**: Full pipeline testing with real files
- **Compatibility Tests**: Ensure legacy API continues working

### Test Coverage

The refactor includes 34 comprehensive tests covering:
- AudiobookMeta dataclass operations
- ValidationResult functionality
- MetadataEngine dependency injection
- Full pipeline processing
- Error handling and edge cases
- Real file processing with sample data

### Running Tests

```bash
# Run all metadata core tests
pytest tests/unit/core/metadata/ tests/integration/ -v

# Run with coverage
pytest tests/unit/core/metadata/ tests/integration/ --cov=src/mk_torrent/core/metadata
```

## 📦 Dependencies

### Core System (Zero Dependencies)
The core metadata system requires only Python 3.8+ standard library:
- `dataclasses` for AudiobookMeta
- `typing` for protocols and type hints
- `pathlib` for path handling
- `abc` for abstract base classes

### Optional Enhancements
Additional functionality available through optional dependencies:

```toml
[project.optional-dependencies]
net = ["httpx>=0.25.0", "aiofiles>=23.0.0"]
strict = ["pydantic>=2.0.0", "pydantic-settings>=2.0.0"]
html = ["nh3>=0.2.0", "markupsafe>=2.1.0"]
```

## 🔄 Backward Compatibility

### Compatibility Layer
The `features/__init__.py` module provides seamless compatibility:

```python
# Redirects to new core system
from mk_torrent.core.metadata import MetadataEngine as NewEngine

class MetadataEngine(NewEngine):
    """Compatibility wrapper for legacy code."""
    # Maintains old method signatures
    # Adapts to new internal architecture
```

### Migration Timeline
- **Current**: Both systems work in parallel
- **Next Release**: Deprecation warnings for legacy API
- **Future Release**: Legacy system removal

## 🎉 Demo

A comprehensive demo is available in `examples/metadata_core_demo.py` showing:
- Engine setup and component registration
- Real file processing with sample audiobooks
- Validation and completeness checking
- Tracker-specific mapping
- Full pipeline processing
- Backward compatibility verification

Run the demo:
```bash
python examples/metadata_core_demo.py
```

## 📋 Implementation Status

### ✅ Completed
- [x] Core protocol interfaces and dataclasses
- [x] MetadataEngine with dependency injection
- [x] Exception hierarchy with proper typing
- [x] Comprehensive test suite (34 tests passing)
- [x] Package structure and clean imports
- [x] Backward compatibility shims
- [x] Real file processing with samples
- [x] Documentation and examples

### 🔄 Future Enhancements
- [ ] Implement concrete processors for all content types
- [ ] Add comprehensive source implementations
- [ ] Expand tracker mapper collection
- [ ] Performance optimizations
- [ ] Additional validation rules
- [ ] Enhanced error reporting

## 🤝 Contributing

When adding new components:

1. **Follow Protocol Interfaces**: Implement the appropriate protocol from `base.py`
2. **Add Type Hints**: Use comprehensive typing for better developer experience
3. **Write Tests**: Include both unit and integration tests
4. **Update Documentation**: Keep examples and docs current
5. **Maintain Compatibility**: Ensure legacy code continues working

The modular architecture makes it easy to contribute new processors, sources, validators, or mappers without affecting existing functionality.
