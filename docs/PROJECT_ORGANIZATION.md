# Project Organization Guide

## New Src Layout Structure

```
mk_torrent/
├── 📁 src/mk_torrent/           # Main source code package
│   ├── __init__.py             # Package initialization
│   ├── __main__.py             # Module execution entry point
│   ├── cli.py                  # Main CLI interface
│   ├── config.py               # Configuration management
│   ├── 📁 api/                 # External API integrations
│   │   ├── qbittorrent.py      # qBittorrent API client
│   │   ├── red_integration.py  # RED tracker integration
│   │   └── tracker_upload.py   # Generic tracker upload
│   ├── 📁 core/                # Core application logic
│   │   ├── torrent_creator.py  # Torrent creation engine
│   │   ├── health_checks.py    # System health monitoring
│   │   ├── secure_credentials.py # Credential management
│   │   └── upload_queue.py     # Upload queue management
│   ├── 📁 features/            # Extended functionality
│   │   ├── metadata_engine.py  # Metadata processing
│   │   ├── validator.py        # File/path validation
│   │   ├── cross_seed.py       # Cross-seeding features
│   │   ├── red_uploader.py     # RED-specific uploading
│   │   └── templates.py        # Template management
│   ├── 📁 utils/               # Utility modules
│   │   ├── async_helpers.py    # Async utilities
│   │   ├── red_api_parser.py   # RED API parsing
│   │   └── red_compliance.py   # RED compliance checks
│   └── 📁 workflows/           # Automated workflows
│       ├── wizard.py           # Setup wizard
│       └── audiobook_complete.py # Audiobook workflow
├── 📁 tests/                   # Unit and integration tests
├── 📁 test_results/            # Test output and reports
├── 📁 docs/                    # All documentation
├── 📁 examples/                # Example usage files
├── 📁 scripts/                 # Utility scripts and runners
│   ├── run_new.py             # New entry point script
│   ├── test_metadata.py       # Metadata test runner
│   └── test_mutagen_m4b.py    # Audio testing script
├── � pyproject.toml          # Modern Python project config
├── 📋 requirements.txt        # Dependencies
├── 📋 test_runner.py          # Test management script
├── 📋 README.md              # Project documentation
└── 📋 LICENSE                # License file
```

## Benefits of Src Layout

### ✅ **Organization Benefits:**
- **Logical grouping**: Related modules are organized by purpose
- **Clear separation**: Source code isolated from config/docs/tests
- **Namespace protection**: Prevents accidental imports during development
- **Standard compliance**: Follows modern Python packaging standards

### ✅ **Development Benefits:**
- **IDE support**: Better IntelliSense and code navigation
- **Import clarity**: Clear module hierarchy and relationships
- **Testing isolation**: Tests import from installed package, not source
- **Pip installable**: Can be installed as proper Python package

### ✅ **Maintenance Benefits:**
- **Scalability**: Easy to add new modules in appropriate categories
- **Refactoring**: Module moves don't break external imports
- **Documentation**: Structure is self-documenting
- **Collaboration**: New developers understand organization quickly

## Module Categories

### 🔌 **API Package** (`src/mk_torrent/api/`)
External service integrations and client libraries.

### ⚙️ **Core Package** (`src/mk_torrent/core/`)
Essential application logic and base functionality.

### 🎯 **Features Package** (`src/mk_torrent/features/`)
Extended functionality and specialized modules.

### 🛠️ **Utils Package** (`src/mk_torrent/utils/`)
Helper functions and utility modules.

### 🔄 **Workflows Package** (`src/mk_torrent/workflows/`)
Automated processes and multi-step operations.

## Usage Examples

### Running the Application
```bash
# Using new entry point
python scripts/run_new.py

# Using module execution
python -m mk_torrent

# After pip install -e .
mk-torrent
```

### Importing Modules
```python
# Import from organized packages
from mk_torrent.core.torrent_creator import TorrentCreator
from mk_torrent.api.qbittorrent import QBittorrentAPI
from mk_torrent.features.metadata_engine import MetadataEngine
```

## Migration Notes

- Old files remain in root for reference
- New entry point: `scripts/run_new.py`
- Tests updated to use src layout
- pyproject.toml configured for src layout
- See `docs/MIGRATION_GUIDE.md` for details
