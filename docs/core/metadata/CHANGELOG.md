# Metadata Core Architecture - Detailed Changelog

> **Comprehensive change tracking for the metadata core refactor**
> For quick summaries, see individual document changelogs. For detailed context and implementation notes, see entries below.

---

## 2025-09-03 - Three-Source Strategy Implementation

### Major Architectural Changes

#### Embedded Source Complete Refactor
**Files affected:** `sources/embedded.py`, `docs/07.6 — Embedded Source (Technical Focus).md`

**BREAKING CHANGE**: Complete strategic shift from descriptive tag extraction to technical-only approach.

**Previous Approach (Abandoned):**
- Extracted title, author, series, description from embedded tags
- Mixed descriptive and technical metadata in single source
- Relied on tag consistency across different encoders and sources
- **Problem**: Tag metadata proved highly unreliable across sources

**New Approach (Current):**
- **Technical properties only**: Duration, bitrate, codec, file size, chapters
- **Multi-backend architecture**: ffprobe (preferred) + mutagen (fallback) + basic file info (minimal)
- **Authoritative for technical data**: Only embedded source can provide precise technical details
- **Avoid descriptive tags**: Title, author, series handled by path info + API sources

**Implementation Details:**
- `_extract_with_ffprobe()`: Primary extraction using ffprobe subprocess
- `_extract_with_mutagen()`: Python-native fallback for compatibility
- `_basic_file_info()`: Minimal extraction when no tools available
- Comprehensive data normalization for both backends
- Precise chapter timing extraction with multiple format support

**Data Output Changes:**
```python
# NEW: Technical-only output
{
    "_src": "embedded",
    "duration_sec": 31509,           # Precise seconds from audio stream
    "file_size_bytes": 367296512,   # Exact file size
    "bitrate": 125588,              # Audio bitrate
    "codec": "aac",                 # Audio codec
    "has_embedded_cover": True,     # Cover presence
    "chapter_count": 7,             # Chapter count
    "chapters": [...],              # Precise timing data
    "source": "ffprobe"            # Backend used
}

# OLD: Mixed descriptive + technical (unreliable)
{
    "_src": "embedded",
    "title": "...",                # REMOVED: Unreliable
    "author": "...",               # REMOVED: Inconsistent
    "description": "...",          # REMOVED: Poor quality
    # ... technical data was mixed with unreliable descriptive data
}
```

#### Chapter Integration in Audnexus Source
**Files affected:** `sources/audnexus.py`, `docs/07.3 — Audnexus Source.md`

**Enhancement**: Integrated chapter fetching directly into main extract() method for seamless operation.

**Changes:**
- Added automatic chapter data fetching during metadata extraction
- Enhanced chapter timing accuracy using chapter-specific runtime data
- Graceful error handling - chapter extraction never fails main operation
- Added `chapter_accuracy` flag from API response
- Improved chapter data normalization with comprehensive field mapping

**Implementation:**
```python
# NEW: Chapter integration in extract()
def extract(self, source):
    # ... main metadata extraction

    # Try to fetch chapter data (best effort)
    try:
        chapter_data = self.get_chapters(asin)
        if chapter_data:
            chapters = chapter_data.get("chapters", [])
            if chapters:
                normalized["chapters"] = chapters
                normalized["chapter_count"] = len(chapters)
                normalized["has_chapters"] = True

                # Use more accurate chapter runtime if available
                if chapter_data.get("runtimeLengthSec"):
                    normalized["duration_sec"] = chapter_data["runtimeLengthSec"]
    except Exception as e:
        logger.debug(f"Chapter data unavailable: {e}")
        # Continue without failing
```

#### Field Merger Strategy Overhaul
**Files affected:** `services/merge.py`, `docs/07.5 — Audiobook Metadata Field Merger.md`

**BREAKING CHANGE**: Complete revision of field precedence rules to support three-source strategy with technical/descriptive separation.

**New Precedence Rules:**
```python
DEFAULT_PRECEDENCE = {
    # Descriptive fields (API + path only, embedded unreliable)
    "title":        ["api", "path"],           # Skip embedded titles
    "author":       ["api", "path"],           # Skip embedded authors
    "series":       ["path", "api"],           # Path wins for compliance
    "narrator":     ["api"],                   # API only
    "description":  ["api"],                   # API only

    # Technical fields (embedded wins - most accurate)
    "duration_sec": ["embedded", "api"],       # Embedded precise > API minutes
    "file_size_bytes": ["embedded"],           # Only embedded has this
    "bitrate":         ["embedded"],           # Only embedded has this
    "codec":           ["embedded"],           # Only embedded has this
    "has_embedded_cover": ["embedded"],        # Only embedded has this
    "chapter_count":   ["embedded", "api"],    # Embedded count > API

    # List fields (API primary, embedded technical)
    "genres":       ["api"],                   # API only (embedded often poor)
    "chapters":     ["api", "embedded"],       # API structured > embedded timing
}
```

