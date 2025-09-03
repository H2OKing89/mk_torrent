# 👨‍💻 Development Guide

**Prerequisites**: Python 3.11+, Git, Basic Python packaging knowledge
**Development Approach**: Test-driven development with modern Python practices
**Code Style**: Black formatting, type hints, comprehensive documentation

---

## 🚀 **Quick Setup**

### **1. Clone and Setup Environment**
```bash
# Clone repository
git clone <repository-url>
cd mk_torrent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### **2. Verify Installation**
```bash
# Run tests to verify setup
python -m pytest tests/ -v

# Test application entry point
python scripts/run_new.py --help

# Test module execution
python -m mk_torrent --help
```

### **3. IDE Configuration**
```bash
# Set Python path for IDE
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# VS Code: Add to .vscode/settings.json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.analysis.extraPaths": ["src"]
}
```

---

## 🏗️ **Project Architecture**

### **Package Structure**
```
src/mk_torrent/
├── api/          # External service integrations
├── core/         # Essential business logic
├── features/     # Extended functionality
├── utils/        # Helper utilities
└── workflows/    # Multi-step processes
```

### **Dependency Guidelines**
- **Core modules**: Independent, no feature dependencies
- **Features**: Can use core, minimal feature interdependence
- **API**: External integrations, minimal internal dependencies
- **Utils**: Helper functions, used by all packages
- **Workflows**: Orchestrate other packages, no business logic

---

## 🧪 **Development Workflow**

### **Test-Driven Development**
```bash
# 1. Write failing test
def test_new_feature():
    assert new_feature() == expected_result

# 2. Run test (should fail)
python -m pytest tests/test_module.py::test_new_feature -v

# 3. Write minimal code to pass
def new_feature():
    return expected_result

# 4. Refactor while keeping tests green
# 5. Repeat cycle
```

### **Branch Strategy**
```bash
# Feature development
git checkout -b feature/descriptive-name
git commit -m "feat: add new functionality"

# Bug fixes
git checkout -b fix/issue-description
git commit -m "fix: resolve specific problem"

# Documentation
git checkout -b docs/section-name
git commit -m "docs: update development guide"
```

### **Code Quality Checks**
```bash
# Run all tests
python -m pytest tests/ -v

# Check test coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Type checking (if mypy installed)
mypy src/

# Code formatting (if black installed)
black src/ tests/
```

---

## 📝 **Coding Standards**

### **Code Style**
- **Formatting**: Black (line length 88)
- **Import organization**: isort
- **Docstrings**: Google/Sphinx style
- **Type hints**: Required for public APIs
- **Variable naming**: descriptive, snake_case

### **Example Module Structure**
```python
"""
Module for handling audiobook metadata processing.

This module provides functionality for extracting, validating, and
enhancing audiobook metadata from various sources.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

from ..core.base import BaseProcessor
from ..utils.validation import validate_metadata

logger = logging.getLogger(__name__)


class MetadataProcessor(BaseProcessor):
    """Process audiobook metadata with validation and enhancement.

    Args:
        config: Configuration dictionary
        validation_enabled: Whether to enable strict validation

    Example:
        >>> processor = MetadataProcessor(config)
        >>> metadata = processor.process(audiobook_files)
        >>> print(metadata['title'])
    """

    def __init__(
        self,
        config: Dict[str, Any],
        validation_enabled: bool = True
    ) -> None:
        super().__init__(config)
        self.validation_enabled = validation_enabled
        self._cache: Dict[str, Any] = {}

    def process(self, files: List[Path]) -> Dict[str, Any]:
        """Process files and extract metadata.

        Args:
            files: List of audiobook files to process

        Returns:
            Dictionary containing extracted metadata

        Raises:
            ValidationError: If validation fails and strict mode enabled
        """
        logger.info(f"Processing {len(files)} files")

        try:
            metadata = self._extract_metadata(files)

            if self.validation_enabled:
                validate_metadata(metadata)

            return metadata

        except Exception as e:
            logger.error(f"Failed to process metadata: {e}")
            raise
```

### **Testing Standards**
```python
"""
Tests for metadata processing functionality.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.mk_torrent.features.metadata_engine import MetadataProcessor


class TestMetadataProcessor:
    """Test MetadataProcessor functionality."""

    @pytest.fixture
    def processor(self):
        """Create processor instance for testing."""
        config = {"validation": True, "source": "audnexus"}
        return MetadataProcessor(config)

    @pytest.fixture
    def sample_files(self, tmp_path):
        """Create sample audiobook files."""
        files = []
        for i in range(3):
            file_path = tmp_path / f"chapter_{i}.mp3"
            file_path.touch()
            files.append(file_path)
        return files

    def test_process_basic_metadata(self, processor, sample_files):
        """Test basic metadata extraction works."""
        # Act
        result = processor.process(sample_files)

        # Assert
        assert isinstance(result, dict)
        assert 'title' in result
        assert len(result) > 0

    @patch('src.mk_torrent.features.metadata_engine.validate_metadata')
    def test_process_with_validation_disabled(self, mock_validate, processor, sample_files):
        """Test processing with validation disabled."""
        # Arrange
        processor.validation_enabled = False

        # Act
        result = processor.process(sample_files)

        # Assert
        mock_validate.assert_not_called()
        assert result is not None

    def test_process_empty_files_raises_error(self, processor):
        """Test processing empty file list raises appropriate error."""
        with pytest.raises(ValueError, match="No files provided"):
            processor.process([])
```

---

## 🔧 **Development Tools**

### **Essential Tools**
```bash
# Install development dependencies
pip install pytest pytest-cov mypy black isort

# Pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### **Useful Commands**
```bash
# Run specific test file
python -m pytest tests/test_metadata_engine.py -v

# Run tests with coverage
python -m pytest --cov=src --cov-report=html

# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/mk_torrent/
```

