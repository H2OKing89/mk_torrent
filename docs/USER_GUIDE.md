# 📖 User Guide

## Table of Contents

- [Core Concepts](#core-concepts)
- [Advanced Features](#advanced-features)
- [Workflow Examples](#workflow-examples)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Core Concepts

### Torrent Creation

#### File Selection
```bash
# Single file
python scripts/run_new.py create path/to/file.mp3

# Multiple files
python scripts/run_new.py create path/to/directory/

# Recursive directory
python scripts/run_new.py create path/to/collection/ --recursive
```

#### Piece Size Optimization
```bash
# Auto-detect (recommended)
python scripts/run_new.py create large_file.iso

# Manual piece size
python scripts/run_new.py create file.mp4 --piece-size 16

# Small files (< 1GB)
python scripts/run_new.py create small_files/ --piece-size 4
```

### Metadata Management

#### Automatic Metadata
```bash
# From filename
python scripts/run_new.py prepare audiobook.mp3 --metadata auto

# From directory structure
python scripts/run_new.py prepare "Author - Book Title/" --metadata auto
```

#### Manual Metadata Entry
```bash
python scripts/run_new.py prepare file.m4b --metadata manual \
  --title "Book Title" \
  --author "Author Name" \
  --narrator "Narrator Name" \
  --year 2024 \
  --genre "Fiction"
```

#### Metadata Sources
- **Audnexus API**: Automatic lookup by ISBN/ASIN
- **File Tags**: ID3v2, MP4 metadata
- **Directory Names**: Parsed author/title patterns
- **Manual Entry**: Interactive prompts

### Tracker Integration

#### Supported Trackers
- **RED**: Audiobook-focused private tracker
- **OPS**: General private tracker
- **PTL**: Private tracker network

#### Upload Configuration
```bash
# RED upload
python scripts/run_new.py upload torrent.torrent --tracker red \
  --category audiobook \
  --tags "unabridged,fiction" \
  --description "High-quality audiobook"

# Batch upload
python scripts/run_new.py batch ./torrents/ --upload red --category audiobook
```

## Advanced Features

### Batch Processing

#### Directory Scanning
```bash
# Process all subdirectories
python scripts/run_new.py batch /path/to/audiobooks/ --recursive

# Filter by file type
python scripts/run_new.py batch /path/to/files/ --filter "*.m4b"

# Custom naming pattern
python scripts/run_new.py batch /path/to/files/ --pattern "Author - Title"
```

#### Queue Management
```bash
# Add to upload queue
python scripts/run_new.py queue add torrent.torrent --tracker red

# Process queue
python scripts/run_new.py queue process

# View queue status
python scripts/run_new.py queue status
```

### File Preparation

#### Audio Format Conversion
```bash
# Convert to M4B (chapter support)
python scripts/run_new.py prepare audiobook/ --format m4b

# Convert to MP3 (compatibility)
python scripts/run_new.py prepare audiobook/ --format mp3 --bitrate 128k

# Keep original format
python scripts/run_new.py prepare audiobook/ --format preserve
```

#### Quality Validation
```bash
# Check audio quality
python scripts/run_new.py validate audiobook.m4b --quality

# Verify metadata completeness
python scripts/run_new.py validate audiobook.m4b --metadata

# Full validation suite
python scripts/run_new.py validate audiobook.m4b --full
```

### Docker Integration

#### Container Path Mapping
```json
{
  "docker_mappings": {
    "/host/path": "/container/path",
    "/mnt/data": "/data"
  }
}
```

#### Docker Commands
```bash
# Run in container
docker run --rm -v $(pwd):/app mk-torrent create /app/file.mp3

# With qBittorrent
docker-compose up -d qbittorrent
docker run --network container:qbittorrent mk-torrent upload torrent.torrent
```

## Workflow Examples

### Audiobook Production Pipeline

```bash
# 1. Prepare source files
python scripts/run_new.py prepare ./raw_audiobook/ \
  --format m4b \
  --metadata auto \
  --isbn 9780123456789

# 2. Validate quality
python scripts/run_new.py validate ./prepared_audiobook.m4b \
  --quality \
  --metadata

# 3. Create torrent
python scripts/run_new.py create ./prepared_audiobook.m4b \
  --private \
  --piece-size 16 \
  --trackers "https://tracker.example.com/announce"

# 4. Upload to tracker
python scripts/run_new.py upload audiobook.torrent \
  --tracker red \
  --category audiobook \
  --tags "unabridged,fiction,mystery" \
  --description "Professional narration by acclaimed actor"
```

### Bulk Processing Workflow

```bash
# 1. Scan directory
python scripts/run_new.py batch ./audiobook_library/ \
  --recursive \
  --filter "*.m4b" \
  --output ./processed/

# 2. Batch metadata update
python scripts/run_new.py batch ./processed/ \
  --metadata-update \
  --source audnexus

# 3. Create torrents
python scripts/run_new.py batch ./processed/ \
  --create-torrents \
  --private \
  --trackers "udp://tracker.opentrackr.org:1337/announce"

# 4. Queue for upload
python scripts/run_new.py batch ./torrents/ \
  --queue-upload \
  --tracker red \
  --category audiobook
```

### Quality Assurance Pipeline

```bash
# 1. Pre-upload validation
python scripts/run_new.py validate ./torrent.torrent \
  --full \
  --report validation_report.json

# 2. Test download
python scripts/run_new.py test-download ./torrent.torrent \
  --verify-integrity \
  --check-metadata

# 3. Generate upload report
python scripts/run_new.py upload ./torrent.torrent \
  --tracker red \
  --dry-run \
  --report upload_preview.json
```

## Configuration

### Configuration Files

#### Main Configuration
Location: `~/.config/mk_torrent/config.json`
```json
{
  "qbittorrent": {
    "host": "localhost",
    "port": 8080,
    "username": "admin",
    "password": "encrypted"
  },
  "directories": {
    "input": "~/audiobooks",
    "output": "~/torrents",
    "temp": "~/temp"
  },
  "trackers": {
    "red": {
      "api_key": "encrypted",
      "upload_url": "https://redacted.ch/upload.php"
    }
  }
}
```

#### Advanced Configuration
```json
{
  "processing": {
    "max_concurrent_jobs": 4,
    "piece_size_algorithm": "auto",
    "metadata_sources": ["audnexus", "file_tags", "directory"]
  },
  "quality": {
    "min_bitrate": 64,
    "max_bitrate": 320,
    "allowed_formats": ["mp3", "m4b", "flac"],
    "require_chapters": true
  },
  "upload": {
    "retry_attempts": 3,
    "retry_delay": 30,
    "queue_size": 10
  }
}
```

### Environment Variables
```bash
# Override configuration
export MK_TORRENT_QBITTORRENT_HOST="192.168.1.100"
export MK_TORRENT_QBITTORRENT_PORT="9090"
export MK_TORRENT_VERBOSE="true"

# API keys
export AUDNEXUS_API_KEY="your_api_key"
export RED_API_KEY="your_red_api_key"
```

## Troubleshooting

### Performance Issues

#### Slow Torrent Creation
```bash
# Increase piece size for large files
python scripts/run_new.py create large_file.iso --piece-size 32

# Use SSD storage
# Process in parallel
python scripts/run_new.py batch ./files/ --parallel 4
```

#### Memory Usage
```bash
# Process in chunks
python scripts/run_new.py batch ./large_collection/ --chunk-size 10

# Clear temp files
python scripts/run_new.py clean --temp
```

### Network Issues

#### Connection Timeouts
```bash
# Increase timeout
python scripts/run_new.py upload torrent.torrent --timeout 300

# Retry with backoff
python scripts/run_new.py upload torrent.torrent --retry 5 --backoff
```

#### Proxy Configuration
```bash
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
```

### File System Issues

#### Permission Errors
```bash
# Fix permissions
chmod -R 755 /path/to/audiobooks/
chown -R $USER:$USER /path/to/output/

# Run with sudo (not recommended)
sudo python scripts/run_new.py create /path/to/file
```

#### Path Mapping Issues
```bash
# Check Docker paths
docker inspect qbittorrent | grep -A 10 Mounts

# Update mappings
python scripts/run_new.py config --update-mappings
```

### Metadata Issues

#### Missing Metadata
```bash
# Manual entry
python scripts/run_new.py prepare file.mp3 --metadata manual

# Search online
python scripts/run_new.py prepare file.mp3 --metadata search --query "book title"
```

#### Incorrect Metadata
```bash
# Edit metadata
python scripts/run_new.py edit-metadata file.mp3 \
  --title "Correct Title" \
  --author "Correct Author"

# Revert changes
python scripts/run_new.py edit-metadata file.mp3 --revert
```

## Best Practices

### File Organization
```
audiobooks/
├── author_name/
│   ├── book_title_01.m4b
│   ├── book_title_02.m4b
│   └── metadata.json
└── series_name/
    ├── book_01.m4b
    ├── book_02.m4b
    └── series_metadata.json
```

### Quality Standards
- **Audio**: 64kbps minimum, 320kbps maximum
- **Formats**: M4B preferred for chapters, MP3 for compatibility
- **Metadata**: Complete author, title, narrator information
- **Torrents**: Private flag, optimized piece sizes

### Backup Strategy
```bash
# Backup configuration
cp ~/.config/mk_torrent/config.json ~/backup/

# Backup secure credentials
python scripts/run_new.py backup-credentials ~/backup/

# Full system backup
tar -czf mk_torrent_backup.tar.gz \
  ~/.config/mk_torrent/ \
  ~/torrents/ \
  ~/audiobooks/
```

## Support

### Getting Help
- 📖 [Documentation](https://github.com/H2OKing89/mk_torrent/wiki)
- 🐛 [Issue Tracker](https://github.com/H2OKing89/mk_torrent/issues)
- 💬 [Discussions](https://github.com/H2OKing89/mk_torrent/discussions)

### Debug Information
```bash
# System information
python scripts/run_new.py info

# Verbose logging
python scripts/run_new.py create file.mp3 --verbose --log debug.log

# Configuration dump
python scripts/run_new.py config --dump
```
