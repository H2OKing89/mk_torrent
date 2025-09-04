# Integration Test Examples

This directory contains standalone integration test scripts that demonstrate the functionality of the mk_torrent system.

## Files

### `test_audiobook_processor.py`
Demonstrates the new audiobook processor with Audnexus API integration:
- Extracts metadata from real audiobook files
- Shows API vs filename parsing comparison
- Validates AudiobookMeta object creation
- Compares old vs new system implementations

### `test_audnexus_integration.py`
Tests the Audnexus API integration specifically:
- ASIN extraction and validation
- Real API calls to Audnexus database
- Chapter fetching functionality
- Data normalization verification

## Usage

Run from the project root:

```bash
python examples/integration_tests/test_audiobook_processor.py
python examples/integration_tests/test_audnexus_integration.py
```

## Purpose

These scripts serve as:
- Integration testing demonstrations
- Development debugging tools
- Examples of how to use the metadata system
- Validation of API integrations

They are not part of the formal pytest test suite but provide valuable integration testing capabilities.
