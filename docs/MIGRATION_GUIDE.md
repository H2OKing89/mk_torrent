# Migration Guide: Root to Src Layout

This document explains the restructuring from flat root layout to organized src layout.

## Directory Changes

### Before (Root Layout)
```
mk_torrent/
├── cli.py
├── config.py
├── api_qbittorrent.py
├── torrent_creator.py
├── core_*.py
├── feature_*.py
├── utils_*.py
├── workflow_*.py
├── wizard.py
└── ... (28 Python files in root)
```

### After (Src Layout)
```
mk_torrent/
├── src/mk_torrent/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── api/
│   │   ├── qbittorrent.py
│   │   ├── red_integration.py
│   │   └── tracker_upload.py
│   ├── core/
│   │   ├── torrent_creator.py
│   │   ├── health_checks.py
│   │   ├── secure_credentials.py
│   │   └── upload_queue.py
│   ├── features/
│   │   ├── metadata_engine.py
│   │   ├── validator.py
│   │   ├── cross_seed.py
│   │   └── ... (other features)
│   ├── utils/
│   │   ├── async_helpers.py
│   │   ├── red_api_parser.py
│   │   └── ... (other utils)
│   └── workflows/
│       ├── wizard.py
│       └── audiobook_complete.py
├── tests/
├── docs/
├── examples/
├── scripts/
└── ... (config files)
```

## File Mapping

| Old Location | New Location |
|-------------|--------------|
| `api_qbittorrent.py` | `src/mk_torrent/api/qbittorrent.py` |
| `torrent_creator.py` | `src/mk_torrent/core/torrent_creator.py` |
| `core_*.py` | `src/mk_torrent/core/*.py` |
| `feature_*.py` | `src/mk_torrent/features/*.py` |
| `utils_*.py` | `src/mk_torrent/utils/*.py` |
| `workflow_*.py` | `src/mk_torrent/workflows/*.py` |
| `wizard.py` | `src/mk_torrent/workflows/wizard.py` |

## Import Changes

### Before
```python
from api_qbittorrent import QBittorrentAPI
from torrent_creator import TorrentCreator
from feature_metadata_engine import MetadataEngine
```

### After
```python
from mk_torrent.api.qbittorrent import QBittorrentAPI
from mk_torrent.core.torrent_creator import TorrentCreator
from mk_torrent.features.metadata_engine import MetadataEngine
```

## Running the Application

### Before
```bash
python run.py
python cli.py
```

### After
```bash
# Using new entry point
python scripts/run_new.py

# Or using module execution
python -m mk_torrent

# Or after pip install -e .
mk-torrent
```

## Testing

### Before
```bash
pytest
python test_runner.py run
```

### After
```bash
# Same commands, but PYTHONPATH is automatically set
pytest
python test_runner.py run
```

## Development Setup

1. **Editable Install** (Recommended):
   ```bash
   pip install -e .
   ```

2. **Manual PYTHONPATH**:
   ```bash
   export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
   ```

## Benefits Achieved

- ✅ **Separation of concerns**: Source code isolated from config/docs
- ✅ **Standard Python packaging**: Follows PEP 518/621 standards
- ✅ **Logical organization**: Related modules grouped together
- ✅ **Namespace protection**: Prevents import conflicts
- ✅ **Pip installable**: Can be installed as a proper Python package
- ✅ **IDE friendly**: Better IntelliSense and navigation
- ✅ **Clean root**: Only essential files at project root

## Next Steps

1. Test the new structure with `python scripts/run_new.py`
2. Update any scripts that import the old modules
3. Consider removing old files after verification
4. Update CI/CD pipelines if needed
