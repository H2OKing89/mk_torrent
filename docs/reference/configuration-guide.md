# 🔧 Configuration Guide

**Complete configuration reference for mk_torrent**

---

## 📋 **Table of Contents**

- [Quick Start Configuration](#-quick-start-configuration)
- [Configuration File Structure](#-configuration-file-structure)
- [Environment Variables](#-environment-variables)
- [Security Configuration](#-security-configuration)
- [Advanced Settings](#-advanced-settings)
- [Troubleshooting](#-troubleshooting)

updated: 2025-09-07T04:23:39-05:00
---

## 🚀 **Quick Start Configuration**

### **Minimal Configuration**

Create `~/.config/mk_torrent/config.json`:

```json
{
  "working_directory": "/tmp/mk_torrent",
  "output_directory": "~/torrents",
  "qbittorrent": {
    "host": "localhost",
    "port": 8080,
    "username": "admin"
  },
  "metadata": {
    "audnexus_api_url": "https://api.audnex.us"
  }
}
```

### **First-Time Setup**

```bash
# 1. Create configuration directory
mkdir -p ~/.config/mk_torrent

# 2. Create basic config file
cat > ~/.config/mk_torrent/config.json << 'EOF'
{
  "working_directory": "/tmp/mk_torrent",
  "output_directory": "~/torrents",
  "log_level": "INFO"
}
EOF

# 3. Set up credentials (interactive)
python -c "
from mk_torrent.core.secure_credentials import setup_credentials
setup_credentials()
"

# 4. Test configuration
python -m mk_torrent --config-test
```

---

## 📁 **Configuration File Structure**

### **Complete Configuration Schema**

```json
{
  "version": "1.0",
  "working_directory": "/tmp/mk_torrent",
  "output_directory": "~/torrents",
  "log_level": "INFO",
  "log_file": "~/logs/mk_torrent.log",

  "metadata": {
    "audnexus_api_url": "https://api.audnex.us",
    "cache_enabled": true,
    "cache_directory": "~/.cache/mk_torrent/metadata",
    "cache_ttl": 86400,
    "validation_strict": true,
    "auto_enhance": true,
    "required_fields": [
      "title",
      "author",
      "narrator",
      "duration"
    ]
  },

  "torrent": {
    "piece_size_auto": true,
    "piece_size_manual": null,
    "private": true,
    "include_md5": false,
    "source": "RED",
    "announce_urls": [
      "https://flacsfor.me/announce"
    ],
    "comment_template": "Audiobook: {title} by {author}",
    "created_by": "mk_torrent"
  },

  "qbittorrent": {
    "enabled": true,
    "host": "localhost",
    "port": 8080,
    "username": "admin",
    "use_https": false,
    "timeout": 30,
    "verify_ssl": true,
    "auto_add": true,
    "default_category": "audiobooks",
    "default_tags": ["audiobook", "automated"],
    "pause_after_add": false
  },

  "red": {
    "enabled": false,
    "api_url": "https://redacted.ch",
    "upload_enabled": false,
    "auto_search_duplicates": true,
    "format": "24bit Lossless",
    "media": "WEB",
    "description_template": "High-quality audiobook rip"
  },

  "security": {
    "encryption_enabled": true,
    "keyring_enabled": true,
    "secure_delete": true,
    "credential_timeout": 3600,
    "auto_logout": true
  },

  "validation": {
    "structure_check": true,
    "file_integrity": true,
    "metadata_completeness": true,
    "audio_format_validation": true,
    "minimum_duration": 300,
    "maximum_file_size": "10GB"
  },

  "processing": {
    "parallel_processing": true,
    "max_workers": 4,
    "memory_limit": "2GB",
    "temp_cleanup": true,
    "progress_updates": true
  }
}
```

### **Configuration File Locations**

Files are checked in this order:

1. `./mk_torrent.json` (current directory)
2. `~/.config/mk_torrent/config.json`
3. `~/.mk_torrent.json`
4. `/etc/mk_torrent/config.json`

```bash
# Override default config location
export MK_TORRENT_CONFIG_PATH="/path/to/custom/config.json"
```

---

## 🌍 **Environment Variables**

### **General Settings**

```bash
# Configuration
export MK_TORRENT_CONFIG_PATH="/path/to/config.json"
export MK_TORRENT_LOG_LEVEL="DEBUG"
export MK_TORRENT_WORKING_DIR="/tmp/mk_torrent"
export MK_TORRENT_OUTPUT_DIR="~/torrents"

# Credentials (alternative to secure storage)
export QBITTORRENT_PASSWORD="your_password"
export RED_API_KEY="your_api_key"

# Feature toggles
export MK_TORRENT_CACHE_ENABLED="true"
export MK_TORRENT_VALIDATION_STRICT="false"
export MK_TORRENT_AUTO_ADD_QBITTORRENT="true"
```

### **Development Settings**

```bash
# Development mode
export MK_TORRENT_DEV_MODE="true"
export MK_TORRENT_DEBUG="true"
export MK_TORRENT_MOCK_APIS="true"

# Testing
export MK_TORRENT_TEST_DATA_DIR="/path/to/test/data"
export MK_TORRENT_TEST_CONFIG="/path/to/test/config.json"
```

---

## 🔒 **Security Configuration**

### **Credential Management**

```python
# Set up secure credentials
from mk_torrent.core.secure_credentials import SecureCredentialManager

# Initialize manager
manager = SecureCredentialManager(config)

# Store qBittorrent password
manager.store_credential("qbittorrent", "admin", "your_password")

# Store RED API key
manager.store_credential("red", "default", "your_api_key")

# Test retrieval
password = manager.get_credential("qbittorrent", "admin")
```

### **Encryption Settings**

```json
{
  "security": {
    "encryption_enabled": true,
    "encryption_algorithm": "AES-256",
    "key_derivation": "PBKDF2",
    "iterations": 100000,
    "keyring_enabled": true,
    "keyring_service": "mk_torrent",
    "secure_delete": true,
    "auto_lock_timeout": 3600
  }
}
```

### **System Keyring Integration**

```bash
# Linux (GNOME Keyring)
sudo apt install python3-keyring

# macOS (Keychain) - Built-in support

# Windows (Windows Credential Manager) - Built-in support

# Test keyring access
python -c "import keyring; print(keyring.get_keyring())"
```

---

## ⚙️ **Advanced Settings**

### **Performance Tuning**

```json
{
  "processing": {
    "parallel_processing": true,
    "max_workers": 8,
    "memory_limit": "4GB",
    "io_buffer_size": "64KB",
    "chunk_size": "1MB",
    "compress_temp_files": false,
    "use_memory_mapping": true
  },

  "caching": {
    "metadata_cache_size": "100MB",
    "api_response_cache": true,
    "cache_compression": true,
    "cache_encryption": false
  }
}
```

### **Network Configuration**

```json
{
  "network": {
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 1.0,
    "user_agent": "mk_torrent/1.0",
    "max_connections": 10,
    "connection_pool_size": 5,
    "verify_ssl": true,
    "proxy": {
      "enabled": false,
      "http": "http://proxy.example.com:8080",
      "https": "https://proxy.example.com:8080"
    }
  }
}
```

### **Logging Configuration**

```json
{
  "logging": {
    "level": "INFO",
    "file": "~/logs/mk_torrent.log",
    "max_size": "50MB",
    "backup_count": 5,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "console_output": true,
    "rich_formatting": true,
    "log_api_calls": false,
    "log_sensitive_data": false
  }
}
```

---

## 🎯 **Application-Specific Settings**

### **qBittorrent Configuration**

```json
{
  "qbittorrent": {
    "connection": {
      "host": "192.168.1.100",
      "port": 8080,
      "username": "admin",
      "use_https": true,
      "verify_ssl": false,
      "timeout": 30
    },

    "behavior": {
      "auto_add": true,
      "pause_after_add": false,
      "skip_hash_check": false,
      "sequential_download": false,
      "first_last_piece_priority": false
    },

    "organization": {
      "default_category": "audiobooks",
      "category_by_genre": true,
      "default_tags": ["audiobook", "automated"],
      "tag_by_source": true,
      "save_path": "/downloads/audiobooks"
    },

    "health_check": {
      "enabled": true,
      "check_connection": true,
      "check_free_space": true,
      "min_free_space": "5GB",
      "check_version": true
    }
  }
}
```

### **RED Tracker Configuration**

```json
{
  "red": {
    "api": {
      "base_url": "https://redacted.ch",
      "rate_limit": 5,
      "rate_limit_window": 10,
      "retry_on_rate_limit": true
    },

    "upload": {
      "enabled": false,
      "auto_upload": false,
      "format": "24bit Lossless",
      "media": "WEB",
      "description_template": "files/red_description_template.txt",
      "tags": ["audiobook"],
      "scene": false
    },

    "search": {
      "auto_check_duplicates": true,
      "similarity_threshold": 0.9,
      "check_artist": true,
      "check_title": true,
      "check_year": false
    }
  }
}
```

### **Metadata Engine Configuration**

```json
{
  "metadata": {
    "sources": {
      "audnexus": {
        "enabled": true,
        "api_url": "https://api.audnex.us",
        "timeout": 30,
        "cache_responses": true
      },
      "local_files": {
        "enabled": true,
        "priority": 1,
        "formats": ["m4b", "mp3", "flac"]
      }
    },

    "enhancement": {
      "auto_enhance": true,
      "fetch_cover_art": true,
      "sanitize_html": true,
      "normalize_fields": true,
      "validate_isbn": true
    },

    "validation": {
      "required_fields": [
        "title",
        "author",
        "narrator",
        "duration"
      ],
      "optional_fields": [
        "description",
        "genre",
        "publication_year",
        "isbn"
      ],
      "strict_mode": false
    }
  }
}
```

---

## 🔧 **Configuration Templates**

### **Home User Template**

```json
{
  "working_directory": "~/mk_torrent/work",
  "output_directory": "~/torrents",
  "log_level": "INFO",

  "qbittorrent": {
    "host": "localhost",
    "port": 8080,
    "username": "admin",
    "auto_add": true,
    "default_category": "audiobooks"
  },

  "torrent": {
    "private": true,
    "announce_urls": ["https://your-tracker.com/announce"]
  },

  "security": {
    "encryption_enabled": true,
    "keyring_enabled": true
  }
}
```

### **Headless Server Template**

```json
{
  "working_directory": "/var/lib/mk_torrent/work",
  "output_directory": "/var/lib/mk_torrent/output",
  "log_level": "WARNING",
  "log_file": "/var/log/mk_torrent.log",

  "qbittorrent": {
    "host": "127.0.0.1",
    "port": 8080,
    "username": "mk_torrent_bot",
    "auto_add": true,
    "pause_after_add": true
  },

  "processing": {
    "parallel_processing": true,
    "max_workers": 2,
    "memory_limit": "1GB"
  },

  "security": {
    "encryption_enabled": true,
    "keyring_enabled": false,
    "auto_logout": true
  }
}
```

### **Development Template**

```json
{
  "working_directory": "./dev_work",
  "output_directory": "./dev_output",
  "log_level": "DEBUG",

  "qbittorrent": {
    "enabled": false
  },

  "metadata": {
    "cache_enabled": false,
    "validation_strict": false
  },

  "red": {
    "enabled": false
  },

  "validation": {
    "structure_check": false,
    "file_integrity": false
  }
}
```

---

## 🚨 **Troubleshooting**

### **Common Configuration Issues**

#### **Configuration Not Found**

```bash
# Error: Configuration file not found
# Solution: Create default config
mkdir -p ~/.config/mk_torrent
python -m mk_torrent --create-config
```

#### **Invalid JSON Syntax**

```bash
# Error: JSON decode error
# Solution: Validate JSON syntax
python -m json.tool ~/.config/mk_torrent/config.json
```

#### **Permission Errors**

```bash
# Error: Permission denied
# Solution: Fix permissions
chmod 600 ~/.config/mk_torrent/config.json
chmod 700 ~/.config/mk_torrent/
```

#### **Credential Issues**

```python
# Error: Credential not found
# Solution: Reset credentials
from mk_torrent.core.secure_credentials import SecureCredentialManager

manager = SecureCredentialManager({})
manager.delete_credential("qbittorrent", "admin")
manager.store_credential("qbittorrent", "admin", "new_password")
```

### **Configuration Validation**

```bash
# Test complete configuration
python -m mk_torrent --config-test

# Test specific component
python -m mk_torrent --test-qbittorrent
python -m mk_torrent --test-metadata
python -m mk_torrent --test-credentials

# Debug configuration loading
python -c "
from mk_torrent.core.config import load_config
config = load_config(debug=True)
print('Config loaded successfully')
"
```

### **Environment Variable Debugging**

```bash
# Show all mk_torrent environment variables
env | grep MK_TORRENT

# Test environment override
MK_TORRENT_LOG_LEVEL=DEBUG python -m mk_torrent --version

# Clear environment variables
unset $(env | grep MK_TORRENT | cut -d= -f1)
```

---

## 📝 **Configuration Best Practices**

### **Security Best Practices**

1. **Use secure credential storage** instead of plain text passwords
2. **Enable encryption** for sensitive data
3. **Set appropriate file permissions** (600 for config files)
4. **Use environment variables** for temporary overrides only
5. **Regular credential rotation** for long-running setups

### **Performance Best Practices**

1. **Enable caching** for metadata and API responses
2. **Tune worker count** based on CPU cores
3. **Set memory limits** to prevent system overload
4. **Use SSD storage** for working directory
5. **Monitor disk space** in output directory

### **Reliability Best Practices**

1. **Enable validation** to catch errors early
2. **Configure retry logic** for network operations
3. **Set up comprehensive logging** for troubleshooting
4. **Regular backup** of configuration and credentials
5. **Test configuration** after changes

---

**🔧 For specific configuration examples, see the [examples](../examples/) directory.**
