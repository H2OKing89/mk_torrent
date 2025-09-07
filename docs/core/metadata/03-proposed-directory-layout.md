# 3) Proposed Directory Layout

## File Structure

```
src/mk_torrent/core/metadata/
  base.py                 # Protocols/ABCs + canonical dataclasses (AudiobookMeta)
  engine.py               # One true engine (registry + pipeline)
  exceptions.py           # Custom metadata exceptions (optional)
  processors/
    __init__.py
    audiobook.py          # Path/series/asin extraction; calls services/sources
    # music.py, video.py (placeholders)
  sources/
    __init__.py
    embedded.py           # Mutagen-backed tag extraction (file-level)
    audnexus.py           # api.audnex.us client + normalization
    pathinfo.py           # folder/filename parser (kept tiny & tested)
  services/
    __init__.py
    html_cleaner.py       # nh3/bs4-based sanitizer (plain-text output)
    format_detector.py    # Comprehensive audio format detection & quality scoring
    tag_normalizer.py     # genres/tags normalization (lowercasing, dedupe)
    merge_audiobook.py    # precedence-based field merger (declarative)
  validators/
    __init__.py
    common.py             # basic schemas/rules
    audiobook_validator.py# tracker-agnostic + RED-specific hints
  mappers/
    __init__.py
    red.py                # internal → RED upload fields mapping
```

## Module Organization Principles

### Core Modules

- **base.py**: Foundation protocols and dataclasses
- **engine.py**: Central orchestration and component registry
- **exceptions.py**: Custom exception hierarchy

### Processors (Content Type Handlers)

- Each content type (audiobook, music, video) gets its own processor
- Processors coordinate sources, services, and validation
- Future-ready for new content types

### Sources (Metadata Extractors)

- **embedded.py**: File tag extraction via Mutagen
- **audnexus.py**: API-based metadata from Audnexus
- **pathinfo.py**: Filename/path parsing
- Easy to add new sources (MusicBrainz, TMDB, etc.)

### Services (Utilities)

- Generic, reusable utilities
- No content-type specific logic
- Easily testable in isolation

### Validators (Quality Assurance)

- **common.py**: Basic validation primitives
- Content-specific validators for each type
- Tracker-specific hints without tight coupling

### Mappers (Output Formatting)

- Transform internal model to tracker-specific formats
- Keeps tracker APIs clean and focused
- Easy to add new trackers

## Migration Note

> **Note**: `features/metadata_engine.py` becomes **thin re-exports** or is removed after callers migrate to `core/metadata`.
