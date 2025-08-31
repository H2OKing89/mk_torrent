# 🎯 Interactive Torrent Creator

A user-friendly, interactive torrent creator for qBittorrent with Docker support.

## Features

- ✨ **Interactive CLI** - Beautiful terminal UI with colors and progress bars
- 🐳 **Docker Support** - Works with qBittorrent running in Docker containers
- 📦 **Batch Creation** - Create multiple torrents at once
- 📊 **History Tracking** - Keep track of all created torrents
- 🎨 **Rich UI** - Modern terminal interface with Rich library
- ⚡ **Quick Mode** - Fast torrent creation with minimal prompts
- 🧙 **Guided Wizard** - Step-by-step assistance for beginners
- 📋 **Templates** - Save and reuse torrent configurations
- ⚙️ **Config Editor** - Modify settings without re-running setup
- 🔍 **Path Validation** - Check paths before creating torrents

## Installation

```bash
# Navigate to the script directory
cd /mnt/cache/scripts/mk_torrent

# Create virtual environment (if not already created)
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install setuptools if needed
pip install setuptools wheel
```

## Quick Start

### Run the Application

```bash
# Using the run script (recommended)
python run.py [command]

# Or directly
python cli.py [command]
```

### First Time Setup
```bash
python run.py setup
```

### Create Single Torrent
```bash
python run.py create
```

### Create Multiple Torrents
```bash
python run.py create --batch
```

### Quick Creation (minimal prompts)
```bash
python run.py quick
```

### With Docker
```bash
python run.py create --docker qbittorrent
```

## Usage Examples

### Interactive Single Torrent
1. Run `python run.py create`
2. Enter the path to your file/folder
3. Choose output directory
4. Configure options (trackers, web seeds, etc.)
5. Torrent is created!

### Batch Creation
1. Run `python run.py create --batch`
2. Select base directory
3. Choose which items to create torrents for
4. Configure options (applied to all)
5. Watch the progress as torrents are created

### Docker Path Mapping

If qBittorrent runs in Docker, the script handles path mapping:

```
Host Path → Docker Path
/mnt/cache/downloads → /data/downloads
/mnt/user/media → /media
```

Configure custom mappings during setup or edit `~/.config/torrent_creator/config.json`

## Configuration

Config files are stored in `~/.config/torrent_creator/`:
- `config.json` - Main configuration
- `trackers.txt` - Default tracker URLs
- `history.db` - Torrent creation history

## Commands

### Core Commands
- `create` - Create torrent(s) interactively
- `wizard` - Guided wizard for common tasks
- `quick` - Quick torrent with defaults
- `batch` - Create multiple torrents

### Configuration
- `setup` - Initial setup wizard
- `config` - Edit configuration
- `config --show` - View current settings
- `config --reset` - Reset to defaults

### Management
- `history` - View recent torrent creations
- `templates` - Manage torrent templates
- `validate <path>` - Validate path for torrent creation
- `health` - Check qBittorrent connectivity

### Command Examples

```bash
# Initial setup
python run.py setup

# Guided wizard (recommended for beginners)
python run.py wizard

# Edit specific configuration
python run.py config

# View current configuration
python run.py config --show

# Create with template
python run.py templates  # Then select "Apply template"

# Validate a path before creating
python run.py validate /path/to/content

# Quick creation modes
python run.py quick  # Minimal prompts
python run.py create  # Interactive
python run.py create --batch  # Multiple torrents
python run.py wizard  # Guided experience

# Check system health
python run.py health
```

## 🧙 Wizard Mode

The wizard provides guided workflows for:
- **Single torrents** - Simple step-by-step creation
- **TV Series** - Automatically detect seasons/episodes
- **Music Collections** - Handle albums and compilations
- **Batch Operations** - Process multiple folders
- **Learning Mode** - Interactive tutorial

## 📋 Templates

Save time by creating reusable templates:
```bash
python run.py templates
```

Templates can store:
- Tracker lists
- Private/public settings
- Piece sizes
- Categories and tags
- Comments

## ⚙️ Configuration Editor

Edit settings without full setup:
```bash
python run.py config
```

Modify:
- qBittorrent connection
- Docker settings
- Path mappings
- Default directories
- Categories & tags
- Tracker URLs
- Default behaviors

## Tips for Best User Experience

1. **First Time?** Run `python run.py wizard` for guided setup
2. **Regular User?** Create templates for your common scenarios
3. **Multiple Torrents?** Use the wizard's TV/Music modes
4. **Quick Check?** Validate paths before creating large torrents
5. **Settings Changed?** Use `config` instead of re-running setup

## Requirements

- Python 3.8+
- qBittorrent with CLI tools (or API access)
- Docker (optional, for containerized qBittorrent)

## Troubleshooting

### Import Errors
If you get import errors, make sure you're in the correct directory:
```bash
cd /mnt/cache/scripts/mk_torrent
python run.py [command]
```

### "qbittorrent-cli not found"
The script will use qBittorrent's Web API instead. Make sure qBittorrent is running.

### Docker permission denied
Make sure your user has Docker permissions: `sudo usermod -aG docker $USER`

### Path mapping issues
Run `python run.py setup` to reconfigure Docker path mappings

## Alternative: Using qBittorrent Web API

If qbittorrent-cli is not available, the script can use the Web API directly.
Configure during setup with your qBittorrent Web UI credentials.

## License

MIT License - feel free to modify and distribute!
