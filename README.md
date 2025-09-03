![CI](https://github.com/H2OKing89/mk_torrent/actions/workflows/ci.yml/badge.svg)

# 🎯 MK Torrent - Interactive Torrent Creator

[![Tests](https://img.shields.io/badge/Tests-122%20passing-brightgreen)](tests/)
[![Security](https://img.shields.io/badge/Security-Enterprise-green.svg)](docs/SECURITY.md)
[![Encryption](https://img.shields.io/badge/Encryption-AES--256-blue.svg)](docs/SECURITY.md)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A professional torrent creation toolkit with enterprise-grade security, RED tracker support, and beautiful CLI interface.**

![Terminal Demo](docs/assets/demo.gif)

## ✨ Key Features

- 🔐 **Enterprise Security** - AES-256 encryption for all credentials
- 🎨 **Beautiful CLI** - Rich terminal UI with progress bars and colors
- 📚 **Audiobook Support** - Advanced metadata extraction and RED compliance
- 🐳 **Docker Ready** - Seamless qBittorrent container integration
- 📦 **Batch Operations** - Process entire libraries efficiently
- 🎯 **RED Integration** - Full tracker API support with validation
- 🧪 **Well Tested** - 122+ tests with comprehensive coverage

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/H2OKing89/mk_torrent.git
cd mk_torrent

# Install dependencies
pip install -r requirements.txt

# Run initial setup
python scripts/run_new.py setup

# Create your first torrent
python scripts/run_new.py create
```

📖 **[Full Installation Guide →](docs/INSTALLATION.md)**

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| 📦 **[Installation](docs/INSTALLATION.md)** | Setup, dependencies, and configuration |
| 🎯 **[Quick Start](docs/QUICK_START.md)** | Get up and running in 5 minutes |
| 📖 **[User Guide](docs/USER_GUIDE.md)** | Complete feature documentation |
| 🔐 **[Security](docs/SECURITY.md)** | Credential encryption and best practices |
| 🎵 **[Audiobooks](docs/AUDIOBOOKS.md)** | RED tracker integration and metadata |
| 🔧 **[API Reference](docs/reference/API_REFERENCE.md)** | Developer documentation |
| ❓ **[FAQ](docs/FAQ.md)** | Common questions and troubleshooting |

## 🎮 Basic Usage

```bash
# Interactive torrent creation
python scripts/run_new.py create

# Batch process a directory
python scripts/run_new.py batch /path/to/content

# Audiobook with metadata
python scripts/run_new.py audiobook /path/to/audiobook.m4b

# Check system health
python scripts/run_new.py health
```

📖 **[See All Commands →](docs/USER_GUIDE.md)**

## 🏗️ Project Structure

```
mk_torrent/
├── src/mk_torrent/     # Source code (organized by feature)
├── tests/              # Comprehensive test suite
├── docs/               # Documentation
├── scripts/            # Utility scripts
└── examples/           # Usage examples
```

🔍 **[Architecture Details →](docs/reference/PROJECT_STRUCTURE.md)**

## 🤝 Contributing

We welcome contributions! Please see our Contributing Guide for details.

```bash
# Run tests before submitting PR
python test_runner.py run

# Check code style
black src/ tests/
flake8 src/ tests/
```

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [qBittorrent](https://www.qbittorrent.org/) for the excellent torrent client
- [Rich](https://github.com/Textualize/rich) for beautiful terminal formatting
- [RED](https://redacted.ch/) for tracker API documentation
- All contributors and testers

---

<p align="center">
  <a href="docs/QUICK_START.md">Get Started</a> •
  <a href="docs/USER_GUIDE.md">User Guide</a> •
  <a href="docs/reference/API_REFERENCE.md">API Docs</a> •
  <a href="https://github.com/H2OKing89/mk_torrent/issues">Report Bug</a>
</p>
