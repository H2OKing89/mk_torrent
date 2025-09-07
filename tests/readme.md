# Integration Tests

This directory contains integration tests for the mk_torrent project.

## Test Organization

### Core Test Files

1. **`test_red_api.py`** (333 lines)
   - **Purpose**: Unit tests for RED API functionality
   - **Scope**: API validation, path compliance, metadata validation
   - **Input**: Mock data only (no real files)
   - **Focus**: RED API behavior in isolation

2. **`test_red_integration.py`** (532 lines)
   - **Purpose**: Integration tests with real audiobook files
   - **Scope**: End-to-end RED workflow with actual M4B files
   - **Input**: Real audiobook samples from test_audiobooks/
   - **Focus**: RED integration with real data

3. **`test_metadata_engine.py`** (530 lines)
   - **Purpose**: Tests for the metadata extraction engine
   - **Scope**: Tag normalization, mappers, extraction pipeline
   - **Input**: Real audiobook files for engine validation
   - **Focus**: Core metadata functionality

4. **`test_template_integration.py`** (152 lines)
   - **Purpose**: Tests for BBCode template rendering
   - **Scope**: Template system, description generation
   - **Input**: Mock metadata for template testing
   - **Focus**: Template rendering and formatting

## Workflow Examples

- **`examples/audiobook_workflow.py`** (615 lines)
  - Complete workflow demonstration
  - Torrent creation, metadata extraction, RED upload
  - More of an example than a test

## Running Tests

```bash
# Run all integration tests
python -m pytest tests/integration/ -v

# Run specific test file
python -m pytest tests/integration/test_red_api.py -v

# Run with Rich output (development)
SHOW_RICH_TEST_OUTPUT=1 python -m pytest tests/integration/ -v
```

## Test Coverage

- **API Unit Tests**: RED API behavior without files
- **Integration Tests**: RED workflow with real files
- **Engine Tests**: Metadata extraction and processing
- **Template Tests**: BBCode generation and formatting

## CI/CD

Tests are designed to run in CI with minimal output:
- Use `SHOW_RICH_TEST_OUTPUT=0` (default) for clean CI output
- All tests pass with 48 passed, 2 skipped (conditional tests)
