# Integration Test Examples

This directory contains standalone integration test scripts that demonstrate the functionality of the mk_torrent system.

# Integration Test Examples

This directory contains standalone integration test scripts that demonstrate the functionality of the mk_torrent system.

## Files

### `audiobook_metadata_integration_demo.py`
Comprehensive integration test and demonstration of the complete audiobook metadata pipeline:
- **Three-source metadata extraction**: Audnexus API, embedded file metadata, and path-based parsing
- **Advanced metadata processing**: Smart field merging with declarative precedence rules
- **Rich visualization**: Progress bars, tables, and comparison trees (with rich library)
- **Performance features**: API response caching and fuzzy matching for comparisons
- **Full validation**: AudiobookMeta object creation, completeness scoring, and RED compliance
- **System comparison**: Side-by-side analysis of legacy vs new core architecture
- **Real-world testing**: Uses actual audiobook sample files with automatic fallback detection

### `test_audnexus_integration.py`
Focused test of the Audnexus API integration specifically:
- ASIN extraction and validation from various formats
- Real API calls to Audnexus database with error handling
- Chapter fetching and metadata normalization
- API response validation and data structure verification

## Usage

Run from the project root:

```bash
python examples/integration_tests/audiobook_metadata_integration_demo.py
python examples/integration_tests/test_audnexus_integration.py
```

## Purpose

These scripts serve as:
- **Primary integration validation**: End-to-end testing of the complete metadata pipeline
- **Architecture demonstration**: Showcasing the modular metadata core system capabilities
- **Development debugging tools**: Rich output for troubleshooting metadata extraction issues
- **Performance benchmarking**: Caching, fuzzy matching, and processing speed validation
- **Migration guidance**: Comparing legacy vs modern metadata system implementations
- **User education**: Comprehensive examples of how to use the metadata system effectively

They are not part of the formal pytest test suite but provide critical integration testing and demonstration capabilities for the metadata core system.
