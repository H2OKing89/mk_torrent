# ❓ Frequently Asked Questions

## General Questions

### What is mk_torrent?

mk_torrent is a comprehensive Python tool for creating and managing torrents, with specialized support for audiobook workflows. It integrates with qBittorrent and supports multiple private trackers.

### Why use mk_torrent over other tools?

- **Audiobook-focused**: Specialized metadata handling for audiobooks
- **Secure**: Encrypted credential storage and secure API handling
- **Batch processing**: Efficient handling of large audiobook collections
- **Tracker integration**: Native support for RED, OPS, and other private trackers
- **Quality assurance**: Built-in validation and quality checks

### Is it free?

Yes, mk_torrent is open-source software released under the MIT License.

## Installation & Setup

### System Requirements

**Q: What are the minimum system requirements?**

A: Python 3.8+, qBittorrent 4.3+, 1GB free space, Linux/macOS/Windows.

**Q: Can I run it on a Raspberry Pi?**

A: Yes, but performance may be limited for large files. Use external storage for better performance.

### Installation Issues

**Q: Getting "ModuleNotFoundError" after installation**

A: Ensure you're using the virtual environment:

```bash
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

**Q: qBittorrent connection failed**

A: Check:

1. qBittorrent is running
2. Web UI is enabled (default: <http://localhost:8080>)
3. Correct username/password
4. Firewall isn't blocking port 8080

### Configuration

**Q: How do I configure multiple trackers?**

A: Edit `~/.config/mk_torrent/config.json`:

```json
{
  "trackers": {
    "red": {
      "api_key": "your_red_key",
      "upload_url": "https://redacted.ch/upload.php"
    },
    "ops": {
      "username": "your_ops_user",
      "api_key": "your_ops_key"
    }
  }
}
```

## Usage Questions

### Torrent Creation

**Q: What's the optimal piece size?**

A:

- Small files (< 1GB): 4MB - 8MB pieces
- Medium files (1GB - 10GB): 8MB - 16MB pieces
- Large files (> 10GB): 16MB - 32MB pieces
- Use `--piece-size auto` for automatic detection

**Q: How do I create private torrents?**

A: Use the `--private` flag:

```bash
python scripts/run_new.py create file.mp3 --private
```

### Metadata Handling

**Q: Metadata isn't being detected automatically**

A: Try:

1. Use `--metadata manual` for manual entry
2. Ensure filenames follow "Author - Title" format
3. Check for ID3 tags in audio files
4. Use Audnexus API with ISBN/ASIN

**Q: How do I update metadata for existing files?**

A:

```bash
python scripts/run_new.py prepare file.mp3 --metadata update \
  --title "New Title" \
  --author "New Author"
```

### Upload Issues

**Q: Upload to RED tracker failing**

A: Common causes:

1. Invalid API key
2. Missing required fields (category, tags)
3. File size limits exceeded
4. Rate limiting - wait and retry

**Q: How do I check upload status?**

A:

```bash
python scripts/run_new.py status --tracker red --torrent-id 12345
```

## Audio & File Handling

### Format Support

**Q: Which audio formats are supported?**

A: MP3, M4B, FLAC, AAC, OGG, WAV

**Q: Should I use M4B or MP3?**

A:

- **M4B**: Better for audiobooks (supports chapters, metadata)
- **MP3**: Better compatibility with older devices
- Use M4B for chapter books, MP3 for music/simple audiobooks

### Quality Settings

**Q: What's the recommended bitrate?**

A:

- **Speech/Mono**: 64kbps AAC/MP3
- **Audiobooks**: 128kbps MP3, 96kbps AAC
- **Music**: 192-320kbps depending on source quality

**Q: How do I convert audio formats?**

A:

```bash
python scripts/run_new.py prepare input.mp3 --format m4b --bitrate 128k
```

## Performance & Troubleshooting

### Performance Issues

**Q: Torrent creation is slow**

A: Solutions:

1. Use SSD storage
2. Increase piece size for large files
3. Process in parallel: `--parallel 4`
4. Close other applications using disk I/O

**Q: Memory usage is high**

A: For large files:

```bash
python scripts/run_new.py create large_file.iso --low-memory
```

### Error Messages

**Q: "Connection timeout" errors**

A: Increase timeout and retry:

```bash
python scripts/run_new.py upload torrent.torrent --timeout 300 --retry 3
```

**Q: "Permission denied" errors**

A: Fix permissions:

```bash
chmod 755 /path/to/files/
chown $USER:$USER /path/to/output/
```

### Docker Issues

**Q: Path mapping not working in Docker**

A: Update Docker configuration:

```json
{
  "docker_mappings": {
    "/host/path": "/container/path"
  }
}
```

## Security Questions

### Credential Security

**Q: Are my credentials secure?**

A: Yes, credentials are:

- Encrypted using AES-256
- Stored in system keyring when available
- Never logged in plain text
- Protected by file permissions (600)

**Q: How do I rotate API keys?**

A:

```bash
python scripts/run_new.py credentials rotate red_api_key
python scripts/run_new.py config --update-api-keys
```

### Data Privacy

**Q: What data is collected?**

A: Minimal data collection:

- Configuration settings (local only)
- Error logs (optional, local only)
- Performance metrics (optional, anonymous)

**Q: Can I disable telemetry?**

A:

```bash
export MK_TORRENT_TELEMETRY=false
python scripts/run_new.py config --telemetry off
```

## Advanced Usage

### Batch Processing

**Q: How do I process 100+ audiobooks?**

A:

```bash
python scripts/run_new.py batch /path/to/collection/ \
  --recursive \
  --filter "*.m4b" \
  --parallel 4 \
  --output /path/to/torrents/
