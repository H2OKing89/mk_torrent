# 🎯 Interactive Torrent Creator

A user-friendly, interactive torrent creator for qBittorrent with Docker support.

## 🛡️ Security Status

[![Security: Enterprise](https://img.shields.io/badge/Security-Enterprise-green.svg)](https://github.com/your-repo/security)
[![Encryption: AES-256](https://img.shields.io/badge/Encryption-AES--256-blue.svg)](https://en.wikipedia.org/wiki/Advanced_Encryption_Standard)
[![Credentials: Protected](https://img.shields.io/badge/Credentials-Protected-red.svg)](https://github.com/your-repo/security)

**🔐 Enterprise-grade security with AES-256 encryption for all sensitive credentials**

---

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
- 🏥 **Health Monitoring** - System and qBittorrent health checks
- 🔐 **Enterprise Security** - AES-256 encrypted credential storage

## 🔒 Security

This application implements **enterprise-grade security** for handling sensitive credentials and private tracker information.

### Security Features

- **🔐 Encrypted Password Storage** - qBittorrent passwords are encrypted using AES-256
- **🛡️ Private Tracker Protection** - Passkeys stored securely, not in plain text
- **🔑 API Key Security** - RED and other tracker API keys encrypted with AES-256
- **🔑 Master Password Protection** - PBKDF2 key derivation with 100,000 iterations
- **📁 Secure File Permissions** - All credential files have 600 permissions (owner-only access)
- **🖥️ System Keyring Integration** - Uses OS credential storage when available

### How Credentials Are Protected

**Before Security Implementation:**
```json
{
  "qbit_password": "your_password_here",
  "qbit_username": "admin"
}
```
*❌ Password visible to anyone with file access*

**After Security Implementation:**
```json
{
  "qbit_username": "admin"
}
```
*✅ Password stored in encrypted AES-256 file*

**Tracker URLs:**
```
# Before: https://tracker.example.com/abc123def456/announce
# After:  https://tracker.example.com/announce.php  # SECURE_PASSKEY_STORED
```

**API Keys:**
```json
# Before: {"red_api_key": "your_api_key_here"}
# After:  API keys stored in encrypted AES-256 file, accessed via:
#         secure_manager.get_tracker_credential('RED', 'api_key')
```

### Secure Storage Architecture

```
~/.config/torrent_creator/
├── config.json          # ⚙️ Configuration (no sensitive data)
├── trackers.txt         # 📋 Tracker URLs with secure placeholders
├── master_key           # 🔑 Encrypted master key (600 perms)
├── salt                 # 🧂 PBKDF2 salt (600 perms)
└── secure_config.enc    # 🔒 AES-256 encrypted credentials (600 perms)
```

### Security Best Practices

1. **Strong Master Password** - Use 12+ characters with mixed case, numbers, and symbols
2. **File System Security** - Enable full disk encryption on your system
3. **Regular Backups** - Backup your secure credential files regularly
4. **Environment Variables** - Consider using environment variables for production deployments
5. **Access Control** - Limit file system access to trusted users only

### First-Time Setup Security

When you first run the application, you'll be prompted to set up secure storage:

```bash
python run.py setup
```

This will:
1. Create a master password for encryption
2. Set up secure credential storage
3. Migrate any existing plain text credentials
4. Configure proper file permissions

### Security Verification

Verify your security setup:

```bash
# Check file permissions
ls -la ~/.config/torrent_creator/

# Verify health checks work with secure credentials
python run.py health

# Check that no plain text passwords exist
grep -r "password\|passkey" ~/.config/torrent_creator/*.json
```


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

### Security Dependencies

The application uses enterprise-grade security libraries:
- **cryptography** - AES-256 encryption and PBKDF2 key derivation
- **keyring** - OS-level secure credential storage
- **bcrypt** - Additional password hashing security

These are automatically installed with `pip install -r requirements.txt`

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

Config files are stored in `~/.config/torrent_creator/` with **enterprise-grade security**:

### Secure Configuration Files
- `config.json` - Main configuration (no sensitive data)
- `trackers.txt` - Default tracker URLs with secure passkey placeholders
- `secure_config.enc` - **AES-256 encrypted** credentials (600 permissions)
- `master_key` - Encrypted master key for credential access
- `salt` - PBKDF2 salt for key derivation

### Security Features
- 🔒 **Zero Plain Text** - No passwords stored in readable format
- 🛡️ **AES-256 Encryption** - Military-grade encryption for credentials
- 🔑 **PBKDF2 Protection** - 100,000 iteration key derivation
- 📁 **Secure Permissions** - 600 permissions on all credential files
- 🖥️ **Keyring Integration** - OS credential storage when available

### Configuration Commands
```bash
# View current settings (safe - no sensitive data shown)
python run.py config --show

# Edit configuration securely
python run.py config

# Reset to defaults (preserves secure credentials)
python run.py config --reset
```

## Commands

### Core Commands
- `create` - Create torrent(s) interactively
- `wizard` - Guided wizard for common tasks
- `quick` - Quick torrent with defaults
- `batch` - Create multiple torrents
- `health` - System health checks

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

# Health checks
python run.py health                    # Quick check
python run.py health -c                 # Comprehensive
python run.py health -m                 # Monitor mode
python run.py health -m -d 3600        # Monitor for 1 hour

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

## 🏥 Health Checks

The application includes comprehensive health monitoring to ensure everything is working properly:

### Quick Health Check
```bash
# Quick essential checks (disk, qBittorrent, performance)
python run.py health
```

### Comprehensive Health Check
```bash
# Full system validation
python run.py health --comprehensive
# or
python run.py health -c
```

### Continuous Monitoring
```bash
# Monitor system for 5 minutes (default)
python run.py health --monitor

# Monitor for custom duration (seconds)
python run.py health --monitor --duration 600
```

### What Gets Checked

#### Quick Check (Default)
- **Disk Space** - Ensures sufficient space for torrent creation
- **qBittorrent** - API connectivity and basic status
- **Performance** - CPU and memory usage

#### Comprehensive Check
- **Disk Space** - All configured paths
- **Permissions** - Read/write access to critical directories
- **Dependencies** - Python packages and external tools
- **Network** - Connectivity to qBittorrent and trackers
- **Docker** - Container status (if using Docker mode)
- **qBittorrent** - Detailed API health and statistics
- **Performance** - System resource usage

#### Continuous Monitoring
- Real-time tracking of:
  - CPU and memory usage
  - Active torrents count
  - Transfer rates
  - Disk space changes

### Health Check Examples

```bash
# Run before batch operations
python run.py health
python run.py create --batch

# Diagnose connection issues
python run.py health -c

# Monitor during heavy operations
python run.py health --monitor --duration 1800  # 30 minutes

# Check specific components via Python
python -c "
from config import load_config
from health_checks import SystemHealthCheck
config = load_config()
checker = SystemHealthCheck(config)
checker.check_qbittorrent_health()
checker.check_disk_space()
checker.display_results()
"
```

## Tips for Best User Experience

1. **First Time?** Run `python run.py wizard` for guided setup
2. **Regular User?** Create templates for your common scenarios
3. **Multiple Torrents?** Use the wizard's TV/Music modes
4. **Quick Check?** Validate paths before creating large torrents
5. **Settings Changed?** Use `config` instead of re-running setup
6. **Before Big Jobs?** Run `health` to ensure system readiness
7. **Security Conscious?** Your credentials are AES-256 encrypted and secure
8. **Issues?** Use `health -c` for comprehensive diagnostics

### Security Tips
- **Strong Master Password**: Use 12+ characters for credential encryption
- **Regular Backups**: Backup your `~/.config/torrent_creator/` directory
- **File Permissions**: Keep credential files with 600 permissions
- **Access Control**: Limit system access to trusted users only

## Troubleshooting

### Security Issues

#### "No password found in secure storage"
```bash
# Re-run setup to configure secure credentials
python run.py setup

# Or manually configure qBittorrent connection
python run.py config
```

#### "Master password required"
The application needs your master password to access encrypted credentials:
```bash
# Run any command that needs credentials
python run.py health
# Enter master password when prompted
```

#### Verify Security Setup
```bash
# Check file permissions are secure
ls -la ~/.config/torrent_creator/

# Verify no plain text passwords
grep -r "password\|passkey" ~/.config/torrent_creator/*.json

# Test secure credential access
python run.py health
```

#### Reset Secure Storage
If you forget your master password:
```bash
# Remove secure storage files
rm ~/.config/torrent_creator/secure_config.enc
rm ~/.config/torrent_creator/master_key
rm ~/.config/torrent_creator/salt

# Re-run setup
python run.py setup
```

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

### System Issues
If torrent creation fails or is slow:
```bash
# Run comprehensive health check
python run.py health -c

# Check specific issues
python run.py health | grep -E "(Disk|qBittorrent|Performance)"
```

### Low Disk Space
The health check will warn about low disk space. Free up space in:
- Output directory (where .torrent files are saved)
- qBittorrent download directory
- `/tmp` (for temporary operations)

### High Resource Usage
If the system is slow:
```bash
# Monitor resource usage
python run.py health --monitor

# Consider reducing parallel operations
python run.py create --batch  # Will prompt for parallel vs sequential
```

## Alternative: Using qBittorrent Web API

If qbittorrent-cli is not available, the script can use the Web API directly.
Configure during setup with your qBittorrent Web UI credentials.

## License

MIT License - feel free to modify and distribute!
