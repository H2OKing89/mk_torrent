# 14) Example: Processor Skeleton

## AudiobookMetadata Processor

```python
# processors/audiobook.py
from typing import Dict, Any
from pathlib import Path
from ..base import AudiobookMeta

class AudiobookMetadata:
    def __init__(self, cleaner, detector, aud, pathinfo, merger):
        self.cleaner = cleaner
        self.detector = detector
        self.aud = aud
        self.pathinfo = pathinfo
        self.merger = merger

    def extract(self, source: Path) -> Dict[str, Any]:
        parts = []
        parts.append({"_src": "path", **self.pathinfo.parse(source)})
        parts.append({"_src": "embedded", **self.detector.tags(source)})  # optional
        asin = parts[0].get("asin") or parts[-1].get("asin")
        if asin:
            parts.append({"_src": "api", **self.aud.lookup(asin)})

        merged = self.merger.merge(parts)
        normalized = self.cleaner.sanitize(merged)
        # album fallback
        if not normalized.get("album"):
            normalized["album"] = normalized.get("title", "")
        return normalized

    def validate(self, md: Dict[str, Any]) -> Dict[str, Any]:
        # delegate to validators/audiobook_validator
        from ..validators.audiobook_validator import validate_audiobook
        return validate_audiobook(md)

    def enhance(self, md: Dict[str, Any]) -> Dict[str, Any]:
        # lightweight derived fields (display_name, zero-pad volume, etc.)
        out = dict(md)
        t, a = out.get("title", ""), out.get("author", "")
        if t and a:
            out["display_name"] = f"{t} by {a}"
        return out
```

## Processor Design Patterns

### Constructor Injection

- Accept all dependencies via constructor
- No hidden dependencies or global state
- Easy mocking and testing
- Clear service contracts

### Source Coordination

- Collect metadata from multiple sources
- Handle source failures gracefully
- Provide source attribution
- Support source prioritization

### Three-Phase Processing

1. **Extract**: Gather raw metadata from sources
2. **Validate**: Check quality and completeness
3. **Enhance**: Add derived fields and cleanup

### Error Handling

- Continue processing even if sources fail
- Provide partial results when possible
- Log issues for debugging
- Maintain operation quality

## Processor Interface

### Standard Methods

- `extract()`: Primary metadata gathering
- `validate()`: Quality assurance
- `enhance()`: Post-processing and derivation

### Data Flow

- Input: Source path or identifier
- Processing: Multi-source extraction and merging
- Output: Clean, validated metadata dictionary

### Extension Points

- New sources can be added easily
- Custom validation rules
- Configurable enhancement logic
- Pluggable service implementations
