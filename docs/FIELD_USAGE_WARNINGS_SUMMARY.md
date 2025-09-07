# Field Usage Warnings Summary

This document summarizes all the field usage warnings added to prevent data loss and field confusion in the metadata system.

## Warning Locations Added

### 1. `/src/mk_torrent/core/metadata/services/merge_audiobook.py`

**⚠️ FIELD SOURCE USAGE GUIDELINES**

- Comprehensive guidelines for which fields to prefer from each source
- Critical warning about description vs summary fields from API
- Common pitfalls to avoid

### 2. `/src/mk_torrent/core/metadata/sources/audnexus.py`

**⚠️ AUDNEXUS API FIELD USAGE WARNINGS**

- Fields to prefer: description, summary, title, author, narrator, publisher, genres
- Critical warning about description (truncated) vs summary (full) fields
- Fields to avoid: Technical audio specs not available from API

### 3. `/src/mk_torrent/core/metadata/sources/embedded.py`

**⚠️ EMBEDDED METADATA FIELD USAGE WARNINGS**

- Fields to prefer: ALL technical fields (bitrate, sample_rate, channels, etc.)
- Critical technical accuracy notes about precise measurements
- Fields to avoid: Descriptive metadata (inconsistent between encoders)

### 4. `/src/mk_torrent/core/metadata/sources/pathinfo.py`

**⚠️ PATH SOURCE FIELD USAGE WARNINGS**

- Fields to prefer: series, volume, asin (for compliance)
- Critical compliance priority notes
- Fields to avoid: Technical specs and long descriptions not in filenames

### 5. `/src/mk_torrent/core/metadata/mappers/red.py`

**⚠️ RED MAPPER FIELD USAGE WARNINGS**

- Critical guidance on using metadata.description (post-processed)
- Always use metadata.technical.* for audio specs
- Avoid legacy field access patterns

### 6. `/src/mk_torrent/core/metadata/processors/audiobook.py`

**⚠️ AUDIOBOOK PROCESSOR SOURCE INTEGRATION WARNINGS**

- Three-source strategy overview
- Integration principles and source responsibilities
- Avoid manual field selection bypassing the merger

### 7. `/src/mk_torrent/core/metadata/base.py`

**⚠️ FIELD USAGE GUIDELINES** (in AudiobookMeta class)

- Description field post-processing explanation
- Technical fields usage via .technical container
- Legacy compatibility notes

### 8. `/src/mk_torrent/core/metadata/engine.py`

**⚠️ METADATA ENGINE FIELD STRATEGY WARNINGS**

- Three-source architecture overview
- Intelligent merging strategy
- Critical post-processing explanations
- Do not bypass engine warnings

## Key Principles Established

### Source Specialization

- **API Source**: Best for descriptive metadata (titles, descriptions, genres)
- **Embedded Source**: Best for technical metadata (precise file properties)
- **Path Source**: Best for compliance metadata (series, volume, ASIN)

### Critical Field Issues Addressed

- **description vs summary**: API provides both, summary is usually complete
- **Technical precision**: Always use .technical container for accuracy
- **Post-processing**: Engine intelligently selects best available content

### Data Loss Prevention

- Each source contributes what it does best
- Intelligent merging prevents field conflicts
- Technical data preserved without degradation
- Smart precedence rules avoid truncation

## Benefits

1. **Prevents Future Confusion**: Clear guidance on which fields to use from each source
2. **Avoids Data Loss**: Warnings prevent developers from choosing wrong field variants
3. **Ensures Consistency**: Standardized approach to field selection across the codebase
4. **Documents Best Practices**: Captures learned lessons about source reliability
5. **Guides New Developers**: Clear instructions for proper field usage

## Impact

These warnings solve the root cause of the description vs summary confusion by:

- Making field selection intentional rather than accidental
- Documenting source strengths and weaknesses
- Preventing bypass of intelligent merging logic
- Ensuring technical accuracy and descriptive completeness

The system now has comprehensive guidance to prevent similar field mix-ups in the future.
