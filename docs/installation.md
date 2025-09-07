# 📦 Installation Guide

## System Requirements

- Python 3.8 or higher
- qBittorrent 4.3+ (Web UI enabled)
- 1GB+ free disk space
- Linux/macOS/Windows (WSL)

## Quick Install

```bash
# Clone repository
git clone https://github.com/H2OKing89/mk_torrent.git
cd mk_torrent

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python scripts/run_new.py setup
```

## Detailed Installation

### 1. Prerequisites

#### Python Installation

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.8 python3-pip python3-venv

# RHEL/CentOS/Fedora
sudo dnf install python3.8 python3-pip

# macOS (with Homebrew)
brew install python@3.8
```

#### qBittorrent Setup

```bash
# Install qBittorrent
sudo apt install qbittorrent-nox  # Headless version

# Or use Docker
docker pull qbittorrentofficial/qbittorrent-nox:latest
```

### 2. Installation Methods

#### Method A: From Source (Recommended)

```bash
git clone https://github.com/H2OKing89/mk_torrent.git
cd mk_torrent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Method B: Editable Install (For Development)

```bash
git clone https://github.com/H2OKing89/mk_torrent.git
cd mk_torrent
pip install -e .
```

### 3. Configuration

Run the setup wizard to configure:

```bash
python scripts/run_new.py setup
```

This will configure:

- qBittorrent connection settings
- Docker path mappings (if applicable)
- Secure credential storage
- Default directories
- Tracker URLs

### 4. Verify Installation

```bash
# Check installation
python scripts/run_new.py health

# Run tests
python test_runner.py run
```

## Docker Installation

### Using Docker Compose

```yaml
version: '3.8'
services:
  qbittorrent:
    image: qbittorrentofficial/qbittorrent-nox:latest
    container_name: qbittorrent
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
      - WEBUI_PORT=8080
    volumes:
      - ./config:/config
      - ./downloads:/downloads
    ports:
      - 8080:8080
    restart: unless-stopped
```

### Path Mapping for Docker

```json
{
  "docker_mappings": {
    "/mnt/user/data": "/data",
    "/mnt/cache/downloads": "/downloads"
  }
}
```

## Troubleshooting

### Common Issues

#### ImportError: No module named 'xxx'

```bash
# Ensure you're in virtual environment
source .venv/bin/activate
# Reinstall dependencies
pip install -r requirements.txt
```

#### Permission Denied

```bash
# Fix file permissions
chmod +x scripts/run_new.py
chmod 600 ~/.config/torrent_creator/secure_config.enc
```

#### qBittorrent Connection Failed

```bash
# Check qBittorrent is running
systemctl status qbittorrent-nox

# Verify Web UI is enabled
# Default: http://localhost:8080
```

## Next Steps

- 🎯 Quick Start Guide
- 📖 User Guide
- 🔐 Security Setup
