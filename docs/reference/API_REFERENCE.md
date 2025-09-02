# 🔌 API Reference

**Complete technical reference for all public APIs and interfaces**

---

## 📋 **Table of Contents**

- [Core APIs](#-core-apis)
- [Feature APIs](#-feature-apis)  
- [Utility APIs](#-utility-apis)
- [Workflow APIs](#-workflow-apis)
- [External Integration APIs](#-external-integration-apis)
- [Configuration Reference](#-configuration-reference)
- [Error Handling](#-error-handling)

---

## 🎯 **Core APIs**

### **SecureCredentialManager**
*Location*: `src/mk_torrent/core/secure_credentials.py`

**Purpose**: Manage encrypted credentials with keyring integration

```python
from mk_torrent.core.secure_credentials import SecureCredentialManager

class SecureCredentialManager:
    """Secure credential storage and retrieval with encryption."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize credential manager.
        
        Args:
            config: Configuration dictionary containing:
                - encryption_key: Optional encryption key
                - keyring_enabled: Enable system keyring (default: True)
        """
    
    def store_credential(self, service: str, username: str, password: str) -> bool:
        """
        Store encrypted credential.
        
        Args:
            service: Service identifier (e.g., 'qbittorrent', 'red')
            username: Username for the service
            password: Password to encrypt and store
            
        Returns:
            bool: True if stored successfully
            
        Raises:
            CredentialError: If encryption or storage fails
        """
    
    def get_credential(self, service: str, username: str) -> Optional[str]:
        """
        Retrieve and decrypt credential.
        
        Args:
            service: Service identifier
            username: Username for the service
            
        Returns:
            Optional[str]: Decrypted password or None if not found
        """
    
    def delete_credential(self, service: str, username: str) -> bool:
        """Delete stored credential."""
    
    def list_services(self) -> List[str]:
        """List all stored service identifiers."""
```

**Helper Functions**:
```python
def get_secure_qbittorrent_password(username: str = "admin") -> Optional[str]:
    """Get qBittorrent password from secure storage."""

def get_secure_red_api_key(username: str = "default") -> Optional[str]:
    """Get RED API key from secure storage."""
```

### **BaseProcessor**
*Location*: `src/mk_torrent/core/base.py`

**Purpose**: Base class for all processing components

```python
from mk_torrent.core.base import BaseProcessor

class BaseProcessor(ABC):
    """Abstract base class for all processors."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize processor with configuration."""
        
    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        """Process input data (must be implemented by subclasses)."""
    
    def validate_config(self) -> bool:
        """Validate processor configuration."""
    
    def get_status(self) -> Dict[str, Any]:
        """Get current processor status."""
```

---

## 🎨 **Feature APIs**

### **MetadataEngine**
*Location*: `src/mk_torrent/features/metadata_engine.py`

**Purpose**: Extract and enhance audiobook metadata

```python
from mk_torrent.features.metadata_engine import MetadataEngine

class MetadataEngine(BaseProcessor):
    """Audiobook metadata extraction and enhancement."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize metadata engine.
        
        Args:
            config: Configuration dictionary containing:
                - audnexus_api_url: Audnexus API base URL
                - cache_enabled: Enable metadata caching
                - validation_strict: Enable strict validation
        """
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from audiobook file.
        
        Args:
            file_path: Path to audiobook file
            
        Returns:
            Dict containing:
                - title: Book title
                - author: Author name
                - narrator: Narrator name
                - duration: Total duration in seconds
                - chapters: List of chapter information
                - cover_art: Base64 encoded cover image
                
        Raises:
            MetadataError: If extraction fails
        """
    
    def enhance_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance metadata using external APIs.
        
        Args:
            metadata: Basic metadata dictionary
            
        Returns:
            Enhanced metadata with additional fields:
                - description: Book description
                - genre: Primary genre
                - publication_year: Year of publication
                - isbn: ISBN if available
        """
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """
        Validate metadata completeness.
        
        Returns:
            List of validation error messages (empty if valid)
        """
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats."""
```

### **TorrentCreator**
*Location*: `src/mk_torrent/core/torrent_creator.py`

**Purpose**: Create torrents with proper structure and metadata

```python
from mk_torrent.core.torrent_creator import TorrentCreator

class TorrentCreator(BaseProcessor):
    """Create .torrent files with optimized settings."""
    
    def create_torrent(
        self,
        source_path: Path,
        announce_urls: List[str],
        piece_size: Optional[int] = None,
        private: bool = True,
        comment: Optional[str] = None
    ) -> Path:
        """
        Create torrent file.
        
        Args:
            source_path: Path to file or directory to create torrent from
            announce_urls: List of tracker URLs
            piece_size: Piece size in bytes (auto-calculated if None)
            private: Whether torrent is private
            comment: Optional comment for torrent
            
        Returns:
            Path to created .torrent file
            
        Raises:
            TorrentCreationError: If creation fails
        """
    
    def calculate_optimal_piece_size(self, total_size: int) -> int:
        """Calculate optimal piece size for given total size."""
    
    def validate_torrent(self, torrent_path: Path) -> Dict[str, Any]:
        """Validate created torrent file."""
```

---

## 🛠️ **Utility APIs**

### **ValidationHelpers**
*Location*: `src/mk_torrent/utils/validation.py`

```python
from mk_torrent.utils.validation import (
    validate_audiobook_structure,
    validate_metadata_completeness,
    validate_file_integrity
)

def validate_audiobook_structure(directory: Path) -> List[str]:
    """
    Validate audiobook directory structure.
    
    Args:
        directory: Path to audiobook directory
        
    Returns:
        List of validation errors (empty if valid)
    """

def validate_metadata_completeness(
    metadata: Dict[str, Any], 
    required_fields: Optional[List[str]] = None
) -> List[str]:
    """Validate metadata has all required fields."""

def validate_file_integrity(file_path: Path) -> bool:
    """Check if file is accessible and not corrupted."""
```

### **FileHelpers**
*Location*: `src/mk_torrent/utils/file_helpers.py`

```python
from mk_torrent.utils.file_helpers import (
    get_audio_files,
    calculate_directory_size,
    sanitize_filename
)

def get_audio_files(directory: Path, recursive: bool = True) -> List[Path]:
    """Get all audio files from directory."""

def calculate_directory_size(directory: Path) -> int:
    """Calculate total size of directory in bytes."""

def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """Sanitize filename for cross-platform compatibility."""
```

---

## 🔄 **Workflow APIs**

### **AudiobookCompleteWorkflow**
*Location*: `src/mk_torrent/workflows/audiobook_complete.py`

**Purpose**: Complete audiobook processing workflow

```python
from mk_torrent.workflows.audiobook_complete import AudiobookCompleteWorkflow

class AudiobookCompleteWorkflow:
    """Complete audiobook processing and upload workflow."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize workflow.
        
        Args:
            config: Workflow configuration containing:
                - source_directory: Source audiobook directory
                - output_directory: Output directory for processed files
                - tracker_config: Tracker-specific configuration
                - qbittorrent_config: qBittorrent configuration
        """
    
    def execute(self) -> WorkflowResult:
        """
        Execute complete workflow.
        
        Returns:
            WorkflowResult containing:
                - success: Whether workflow completed successfully
                - torrent_path: Path to created torrent
                - metadata: Extracted metadata
                - errors: List of any errors encountered
        """
    
    def get_progress(self) -> WorkflowProgress:
        """Get current workflow progress."""
    
    def cancel(self) -> None:
        """Cancel running workflow."""
```

### **WorkflowResult**
```python
@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    success: bool
    torrent_path: Optional[Path]
    metadata: Dict[str, Any]
    errors: List[str]
    execution_time: float
    
@dataclass 
class WorkflowProgress:
    """Current workflow progress."""
    current_step: str
    progress_percent: float
    estimated_time_remaining: Optional[float]
```

---

## 🌐 **External Integration APIs**

### **QBittorrentAPI**
*Location*: `src/mk_torrent/api/qbittorrent.py`

```python
from mk_torrent.api.qbittorrent import QBittorrentAPI

class QBittorrentAPI:
    """qBittorrent Web API client."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize API client.
        
        Args:
            config: Configuration containing:
                - host: qBittorrent host (default: localhost)
                - port: qBittorrent port (default: 8080)
                - username: Login username
                - use_https: Whether to use HTTPS
        """
    
    def authenticate(self) -> bool:
        """Authenticate with qBittorrent."""
    
    def add_torrent(
        self,
        torrent_path: Path,
        save_path: Optional[Path] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Add torrent to qBittorrent.
        
        Returns:
            Torrent hash
        """
    
    def get_torrent_info(self, torrent_hash: str) -> Dict[str, Any]:
        """Get detailed torrent information."""
    
    def set_torrent_location(self, torrent_hash: str, location: Path) -> bool:
        """Set torrent download location."""
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check."""
```

### **REDIntegration** ⚠️ **DEPRECATED**
*Location*: ~~`src/mk_torrent/api/red_integration.py`~~ → **REPLACED BY** `src/mk_torrent/api/trackers/red.py`  
*Status*: **DEPRECATED as of Sep 2, 2025** - See RED_MODULES_REFACTOR.md  

**New Usage:**
```python
from mk_torrent.api.trackers import get_tracker_api

# Old way (deprecated)
# from mk_torrent.api.red_integration import REDIntegration

# New way (current)
red_api = get_tracker_api('red', api_key='your_key')
```

~~Old Documentation:~~
```python
from mk_torrent.api.red_integration import REDIntegration

class REDIntegration:
    """RED (Redacted) tracker API integration."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize RED API client."""
    
    def authenticate(self) -> bool:
        """Authenticate with RED API."""
    
    def search_existing(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for existing releases."""
    
    def prepare_upload(self, torrent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare upload data for RED."""
    
    def upload_torrent(self, upload_data: Dict[str, Any]) -> str:
        """Upload torrent to RED."""
```

---

## ⚙️ **Configuration Reference**

### **Main Configuration**
```python
config = {
    # Core settings
    "working_directory": "/path/to/working/dir",
    "output_directory": "/path/to/output",
    "log_level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    
    # Metadata settings
    "metadata": {
        "audnexus_api_url": "https://api.audnex.us",
        "cache_enabled": True,
        "cache_ttl": 86400,  # 24 hours
        "validation_strict": True
    },
    
    # Torrent creation
    "torrent": {
        "piece_size_auto": True,
        "private": True,
        "include_md5": False,
        "announce_urls": [
            "https://tracker1.example.com/announce",
            "https://tracker2.example.com/announce"
        ]
    },
    
    # qBittorrent integration
    "qbittorrent": {
        "host": "localhost",
        "port": 8080,
        "username": "admin",
        "use_https": False,
        "timeout": 30,
        "verify_ssl": True
    },
    
    # Security settings
    "security": {
        "encryption_enabled": True,
        "keyring_enabled": True,
        "secure_delete": True
    }
}
```

### **Environment Variables**
```bash
# Optional environment variables
MK_TORRENT_CONFIG_PATH=/path/to/config.json
MK_TORRENT_LOG_LEVEL=DEBUG
MK_TORRENT_WORKING_DIR=/tmp/mk_torrent
QBITTORRENT_PASSWORD=secret_password
RED_API_KEY=your_red_api_key
```

---

## 🚨 **Error Handling**

### **Exception Hierarchy**
```python
# Base exception
class MkTorrentError(Exception):
    """Base exception for mk_torrent package."""

# Specific exceptions
class MetadataError(MkTorrentError):
    """Metadata extraction/validation errors."""

class TorrentCreationError(MkTorrentError):
    """Torrent creation errors."""

class CredentialError(MkTorrentError):
    """Credential storage/retrieval errors."""

class APIError(MkTorrentError):
    """External API communication errors."""

class ValidationError(MkTorrentError):
    """Data validation errors."""

class WorkflowError(MkTorrentError):
    """Workflow execution errors."""
```

### **Error Response Format**
```python
@dataclass
class ErrorResponse:
    """Standardized error response."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
```

### **Error Handling Examples**
```python
from mk_torrent.core.exceptions import MetadataError

try:
    metadata = engine.extract_metadata(file_path)
except MetadataError as e:
    logger.error(f"Metadata extraction failed: {e}")
    # Handle specific metadata error
except MkTorrentError as e:
    logger.error(f"General mk_torrent error: {e}")
    # Handle any mk_torrent related error
except Exception as e:
    logger.critical(f"Unexpected error: {e}")
    # Handle unexpected errors
```

---

## 🔧 **Advanced Usage**

### **Custom Processors**
```python
from mk_torrent.core.base import BaseProcessor

class CustomProcessor(BaseProcessor):
    """Custom processor implementation."""
    
    def process(self, input_data: Any) -> Any:
        """Implement custom processing logic."""
        # Your custom logic here
        return processed_data
    
    def validate_config(self) -> bool:
        """Validate custom configuration."""
        required_keys = ["custom_setting_1", "custom_setting_2"]
        return all(key in self.config for key in required_keys)
```

### **Plugin Architecture** (Future)
```python
# Plugin interface (planned)
class PluginInterface(ABC):
    """Interface for mk_torrent plugins."""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin with configuration."""
    
    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process data through plugin."""
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup plugin resources."""
```

---

## 📝 **Usage Examples**

### **Basic Metadata Extraction**
```python
from mk_torrent.features.metadata_engine import MetadataEngine

# Initialize engine
config = {"audnexus_api_url": "https://api.audnex.us"}
engine = MetadataEngine(config)

# Extract metadata
metadata = engine.extract_metadata(Path("/path/to/audiobook.m4b"))
print(f"Title: {metadata['title']}")
print(f"Author: {metadata['author']}")
```

### **Create and Add Torrent**
```python
from mk_torrent.core.torrent_creator import TorrentCreator
from mk_torrent.api.qbittorrent import QBittorrentAPI

# Create torrent
creator = TorrentCreator(config)
torrent_path = creator.create_torrent(
    source_path=Path("/path/to/audiobook"),
    announce_urls=["https://tracker.example.com/announce"]
)

# Add to qBittorrent
qb_client = QBittorrentAPI(qb_config)
qb_client.authenticate()
torrent_hash = qb_client.add_torrent(torrent_path)
```

### **Complete Workflow**
```python
from mk_torrent.workflows.audiobook_complete import AudiobookCompleteWorkflow

# Configure workflow
config = {
    "source_directory": "/path/to/audiobooks",
    "output_directory": "/path/to/output",
    "tracker_config": {...},
    "qbittorrent_config": {...}
}

# Execute workflow
workflow = AudiobookCompleteWorkflow(config)
result = workflow.execute()

if result.success:
    print(f"Torrent created: {result.torrent_path}")
else:
    print(f"Errors: {result.errors}")
```

---

**📖 This reference covers all public APIs. For implementation details, see the [Development Guide](DEVELOPMENT_GUIDE.md).**