```

**Q: Can I automate the workflow?**

A: Yes, create a script:

```bash
#!/bin/bash
# auto_process.sh
python scripts/run_new.py batch ./new_audiobooks/ --upload red
```

### Custom Scripts

**Q: How do I integrate with other tools?**

A: Use the Python API:

```python
from src.mk_torrent.api.torrent_creator import TorrentCreator

creator = TorrentCreator()
torrent = creator.create_torrent(
    path="/path/to/file",
    trackers=["udp://tracker.example.com"],
    private=True
)
```

## Development & Contributing

### Development Setup

**Q: How do I set up for development?**

A:

```bash
git clone https://github.com/H2OKing89/mk_torrent.git
cd mk_torrent
pip install -e .[dev]
pre-commit install
```

**Q: How do I run tests?**

A:

```bash
# All tests
python test_runner.py run

# Specific test
python -m pytest tests/test_specific.py -v

# With coverage
python -m pytest --cov=src/mk_torrent --cov-report=html
```

### Contributing

**Q: How do I contribute?**

A:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

**Q: What are the coding standards?**

A: Follow:

- PEP 8 style guide
- Type hints required
- Docstrings for all functions
- 80%+ test coverage

## Common Workflows

### Audiobook Pipeline

**Q: What's the complete audiobook workflow?**

A:

```bash
# 1. Prepare files
python scripts/run_new.py prepare ./audiobook/ --format m4b --metadata auto

# 2. Validate
python scripts/run_new.py validate ./audiobook.m4b --full

# 3. Create torrent
python scripts/run_new.py create ./audiobook.m4b --private

# 4. Upload
python scripts/run_new.py upload audiobook.torrent --tracker red --category audiobook
```

### Quality Assurance

**Q: How do I ensure high quality?**

A: Use the validation suite:

```bash
python scripts/run_new.py validate file.m4b \
  --quality \
  --metadata \
  --integrity \
  --report quality_report.json
```

## Support & Resources

### Getting Help

**Q: Where can I get help?**

A:

- 📖 [Documentation](https://github.com/H2OKing89/mk_torrent/wiki)
- 🐛 [Issues](https://github.com/H2OKing89/mk_torrent/issues)
- 💬 [Discussions](https://github.com/H2OKing89/mk_torrent/discussions)
- 📧 <support@mk-torrent.dev>

### Community

**Q: Is there a community?**

A:

- GitHub Discussions for questions
- Reddit: r/torrents, r/audiobooks
- Discord: [Invite link]

### Updates

**Q: How do I stay updated?**

A:

- Watch the GitHub repository
- Follow releases
- Check changelog
- Join mailing list

---

*Still have questions? Check the [User Guide](USER_GUIDE.md) or create an [issue](https://github.com/H2OKing89/mk_torrent/issues).*"
