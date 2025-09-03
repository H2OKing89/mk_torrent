# 7) Services Details

## Overview

Services provide generic, reusable utilities that are content-type agnostic. They handle common tasks like HTML cleaning, format detection, and field merging. Each service is designed for composability, reusability, and testability.

## Service Architecture

### Design Principles
- **Composability**: Services can be combined in any order
- **Reusability**: Content-type agnostic with configurable behavior
- **Testability**: Pure functions where possible with deterministic behavior
- **Minimal Dependencies**: Each service has focused, minimal external requirements

### Dependency Injection
Services are injected into processors via constructor parameters, enabling:
- Easy mocking and testing
- Runtime configuration and swapping
- Clear separation of concerns
- Pluggable architecture

## Service Modules

### 7.1 HTML Cleaner (`services/html_cleaner.py`)

**[📖 Detailed Specification](./7.1%20—%20HTML%20Cleaner%20Service.md)**

**Summary**: Robust HTML sanitization with graceful fallback capabilities.

**Key Features:**
- Modern sanitization with nh3 (preferred) and BeautifulSoup (fallback)
- Entity unescaping and whitespace normalization
- Idempotent operations and safe plain-text output
- Configurable strict/relaxed modes

**Interface Preview:**
```python
class HTMLCleaner:
    def sanitize(self, html_content: str) -> str: ...
    def is_html(self, content: str) -> bool: ...
```

### 7.2 Format Detector (`services/format_detector.py`)

**[📖 Detailed Specification](./7.2%20—%20Format%20Detector%20Service.md)**

**Summary**: Comprehensive audio format detection and quality assessment.

**Key Features:**
- Audio format detection (AAC, FLAC, MP3, etc.) with quality assessment
- MP3 VBR bucket classification (V0/V1/V2) and encoding detection
- Graceful degradation without Mutagen (extension-based fallback)
- Comprehensive format information with quality scoring

**Interface Preview:**
```python
class FormatDetector:
    def detect_format(self, file_path: Path) -> FormatInfo: ...
    def get_duration(self, file_path: Path) -> Optional[int]: ...
```

### 7.3 Audnexus Source (`sources/audnexus.py`)

**[📖 Detailed Specification](./7.3%20—%20Audnexus%20Source.md)**

**Summary**: Robust integration with Audnexus API for authoritative audiobook metadata.

**Key Features:**
- ASIN extraction from filenames and embedded tags
- API response normalization with field mapping
- Pluggable HTTP backend (httpx/requests) with rate limiting
- Comprehensive error handling and retry logic

**Interface Preview:**
```python
class AudnexusSource:
    def lookup(self, asin: str) -> Dict[str, Any]: ...
    def extract_asin(self, source: Union[Path, str]) -> Optional[str]: ...
```

### 7.4 Path Info Source (`sources/pathinfo.py`)

**[📖 Detailed Specification](./7.4%20—%20Path%20Info%20Source.md)**

**Summary**: Deterministic parsing of standardized audiobook filenames and directory structures.

**Key Features:**
- Canonical format parsing: `Title - vol_XX (YYYY) (Author) {ASIN.ABC} [Uploader]`
- Zero I/O design (pure functions, deterministic, thread-safe)
- Unicode support and comprehensive pattern matching
- Extensive test coverage with property-based testing

**Interface Preview:**
```python
class PathInfoParser:
    def parse(self, source: Union[Path, str]) -> Dict[str, Any]: ...
    def validate_format(self, filename: str) -> bool: ...
```

### 7.5 Field Merger (`services/merge.py`)

**[📖 Dedicated Specification](./7.5%20—%20Audiobook%20Metadata%20Field%20Merger.md)**

**Summary**: Declarative precedence-based field merging with smart conflict resolution.

**Key Features:**
- **Declarative precedence** (YAML/py config) per field with smart rationales:
  - `duration_sec`: embedded (precise seconds) > API (minute-granular) > path
  - `series/volume`: path (tracker-compliant) > API > embedded
  - `asin`: path (reliable extraction) > API > embedded
- **Smart list union** for genres/tags: stable order + case-insensitive de-duplication
- **Source tagging**: Each input requires `"_src": "path"|"embedded"|"api"` for traceability
- **Meaningful value detection**: Ignores empty strings, null values, empty collections

**Interface Preview:**
```python
class FieldMerger:
    def merge(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]: ...
    def configure_precedence(self, rules: Dict[str, List[str]]): ...
```

## Service Integration Patterns

### Constructor Injection Example
```python
# Engine builds services and injects into processors
class AudiobookProcessor:
    def __init__(self, cleaner, detector, audnexus, pathinfo, merger):
        self.cleaner = cleaner
        self.detector = detector
        self.audnexus = audnexus
        self.pathinfo = pathinfo
        self.merger = merger
```

### Service Composition
```python
# Services work together in processing pipeline
def extract_metadata(self, source_path: Path) -> Dict[str, Any]:
    # Collect from multiple sources
    path_data = {"_src": "path", **self.pathinfo.parse(source_path)}
    embedded_data = {"_src": "embedded", **self.detector.tags(source_path)}

    # API lookup if ASIN available
    asin = path_data.get("asin") or embedded_data.get("asin")
    if asin:
        api_data = {"_src": "api", **self.audnexus.lookup(asin)}
        sources = [path_data, embedded_data, api_data]
    else:
        sources = [path_data, embedded_data]

    # Merge with precedence rules
    merged = self.merger.merge(sources)

    # Clean HTML content
    if merged.get("description"):
        merged["description"] = self.cleaner.sanitize(merged["description"])

    return merged
```

## Error Handling Strategy

### Graceful Degradation
- Services continue operation even when individual components fail
- Fallback mechanisms for missing dependencies (e.g., Mutagen)
- Partial results preferred over complete failure
- Clear error attribution through source tagging

### Error Propagation
```python
# Services handle errors gracefully
try:
    api_data = audnexus.lookup(asin)
except SourceUnavailable:
    logger.warning("API unavailable, continuing with local sources")
    api_data = {}  # Empty dict allows merge to continue
```

## Performance Characteristics

### Service Performance Profiles
- **HTMLCleaner**: ~10x faster with nh3 vs BeautifulSoup
- **FormatDetector**: Microsecond performance for extension fallback
- **PathInfoParser**: ~10-50 microseconds per filename
- **AudnexusSource**: Network-bound with rate limiting
- **FieldMerger**: Linear with number of sources and fields

### Optimization Guidelines
- Reuse service instances (compiled regex caching)
- Use batch processing for better memory locality
- Configure appropriate timeouts and retries
- Enable caching for network-bound services

## Testing Integration

### Service Testing
Each service includes comprehensive test suites:
- Unit tests for core functionality
- Property tests for edge cases
- Integration tests for external dependencies
- Performance benchmarks

### Mocking Strategy
```python
# Easy mocking via dependency injection
def test_processor_with_mocked_services():
    mock_cleaner = Mock(spec=HTMLCleaner)
    mock_detector = Mock(spec=FormatDetector)
    # ... other mocks

    processor = AudiobookProcessor(
        cleaner=mock_cleaner,
        detector=mock_detector,
        # ... other services
    )
```

## Future Extensions

### Adding New Services
1. Implement service interface with clear contracts
2. Add comprehensive test suite
3. Document service in dedicated specification
4. Register with dependency injection system
5. Update processor constructors as needed

### Service Enhancement
- Additional backends for existing services
- Performance optimizations and caching
- Configuration-driven behavior
- Monitoring and metrics collection

---

For detailed implementation guidance, API references, and usage examples, please refer to the individual service specification documents linked above.
