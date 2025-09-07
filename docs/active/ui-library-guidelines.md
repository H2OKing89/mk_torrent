# UI Library Usage Guidelines

## Architecture Principles

### Core Library Modules (NO rich dependency)

- `src/mk_torrent/core/metadata/` - Metadata processors
- `src/mk_torrent/core/torrent/` - Torrent creation
- `src/mk_torrent/integrations/` - External API integrations
- Use **standard Python logging** only

### User Interface Modules (rich encouraged)

- `src/mk_torrent/cli/` - Command line interfaces
- `src/mk_torrent/features/validator.py` - User-facing validation
- Test scripts (`test_*.py`) - Enhanced test output
- Use **rich** for better user experience

### Utility Modules (conditional rich)

- `src/mk_torrent/utils/` - Can use rich if UI-related, logging if core

## Current Status

### ✅ Correctly using standard logging

- `src/mk_torrent/core/metadata/audiobook.py`
- `src/mk_torrent/core/metadata/engine.py`

### ✅ Correctly using rich (UI modules)

- `test_metadata_comprehensive.py`
- `test_red_integration.py`
- `src/mk_torrent/features/validator.py`

### ⚠️ Should be reviewed

- `src/mk_torrent/utils/async_helpers.py` - Using rich for progress bars (acceptable)

## Rationale

1. **Core modules** should have minimal dependencies for:
   - Better testability
   - Library reusability
   - Reduced dependency conflicts
   - Clear separation of concerns

2. **UI modules** should use rich for:
   - Better user experience
   - Enhanced readability
   - Progress indication
   - Error formatting

This ensures the core functionality remains lightweight while user-facing components provide excellent UX.