**Rationale:**
- **Technical data**: Embedded is authoritative source for file properties
- **Descriptive metadata**: API + path only; embedded tags too inconsistent
- **Compliance fields**: Path wins for tracker-specific requirements (series, ASIN)

### Documentation Updates

#### New Documentation Created
- **07.6 — Embedded Source (Technical Focus).md**: Complete specification for new technical-only approach
  - Multi-backend architecture documentation
  - Implementation examples and usage patterns
  - Performance characteristics and optimization guidelines
  - Comprehensive testing strategy

#### Documentation Enhanced
- **__Metadata Core.md**: Updated conductor document with three-source strategy
- **07 — Services Details.md**: Added embedded source, updated service numbering
- **07.3 — Audnexus Source.md**: Chapter integration features and implementation
- **07.5 — Audiobook Metadata Field Merger.md**: New precedence rules and examples

#### Architecture Diagrams Updated
- Updated high-level architecture to show specialized source focus
- Modified service integration patterns for new embedded approach

### Integration & Testing

#### Three-Source Integration Pattern
```python
def extract_all_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract from all three sources for optimal data quality."""

    # 1. Path information (compliance data)
    path_data = path_source.parse(file_path)      # series, volume, ASIN

    # 2. Technical details (authoritative)
    embedded_data = embedded_source.extract(file_path)  # duration, bitrate, codec

    # 3. Descriptive metadata (authoritative)
    asin = path_data.get("asin")
    api_data = audnexus_source.lookup(asin) if asin else {}  # title, author, description

    # 4. Merge with appropriate precedence
    return field_merger.merge([path_data, embedded_data, api_data])
```

#### Test Coverage Updates
- All enhanced fields tests passing (3/3)
- Audnexus functionality tests passing (16/16)
- Total metadata tests: 61 passing
- Chapter integration tested with real API responses

### Performance Impact

#### Embedded Source Performance
- **ffprobe extraction**: ~500-1000ms per file (includes subprocess overhead)
- **mutagen extraction**: ~50-200ms per file (Python-native)
- **basic file info**: ~1-5ms per file (filesystem only)
- **Memory usage**: Minimal (streaming JSON parsing)

#### Optimization Benefits
- Eliminated unreliable tag parsing overhead
- Focused extraction on reliable technical properties
- Better error handling with graceful fallback strategy

### Migration Notes

#### Breaking Changes
1. **Embedded source output format completely changed**
   - No longer provides title, author, series, description
   - Now provides technical properties: duration, bitrate, codec, file size

2. **Field merger precedence rules updated**
   - Technical fields now prefer embedded source
   - Descriptive fields now skip embedded source entirely

#### Backward Compatibility
- Core AudiobookMeta dataclass unchanged
- Public APIs maintained
- Migration path: Update field merger configuration to use new precedence rules

#### Required Actions for Users
1. Update any code expecting descriptive metadata from embedded source
2. Review field merger configuration if customized
3. Update tests that relied on embedded descriptive data

### Benefits Achieved

#### Data Quality Improvements
- **More reliable metadata**: Separated reliable (technical) from unreliable (embedded descriptive) data
- **Better chapter support**: Integrated timing from embedded + structured data from API
- **Precise technical data**: Exact duration, bitrate, codec information

#### Architectural Benefits
- **Clear separation of concerns**: Each source handles what it does best
- **Better error handling**: Sources fail independently without affecting others
- **Improved maintainability**: Focused, single-purpose source implementations

#### User Experience
- **Faster extraction**: No time wasted on unreliable embedded tag parsing
- **Better chapter experience**: Comprehensive chapter support with timing and titles
- **More accurate data**: Technical properties from authoritative source

---

## Previous Releases

### 2025-08-30 - Enhanced Fields Implementation
- Added 11 enhanced fields to AudiobookMeta and AudiobookMetaRich
- Implemented rich entity model with comprehensive structures
- Added provenance tracking and data lineage
- Enhanced validation system with completeness scoring

### 2025-08-25 - Core Architecture Foundation
- Initial metadata core refactor implementation
- Dependency injection engine with registry pattern
- Protocol-based interfaces and clean separation
- Comprehensive test coverage (56 tests passing)

---

## Future Roadmap

### Planned Enhancements
- **Waveform analysis**: Audio quality assessment for embedded source
- **Format validation**: Verify file integrity and compliance
- **Advanced chapter support**: Enhanced metadata and nested structures
- **Batch processing**: Optimized multi-file technical analysis

### Integration Opportunities
- **Quality scoring**: Technical quality metrics for upload validation
- **Format recommendations**: Suggest optimal encoding parameters
- **Chapter enhancement**: Merge embedded timing with API chapter titles

---

*For implementation details, code examples, and usage patterns, see individual document specifications.*
