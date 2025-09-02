# qBittorrent API Documentation 📚

> Comprehensive documentation for the `qbittorrent-api` Python library, covering all aspects of integrating with qBittorrent's Web API. These documents provide detailed guidance for building robust torrent management applications.

<p align="center">
  <a href="https://pypi.org/project/qbittorrent-api/"><img alt="qbittorrent-api" src="https://img.shields.io/pypi/v/qbittorrent-api.svg"></a>
  <img alt="qBittorrent Web API" src="https://img.shields.io/badge/qBittorrent%20Web%20API-2.11.4-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

## 📖 Overview

This directory contains detailed documentation for the `qbittorrent-api` Python library, which provides a complete interface to qBittorrent's Web API. The documentation is organized by functional area and usage patterns, making it easy to find exactly what you need for your torrent management application.

**Supported Versions:**
- **qBittorrent**: v5.1.2+ 
- **Web API**: v2.11.4+
- **Python**: 3.8+

---

## 📑 Documentation Files

### 🚀 **Getting Started**

#### [`qbittorrent-api.py.md`](./qbittorrent-api.py.md)
**📝 Overview & Quick Start Guide**
- Complete introduction to the `qbittorrent-api` Python package
- Installation instructions and environment setup
- Basic usage patterns and code examples
- Configuration options and performance tips
- Exception handling and async patterns
- **Start here** for new users

**Key Topics:**
- Installation via pip
- Basic client setup and connection
- Two API styles: method calls vs object namespaces
- Environment variables and credentials
- Production deployment tips

---

### 🔧 **Core Components**

#### [`qBittorrent_api_client.md`](./qBittorrent_api_client.md)
**🎛️ Client Configuration & Connection Management**
- Comprehensive `Client` class documentation
- Constructor options and parameters
- HTTP configuration (timeouts, proxies, headers)
- TLS/SSL certificate handling
- Session management and context managers
- Error handling patterns

**Key Topics:**
- Client initialization options
- Request/HTTPAdapter configuration
- Certificate verification and security
- Connection pooling and performance
- Reverse proxy support

#### [`qBittorrent_api_authentication.md`](./qBittorrent_api_authentication.md)
**🔐 Authentication & Session Management**
- Login/logout functionality
- Session validation and refresh
- Authentication error handling
- Security best practices
- Cookie management

**Key Topics:**
- `auth_log_in()` and `auth_log_out()` methods
- `is_logged_in` property usage
- Handling authentication failures
- Automatic session refresh
- Self-signed certificate handling

---

### 🎯 **Feature-Specific APIs**

#### [`qBittorrent_api_application.md`](./qBittorrent_api_application.md)
**⚙️ Application Control & System Management**
- qBittorrent application settings and preferences
- Version information and build details
- System shutdown and control
- Network interface management
- Directory operations and file system access
- Cookie management

**Key Topics:**
- `app_preferences()` and settings management
- `app_version()` and compatibility checking
- `app_shutdown()` safety procedures
- Network interface enumeration
- Host directory browsing

#### [`qBittorrent_api_create.md`](./qBittorrent_api_create.md)
**🏗️ Torrent Creation API (v5.0.0+)**
- Creating `.torrent` files from local content
- Task management and progress tracking
- Format selection (v1, v2, hybrid)
- Tracker and web seed configuration
- Automatic seeding setup

**Key Topics:**
- `torrentcreator_add_task()` parameters
- Task status polling and completion
- Torrent file retrieval
- Format options and compatibility
- Error handling and cleanup

---

## 🎯 **Quick Navigation by Use Case**

### **Setting Up a Client**
1. Start with [`qbittorrent-api.py.md`](./qbittorrent-api.py.md) for installation
2. Review [`qBittorrent_api_client.md`](./qBittorrent_api_client.md) for configuration
3. Check [`qBittorrent_api_authentication.md`](./qBittorrent_api_authentication.md) for login

### **Managing Application Settings**
→ [`qBittorrent_api_application.md`](./qBittorrent_api_application.md)

### **Creating Torrents**
→ [`qBittorrent_api_create.md`](./qBittorrent_api_create.md)

### **Production Deployment**
1. [`qBittorrent_api_client.md`](./qBittorrent_api_client.md) - HTTP configuration
2. [`qbittorrent-api.py.md`](./qbittorrent-api.py.md) - Performance and async patterns
3. [`qBittorrent_api_authentication.md`](./qBittorrent_api_authentication.md) - Security practices

---

## 🔗 **Common Code Patterns**

### **Basic Client Setup**
```python
from qbittorrentapi import Client

# Simple connection
client = Client(
    host="localhost:8080",
    username="admin", 
    password="adminadmin"
)

# Production-ready with timeouts and pooling
client = Client(
    host="https://qbt.example.com",
    username="admin",
    password="adminadmin",
    REQUESTS_ARGS={"timeout": (3.1, 30)},
    HTTPADAPTER_ARGS={"pool_connections": 10, "pool_maxsize": 10},
    VERIFY_WEBUI_CERTIFICATE=True
)
```

### **Context Manager Usage**
```python
with Client(host="localhost:8080", username="admin", password="adminadmin") as qbt:
    torrents = qbt.torrents_info()
    for t in torrents:
        print(f"{t.name}: {t.state}")
```

### **Error Handling**
```python
from qbittorrentapi import exceptions as qba_exc

try:
    client.auth_log_in()
    result = client.torrents_info()
except qba_exc.LoginFailed:
    print("Invalid credentials")
except qba_exc.APIConnectionError as e:
    print(f"Connection failed: {e}")
```

---

## 📊 **API Coverage Matrix**

| Feature Area | Documentation File | qBittorrent Version | Status |
|--------------|-------------------|-------------------|---------|
| **Client & Connection** | `qBittorrent_api_client.md` | All versions | ✅ Complete |
| **Authentication** | `qBittorrent_api_authentication.md` | All versions | ✅ Complete |
| **Application Control** | `qBittorrent_api_application.md` | All versions | ✅ Complete |
| **Torrent Creation** | `qBittorrent_api_create.md` | v5.0.0+ | ✅ Complete |

---

## 🚀 **Getting Started Checklist**

- [ ] Read [`qbittorrent-api.py.md`](./qbittorrent-api.py.md) for overview
- [ ] Install: `pip install qbittorrent-api`
- [ ] Enable qBittorrent Web UI (Tools → Preferences → Web UI)
- [ ] Configure client with [`qBittorrent_api_client.md`](./qBittorrent_api_client.md)
- [ ] Test connection with [`qBittorrent_api_authentication.md`](./qBittorrent_api_authentication.md)
- [ ] Explore feature-specific docs based on your needs

---

## 🔗 **External Resources**

- **PyPI Package**: [qbittorrent-api](https://pypi.org/project/qbittorrent-api/)
- **Official Docs**: [qbittorrent-api.readthedocs.io](https://qbittorrent-api.readthedocs.io/)
- **GitHub Repository**: [rmartin16/qbittorrent-api](https://github.com/rmartin16/qbittorrent-api)
- **qBittorrent Web API Wiki**: [Official qBittorrent Web API](https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1))

---

## 💡 **Tips for Success**

1. **Start Simple**: Use the basic examples before adding complexity
2. **Handle Errors**: Always wrap API calls in proper exception handling
3. **Use Context Managers**: Prevent session leaks with `with` statements
4. **Check Versions**: Verify qBittorrent version compatibility for newer features
5. **Read the Docs**: Each file contains detailed examples and best practices

---

*This documentation is maintained as part of the Easy Torrent Creator project and reflects the latest qBittorrent API capabilities as of 2025.*
