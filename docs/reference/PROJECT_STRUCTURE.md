# 🏗️ Project Structure Reference

**Package Layout**: src/ (modern Python packaging standard)  
**Organization**: Domain-driven module structure  
**Status**: ✅ Fully implemented and tested

---

## 📁 **Current Structure**

```
mk_torrent/                    # 🎯 Clean, professional project root
├── 📄 LICENSE                # MIT License
├── 📄 README.md              # Project overview and quick start  
├── 📄 pyproject.toml         # Modern Python project configuration
├── 📄 requirements.txt       # Python dependencies
├── 📄 test_runner.py         # Test management script
├── 📁 archive/               # 🗄️ Legacy code backup (historical)
├── 📁 docs/                  # 📚 Organized documentation
│   ├── README.md            # Documentation index
│   ├── 📁 active/           # Current development docs
│   ├── 📁 archive/          # Completed/historical docs
│   └── 📁 reference/        # Stable reference materials
├── 📁 examples/             # 💡 Example usage files
├── 📁 scripts/              # 🔧 Utility scripts
│   ├── run_new.py          # ✅ Main entry point (working!)
│   ├── run.py              # Legacy entry point  
│   └── test_metadata.py    # Metadata testing tools
├── 📁 src/mk_torrent/       # 🐍 Main source code package
│   ├── __init__.py         # Package initialization
│   ├── __main__.py         # Module execution entry point  
│   ├── cli.py              # Command line interface
│   ├── config.py           # Configuration management
│   ├── 📁 api/             # External service integrations
│   ├── 📁 core/            # Essential application logic
│   ├── 📁 features/        # Extended functionality
│   ├── 📁 utils/           # Helper utilities
│   └── 📁 workflows/       # Multi-step processes
├── 📁 tests/               # 🧪 Comprehensive test suite
├── 📁 test_results/        # 📊 Test output and reports
└── 📁 htmlcov/             # 📈 Coverage reports
```

---

## 🎯 **Package Organization**

### 📦 **Main Package** (`src/mk_torrent/`)
The core application package following modern Python packaging standards.

#### **Entry Points**
- `__init__.py` - Package initialization and version info
- `__main__.py` - Entry point for `python -m mk_torrent`
- `cli.py` - Main command line interface and argument parsing
- `config.py` - Configuration loading, validation, and management

### 🔌 **API Package** (`src/mk_torrent/api/`)
External service integrations and client libraries.

```
api/
├── __init__.py
├── qbittorrent.py        # qBittorrent Web API client
├── red_integration.py    # RED tracker integration  
└── tracker_upload.py     # Generic tracker upload interface
```

**Purpose**: Isolate external dependencies and provide clean interfaces to third-party services.

### ⚙️ **Core Package** (`src/mk_torrent/core/`)
Essential application logic and foundational components.

```
core/
├── __init__.py
├── torrent_creator.py    # Torrent file creation and validation
├── health_checks.py      # System health monitoring
├── secure_credentials.py # Credential encryption and storage
└── upload_queue.py       # Upload job queue management
```

**Purpose**: Core business logic that other modules depend on.

### 🎯 **Features Package** (`src/mk_torrent/features/`)
Extended functionality and specialized processing modules.

```
features/
├── __init__.py
├── metadata_engine.py        # Audiobook metadata processing
├── validator.py              # File and path validation
├── cross_seed.py            # Cross-seeding functionality
├── red_uploader.py          # RED-specific upload logic
├── templates.py             # Template management
├── check_metadata_health.py # Metadata validation
└── database.py              # Data persistence
```

**Purpose**: Specialized functionality that extends core capabilities.

### 🛠️ **Utils Package** (`src/mk_torrent/utils/`)
Helper functions and utility modules.

```
utils/
├── __init__.py
├── async_helpers.py          # Async operation utilities
├── red_api_parser.py        # RED API documentation parsing
├── red_compliance_rename.py # RED file naming compliance
└── red_path_compliance.py   # RED directory structure compliance
```

