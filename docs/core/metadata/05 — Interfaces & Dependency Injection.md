# 5) Interfaces & Dependency Injection

## Processor Protocol

**Processor Protocol** (simplified):

```python
class MetadataProcessor(Protocol):
    def extract(self, source: Source) -> Dict[str, Any]: ...
    def validate(self, metadata: Dict[str, Any]) -> Dict[str, Any]: ...
    def enhance(self, metadata: Dict[str, Any]) -> Dict[str, Any]: ...
```

## Dependency Injection Pattern

**DI**: Processors receive services/sources through the constructor. The engine builds processors with configured services (allows easy mocking/testing).

```python
# engine.py (registration sketch)
cleaner = HTMLCleaner()
detector = FormatDetector()
aud = AudnexusAPI(http_client=RequestsClient(), rate_limit=...)
pathinfo = PathInfoParser()
merger = FieldMerger(precedence=["embedded", "api", "path"])  # configurable

self.processors["audiobook"] = AudiobookMetadata(
    cleaner=cleaner,
    detector=detector,
    aud=aud,
    pathinfo=pathinfo,
    merger=merger,
)
```

## Interface Benefits

### Testability
- Easy mocking of dependencies
- Isolated unit tests
- Controllable test environments

### Flexibility
- Swap implementations without changing processors
- Configure different service combinations
- Runtime behavior modification

### Extensibility
- Add new services without touching existing code
- Plugin-like architecture
- Clear component boundaries

## Protocol Design Principles

### Minimal Interfaces
- Small, focused protocols
- Single responsibility
- Clear contracts

### Composability
- Services can be combined easily
- No tight coupling between components
- Layered architecture support

### Configuration-Driven
- Precedence rules configurable
- Service selection configurable
- Runtime behavior tunable
