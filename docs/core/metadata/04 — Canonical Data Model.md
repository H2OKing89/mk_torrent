# 4) Canonical Data Model

## Primary Data Structure

Use a **dataclass** as the primary DTO (fast, zero deps), with an optional pydantic mirror under `schemas/` for strict-mode validation.

```python
# core/metadata/base.py
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

@dataclass
class AudiobookMeta:
    title: str = ""
    author: str = ""
    album: str = ""          # default: title
    series: str = ""
    volume: str = ""          # e.g., "08"
    year: Optional[int] = None
    narrator: str = ""
    duration_sec: Optional[int] = None
    format: str = ""          # AAC/FLAC/MP3/etc
    encoding: str = ""        # V0/CBR320/Lossless/etc
    asin: str = ""
    isbn: str = ""
    publisher: str = ""
    language: str = "en"
    description: str = ""
    genres: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    chapters: List[Dict[str, Any]] = field(default_factory=list)
    files: List[Path] = field(default_factory=list)
    source_path: Optional[Path] = None
    artwork_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

## Normalization Rules

**Normalization rules** (enforced by services/validators):

* `album` defaults to `title` when empty.
* `year` coerced to `int` when possible; out-of-range → warning (not hard error).
* `volume` stored zero-padded if parseable.
* `genres/tags` normalized to lower-case, deduped, ASCII-friendly by default (configurable).

## Design Decisions

### Dataclass vs Pydantic
- **Primary**: Dataclass (fast, zero dependencies, simple)
- **Optional**: Pydantic mirror for strict validation when needed
- Best of both worlds: performance + validation

### Field Types
- Simple types where possible (str, int, bool)
- Lists for collections (genres, tags, chapters)
- Optional for nullable fields
- Path objects for file references

### Default Values
- Empty strings for text fields
- Empty lists for collections
- Sensible defaults (language="en")
- None for truly optional fields

### Method Conventions
- `to_dict()` for serialization
- Future: `from_dict()` for deserialization
- Keep methods minimal and focused
