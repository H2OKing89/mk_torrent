# 15) Extension Guide

## Adding New Components

### Add a New Source

1. **Create source file** in `sources/`
2. **Implement source interface** with `lookup(...)` or `extract(...)`
3. **Register via DI** in `engine.py`
4. **Add to precedence** in configuration

**Example**: Adding MusicBrainz support

```python
# sources/musicbrainz.py
class MusicBrainzSource:
    def lookup(self, mbid: str) -> Dict[str, Any]:
        # Fetch from MusicBrainz API
        return normalized_data
```

### Add a New Content Type

1. **Create processor** in `processors/<type>.py`
2. **Reuse existing services** (cleaner, detector, etc.)
3. **Create content validator** in `validators/<type>_validator.py`
4. **Update engine registry** to recognize new type

**Example**: Adding video support

```python
# processors/video.py
class VideoMetadata:
    def __init__(self, cleaner, detector, tmdb, pathinfo, merger):
        # Similar pattern to audiobook processor
```

### Support a New Tracker

1. **Implement mapper** in `mappers/<tracker>.py`
2. **Keep tracker API** in `api/trackers/<tracker>.py` focused on HTTP/form mechanics
3. **Handle tracker-specific** field transformations in mapper
4. **Add tracker validation** hints to validators

**Example**: Adding Orpheus support

```python
# mappers/orpheus.py
class OrpheusMapper:
    def map_audiobook(self, meta: AudiobookMeta) -> Dict[str, Any]:
        # Transform to Orpheus format
        return orpheus_fields
```

## Extension Patterns

### Service Extension

- Services are composable and reusable
- New services integrate seamlessly
- Dependency injection handles wiring
- Configuration controls behavior

### Source Extension

- Sources follow standard interface
- Multiple sources can be active
- Precedence rules handle conflicts
- Error handling maintains operation

### Validation Extension

- Validators are pluggable
- Content-specific rules separate from common rules
- Tracker hints don't pollute core logic
- Graduated response (errors/warnings/completeness)

## Configuration Extension

### New Source Configuration

```yaml
sources:
  musicbrainz:
    enabled: true
    timeout: 5.0
    api_key: ${MUSICBRAINZ_API_KEY}

precedence:
  title: [musicbrainz, api, embedded, path]
```

### New Tracker Configuration

```yaml
trackers:
  orpheus:
    field_mapping:
      description_max_length: 5000
      tag_separator: ','
    validation:
      required_fields: [title, author, year]
```

## Best Practices

### Interface Consistency

- Follow established patterns
- Use standard method signatures
- Maintain error handling conventions
- Support configuration consistently

### Testing Requirements

- Unit tests for new components
- Integration tests for interactions
- Mock external dependencies
- Property-based testing where applicable

### Documentation Standards

- Clear component purpose
- Usage examples
- Configuration options
- Extension points
