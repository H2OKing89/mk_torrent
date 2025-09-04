# 🎯 MK Torrent - Interactive Torrent Creator

<!-- Status Badges -->
[![CI](https://github.com/H2OKing89/mk_torrent/actions/workflows/ci.yml/badge.svg)](https://github.com/H2OKing89/mk_torrent/actions/workflows/ci.yml)
[![Security](https://github.com/H2OKing89/mk_torrent/actions/workflows/security.yml/badge.svg)](https://github.com/H2OKing89/mk_torrent/actions/workflows/security.yml)
[![CodeQL](https://github.com/H2OKing89/mk_torrent/actions/workflows/codeql.yml/badge.svg)](https://github.com/H2OKing89/mk_torrent/actions/workflows/codeql.yml)
[![Documentation](https://github.com/H2OKing89/mk_torrent/actions/workflows/docs.yml/badge.svg)](https://github.com/H2OKing89/mk_torrent/actions/workflows/docs.yml)

<!-- Quality Badges -->
[![Tests](https://img.shields.io/badge/Tests-217%20passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/Coverage-70%25+-brightgreen)](https://codecov.io/gh/H2OKing89/mk_torrent)
[![Code Quality](https://img.shields.io/badge/Ruff-0%20issues-brightgreen)](https://github.com/astral-sh/ruff)
[![Security](https://img.shields.io/badge/Bandit-0%20issues-brightgreen)](https://bandit.readthedocs.io/)

<!-- Project Badges -->
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/H2OKing89/mk_torrent)](https://github.com/H2OKing89/mk_torrent/releases)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

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