**Purpose**: Reusable utility functions that support other modules.

### 🔄 **Workflows Package** (`src/mk_torrent/workflows/`)
Automated processes and multi-step operations.

```
workflows/
├── __init__.py
├── wizard.py               # Interactive setup wizard
└── audiobook_complete.py   # Complete audiobook processing workflow
```

**Purpose**: Orchestrate multiple modules into complete user workflows.

---

## 🎯 **Design Principles**

### ✅ **Domain-Driven Organization**
- **Related functionality grouped together** in logical packages
- **Clear separation of concerns** between packages
- **Dependencies flow inward** (features → core, utils → everywhere)

### ✅ **Modern Python Standards**
- **src/ layout** prevents accidental imports during development
- **Package initialization** with proper `__init__.py` files
- **Entry points** defined in `pyproject.toml`
- **Namespace packages** support for future extensions

### ✅ **Scalability & Maintenance**
- **Easy to add new modules** in appropriate packages
- **Clear module responsibilities** reduce coupling
- **Consistent naming conventions** improve discoverability
- **Self-documenting structure** helps new developers

---

## 🔄 **Import Patterns**

### **Internal Imports**
```python
# Within same package
from .module_name import ClassName

# Cross-package (relative)
from ..core.torrent_creator import TorrentCreator
from ..api.qbittorrent import QBittorrentAPI

# Cross-package (absolute) 
from mk_torrent.features.metadata_engine import MetadataEngine
```

### **External Imports**
```python
# External packages always use absolute imports
from mk_torrent.core.torrent_creator import TorrentCreator
from mk_torrent.api.qbittorrent import QBittorrentAPI
```

### **Testing Imports**
```python
# Tests always use absolute imports to test installed package
from src.mk_torrent.core.torrent_creator import TorrentCreator
```

---

## 📊 **Module Dependencies**

### **Dependency Flow**
```
CLI/Config (Entry Points)
    ↓
Workflows (Orchestration)
    ↓
Features (Specialized Logic)
    ↓
Core (Essential Logic)
    ↓
API & Utils (External/Helpers)
```

### **Clean Architecture**
- **No circular dependencies** between packages
- **Core modules are independent** of features
- **Features can depend on core** but not each other directly
- **Workflows orchestrate features** without tight coupling

---

## 🚀 **Usage Examples**

### **Running the Application**
```bash
# Using entry script (recommended)
python scripts/run_new.py --help

# Using module execution
python -m mk_torrent --help

# After pip install -e .
mk-torrent --help
```

### **Importing for Development**
```python
# Import specific classes
from mk_torrent.core.torrent_creator import TorrentCreator
from mk_torrent.api.qbittorrent import QBittorrentAPI

# Import for extension
from mk_torrent.features.metadata_engine import MetadataEngine
from mk_torrent.core.upload_queue import UploadJob, UploadQueue
```

### **Package Installation**
```bash
# Development installation (editable)
pip install -e .

# Production installation (if published)
pip install mk-torrent
```

---

## 📈 **Evolution & Maintenance**

### **Adding New Modules**
1. **Identify appropriate package** based on module purpose
2. **Create module file** with clear, focused responsibility
3. **Update package `__init__.py`** if module should be exported
4. **Add comprehensive tests** in corresponding test file
5. **Update documentation** with new functionality

### **Refactoring Guidelines**
- **Keep package boundaries clean** - don't create circular dependencies
- **Move related functionality together** when patterns emerge
- **Extract common patterns** into utils when appropriate
- **Maintain backward compatibility** in public interfaces

### **Future Extensibility**
- **Plugin architecture** can be added in features/
- **Additional trackers** can be added in api/
- **New workflows** can be added in workflows/
- **Specialized utilities** can be added in utils/

---

**🎯 This structure provides a solid foundation for maintainable, scalable code that follows Python best practices!**
