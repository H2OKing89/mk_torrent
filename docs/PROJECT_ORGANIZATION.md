# Project Organization Guide

## Directory Structure

```
mk_torrent/
├── 📁 docs/                    # All documentation
│   ├── AUDIOBOOK_METADATA_BREAKTHROUGH.md
│   ├── TRACKER_UPLOAD_ENHANCEMENT.md
│   └── ... (other docs)
├── 📁 scripts/                 # Utility scripts and runners
│   ├── run.py                 # Application entry point
│   ├── test_metadata.py       # Metadata test runner
│   └── test_mutagen_m4b.py    # Audio testing script
├── 📁 tests/                  # Unit and integration tests
├── 📁 test_results/           # Test output and reports
├── 📁 examples/               # Example usage files
├── 📁 qBittorrent-api/        # API documentation
├── 🐍 *.py                    # Core application modules
├── 📋 pyproject.toml          # Project configuration
├── 📋 requirements.txt        # Dependencies
├── 📋 setup.py               # Legacy setup (consider removing)
├── 📋 README.md              # Project documentation
└── 📋 LICENSE                # License file
```

## File Organization Rules

### ✅ Keep in Root:
- Core application modules (`*.py`)
- Project configuration (`pyproject.toml`, `requirements.txt`)
- Essential docs (`README.md`, `LICENSE`)
- Entry points (`__init__.py`, `__main__.py`)

### 📁 Move to Subdirectories:
- Documentation → `docs/`
- Scripts/tools → `scripts/`
- Test files → `tests/`
- Examples → `examples/`
- Test results → `test_results/`

### 🗑️ Remove:
- Empty files
- Temporary files
- Cache directories (use `.gitignore`)
- Duplicate files

## Maintenance Tips

1. **Regular cleanup**: Run `find . -name "*.pyc" -delete` periodically
2. **Cache management**: Clear `__pycache__/` and `.pytest_cache/` when needed
3. **Test results**: Use `python test_runner.py clean` to clear old results
4. **Git status**: Keep working directory clean before commits

## Quick Commands

```bash
# Clean Python cache
find . -name "__pycache__" -type d -exec rm -rf {} +

# Clean test cache
rm -rf .pytest_cache/

# Clean all test results
python test_runner.py clean

# Check for large files
find . -size +1M -ls
```
