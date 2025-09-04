# 16) Next Steps (For This Repo)

## Implementation Checklist

### Phase 1: Foundation
* [ ] Create `core/metadata/base.py` and port both engine & audiobook to it.
* [ ] Extract `HTMLCleaner`, `FormatDetector`, `PathInfo`, `Audnexus` into `services/` & `sources/`.
* [x] ~~Implement `services/merge_audiobook.py` + `validators/audiobook_validator.py`~~ **COMPLETE**

### Phase 2: Integration
* [ ] Add `mappers/red.py` and flip `api/trackers/red.py` to consume it.
* [ ] Split tests as per structure; keep one e2e.
* [x] ~~Remove dead code & typos in existing `audiobook.py`~~ **COMPLETE - Major refactoring completed**

### Phase 3: Enhancement
* [ ] Add configuration system for precedence rules
* [ ] Implement error handling and logging framework
* [ ] Create comprehensive test suite
* [ ] Document all interfaces and extension points

## Current Priority

**Immediate Focus**: ~~Implement field merger (`services/merge_audiobook.py`) following the detailed specification in [`7.5 — Audiobook Metadata Field Merger.md`](./7.5%20—%20Audiobook%20Metadata%20Field%20Merger.md)~~ **COMPLETE**

This is the next critical component needed to complete the metadata pipeline.

## Success Metrics

### Technical Goals
- All 172 tests continue passing
- Clean separation of concerns achieved
- New components easily testable
- Performance maintained or improved

### Architecture Goals
- Plugin-based extensibility
- Clear dependency injection
- Comprehensive error handling
- Robust validation system

## Long-term Vision

### Content Type Expansion
- Music metadata processing
- Video metadata processing
- E-book metadata processing
- Generic file metadata

### Tracker Ecosystem
- Multiple tracker support
- Tracker-specific validation
- Custom field mapping
- Upload automation

### Quality Improvements
- Enhanced validation rules
- Better error messages
- Performance optimization
- Monitoring and metrics

## Result

**A crisp, plug-and-play metadata core** that's easy to reason about, test, and extend—without surprising knock-on effects in trackers or torrent creation.