### **Debugging**
```bash
# Run with debugger
python -m pytest tests/ --pdb

# Verbose output
python -m pytest tests/ -v -s

# Stop on first failure
python -m pytest tests/ -x
```

---

## 🧩 **Adding New Features**

### **1. Plan the Feature**
- **Identify the appropriate package** (api, core, features, utils, workflows)
- **Define clear interfaces** and dependencies
- **Consider testing strategy** and mock requirements

### **2. Create Module Structure**
```bash
# Create new module file
touch src/mk_torrent/[package]/new_feature.py

# Create corresponding test file
touch tests/test_new_feature.py

# Update package __init__.py if needed
echo "from .new_feature import NewFeatureClass" >> src/mk_torrent/[package]/__init__.py
```

### **3. Implementation Process**
1. **Write failing tests** for the new functionality
2. **Implement minimum viable code** to pass tests
3. **Add error handling** and edge cases
4. **Update documentation** and docstrings
5. **Add integration tests** if needed

### **4. Example: Adding New API Integration**
```python
# File: src/mk_torrent/api/new_tracker.py
"""Integration with NewTracker API."""

from typing import Dict, Any
import requests
from ..core.secure_credentials import get_secure_api_key


class NewTrackerAPI:
    """Client for NewTracker API integration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("new_tracker_url", "https://api.newtracker.com")
        self.session = requests.Session()

    def authenticate(self) -> bool:
        """Authenticate with NewTracker API."""
        api_key = get_secure_api_key("new_tracker")
        if not api_key:
            return False

        headers = {"Authorization": f"Bearer {api_key}"}
        self.session.headers.update(headers)

        # Test authentication
        response = self.session.get(f"{self.base_url}/user")
        return response.status_code == 200
```

```python
# File: tests/test_new_tracker.py
"""Tests for NewTracker API integration."""

import pytest
from unittest.mock import Mock, patch
from src.mk_torrent.api.new_tracker import NewTrackerAPI


class TestNewTrackerAPI:
    """Test NewTrackerAPI functionality."""

    def test_initialization(self):
        """Test API client initialization."""
        config = {"new_tracker_url": "https://test.com"}
        api = NewTrackerAPI(config)

        assert api.config == config
        assert api.base_url == "https://test.com"

    @patch('src.mk_torrent.api.new_tracker.get_secure_api_key')
    @patch('requests.Session.get')
    def test_authenticate_success(self, mock_get, mock_get_key):
        """Test successful authentication."""
        # Arrange
        mock_get_key.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        api = NewTrackerAPI({})

        # Act
        result = api.authenticate()

        # Assert
        assert result is True
        mock_get.assert_called_once()
```

---

## 🐛 **Debugging Guide**

### **Common Issues**

#### **Import Errors**
```python
# Problem: ModuleNotFoundError
# Solution: Check import paths

# Wrong:
from api_qbittorrent import QBittorrentAPI

# Correct:
from mk_torrent.api.qbittorrent import QBittorrentAPI
# Or in tests:
from src.mk_torrent.api.qbittorrent import QBittorrentAPI
```

#### **Test Failures**
```bash
# Get detailed error info
python -m pytest tests/failing_test.py -v --tb=long

# Run single failing test
python -m pytest tests/test_file.py::TestClass::test_method -v

# Add debugging prints (then remove them!)
def test_something():
    result = function_under_test()
    print(f"DEBUG: result = {result}")  # Temporary debug
    assert result == expected
```

#### **Missing Dependencies**
```bash
# Check installed packages
pip list

# Install missing dependencies
pip install -r requirements.txt

# Check for version conflicts
pip check
```

### **Performance Debugging**
```python
import time
import cProfile

def test_performance():
    """Test function performance."""
    start_time = time.time()

    # Run function
    result = expensive_function()

    execution_time = time.time() - start_time
    print(f"Execution time: {execution_time:.2f} seconds")
    assert execution_time < 10.0  # Should complete in under 10 seconds

# Profile detailed performance
if __name__ == "__main__":
    cProfile.run("expensive_function()")
```

---

## 🚀 **Contributing Guidelines**

### **Before Submitting**
1. **All tests pass**: `python -m pytest tests/ -v`
2. **Code formatted**: `black src/ tests/`
3. **Type hints added**: For public APIs
4. **Documentation updated**: Docstrings and README if needed
5. **No breaking changes**: Or clearly documented

### **Pull Request Process**
1. **Create feature branch** from main
2. **Implement changes** with tests
3. **Update documentation** as needed
4. **Submit PR** with clear description
5. **Address review feedback**

### **Commit Message Format**
```bash
# Feature
git commit -m "feat: add RED tracker integration"

# Bug fix
git commit -m "fix: resolve metadata parsing error"

# Documentation
git commit -m "docs: update API reference"

# Tests
git commit -m "test: add integration tests for upload queue"

# Refactoring
git commit -m "refactor: simplify credential management"
```

---

## 📚 **Resources**

### **Internal Documentation**
- **[Project Structure](PROJECT_STRUCTURE.md)** - Architecture overview
- **[Testing Guide](../active/TESTING_GUIDE.md)** - Testing best practices
- **[API Reference](API_REFERENCE.md)** - Complete API documentation

### **External Resources**
- **[Python Packaging Guide](https://packaging.python.org/)** - Modern Python packaging
- **[pytest Documentation](https://docs.pytest.org/)** - Testing framework
- **[Type Hints (PEP 484)](https://peps.python.org/pep-0484/)** - Type annotations

---

**🎯 Ready to contribute? Start with the test suite to understand the codebase, then pick an area that interests you!**

**Questions?** Check existing code for patterns or ask for guidance.
