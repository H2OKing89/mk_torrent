# 🚀 Quick Start Guide

## Prerequisites

- ✅ Python 3.8+ installed
- ✅ qBittorrent running with Web UI
- ✅ Project installed (see [Installation Guide](INSTALLATION.md))

## First Time Setup

### 1. Run Setup Wizard
```bash
python scripts/run_new.py setup
```

This configures:
- qBittorrent connection
- Default directories
- Secure credentials
- Tracker settings

### 2. Verify Configuration
```bash
python scripts/run_new.py health
```

Expected output:
```
✅ qBittorrent: Connected
✅ Credentials: Secure
✅ Directories: Valid
✅ API: Ready
```

## Basic Usage

### Create a Simple Torrent

```bash
# Single file
python scripts/run_new.py create /path/to/file.mp3

# Directory
python scripts/run_new.py create /path/to/album/
```

### Upload to Tracker

```bash
# Upload with metadata
python scripts/run_new.py upload /path/to/torrent.torrent \
  --tracker red \
  --category audiobook \
  --title "Book Title" \
  --author "Author Name"
```

## Common Workflows

### Audiobook Upload
```bash
# 1. Prepare files
python scripts/run_new.py prepare /path/to/audiobook/ \
  --format m4b \
  --metadata auto

# 2. Create torrent
python scripts/run_new.py create /path/to/audiobook.m4b \
  --private \
  --trackers "https://tracker.example.com/announce"

# 3. Upload
python scripts/run_new.py upload audiobook.torrent \
  --tracker red \
  --category audiobook \
  --tags "fiction,unabridged"
```

### Batch Processing
```bash
# Process multiple directories
python scripts/run_new.py batch /path/to/audiobooks/ \
  --recursive \
  --format m4b \
  --upload red
```

## Command Reference

### Core Commands
```bash
# Setup and configuration
setup          # Interactive setup wizard
health         # System health check
config         # View/edit configuration

# Torrent creation
create         # Create torrent from file/directory
prepare        # Prepare files with metadata
batch          # Batch process multiple items

# Upload and management
upload         # Upload torrent to tracker
status         # Check upload status
queue          # Manage upload queue
```

### Common Options
```bash
# File options
--format m4b|mp3|flac    # Audio format
--metadata auto|manual   # Metadata handling
--private                # Private torrent flag

# Tracker options
--tracker red|ops|ptl    # Target tracker
--category audiobook|music|software
--tags "tag1,tag2"      # Comma-separated tags

# Output options
--output /path/to/output # Custom output directory
--verbose               # Detailed output
--dry-run               # Preview without executing
```

## Examples

### Simple File Upload
```bash
python scripts/run_new.py create book.m4b \
  --private \
  --trackers "udp://tracker.opentrackr.org:1337/announce" \
  --output ./torrents/

python scripts/run_new.py upload ./torrents/book.torrent \
  --tracker red \
  --title "The Great Book" \
  --author "Famous Author" \
  --year 2024 \
  --format "Unabridged Audiobook"
```

### Directory with Metadata
```bash
python scripts/run_new.py prepare ./audiobook_series/ \
  --metadata auto \
  --format m4b

python scripts/run_new.py create ./audiobook_series/ \
  --private \
  --piece-size 16 \
  --output ./torrents/

python scripts/run_new.py upload ./torrents/series.torrent \
  --tracker red \
  --category audiobook \
  --tags "series,unabridged,fiction"
```

## Troubleshooting

### Quick Fixes
```bash
# Clear cache and retry
python scripts/run_new.py clean

# Reset configuration
python scripts/run_new.py setup --reset

# Verbose logging
python scripts/run_new.py create /path/to/file --verbose
```

### Common Errors
- **Connection failed**: Check qBittorrent is running
- **Permission denied**: Run with proper permissions
- **Invalid metadata**: Use `--metadata manual` for manual entry

## Next Steps

- 📖 [User Guide](USER_GUIDE.md) - Advanced features
- 🔧 [Configuration](CONFIGURATION.md) - Detailed settings
- 🧪 [Testing Guide](TESTING_GUIDE.md) - Quality assurance
