# 🧪 Testing Guide

**Test Framework**: pytest
**Coverage Tool**: pytest-cov
**Test Location**: `/tests/`
**Results**: `/test_results/`

---

## 🎯 **Current Test Status**

✅ **122/122 tests passing (100% success rate)**
📊 **18% overall code coverage**
🔧 **All critical modules fully tested**

updated: 2025-09-06T19:14:05-05:00
---

## 🚀 **Quick Start**

### **Run All Tests**

```bash
cd /mnt/cache/scripts/mk_torrent

# Basic test run
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

# Using test runner script
python test_runner.py run
```

### **Run Specific Test Modules**

```bash
# API tests only
python -m pytest tests/test_api_qbittorrent.py -v

# Metadata engine tests
python -m pytest tests/test_metadata_engine.py -v

# Security tests
python -m pytest tests/test_secure_credentials.py -v

# Queue management tests
python -m pytest tests/test_upload_queue.py -v
```

### **Run Single Test**

```bash
# Run one specific test
python -m pytest tests/test_metadata_engine.py::TestHTMLCleaner::test_clean_html_string_basic -v
```

---

## 📊 **Test Coverage by Module**

| Module | Coverage | Test Count | Status |
|--------|----------|------------|---------|
| **API/qBittorrent** | 74% | 35 tests | ✅ Excellent |
| **Core/SecureCredentials** | 91% | 35 tests | ✅ Excellent |
| **Core/UploadQueue** | 82% | 19 tests | ✅ Good |
| **Features/MetadataEngine** | 50% | 33 tests | 🟡 Needs improvement |
| **Utils/Async** | 0% | 0 tests | ❌ Needs tests |
| **CLI** | 0% | 0 tests | ❌ Needs tests |
| **Config** | 0% | 0 tests | ❌ Needs tests |

---

## 🧪 **Test Categories**

### **Unit Tests** (Primary focus)

- **Location**: All files in `/tests/`
- **Purpose**: Test individual functions and classes in isolation
- **Mocking**: Extensive use of `unittest.mock` and `pytest` fixtures
- **Coverage**: Core business logic and error handling

### **Integration Tests** (Subset)

- **Examples**: qBittorrent API integration, Audnexus API calls
- **Purpose**: Test module interactions and external dependencies
- **Approach**: Mock external services but test real integration code

### **End-to-End Tests** (Future)

- **Status**: Not yet implemented
- **Purpose**: Test complete workflows from CLI to final output
- **Scope**: Full audiobook processing pipeline

---

## 🔧 **Test Infrastructure**

### **Configuration Files**

- **`pyproject.toml`**: pytest and coverage configuration
- **`tests/conftest.py`**: Shared fixtures and test setup
- **`test_runner.py`**: Custom test runner with enhanced reporting

### **Fixtures & Mocking**

```python
# Common fixtures available in all tests
@pytest.fixture
def temp_dir():          # Temporary directory for file operations
def sample_metadata():   # Sample audiobook metadata
def mock_qbittorrent():  # Mocked qBittorrent client
def secure_manager():   # Secure credential manager instance
```

### **Test Utilities**

- **Mock factories** for common objects (files, API responses, etc.)
- **Assertion helpers** for complex data structures
- **Test data generators** for various scenarios

---

## 📝 **Writing New Tests**

### **Test File Structure**

```python
"""
Test module for [component_name]
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.mk_torrent.[module_path] import [ComponentClass]

class TestComponentClass:
    """Test [ComponentClass] functionality"""

    def test_basic_functionality(self):
        """Test basic operation works correctly"""
        # Arrange
        component = ComponentClass()

        # Act
        result = component.do_something()

        # Assert
        assert result is not None

    @patch('src.mk_torrent.[module].external_dependency')
    def test_with_mocking(self, mock_external):
        """Test with external dependencies mocked"""
        # Setup mock
        mock_external.return_value = "expected_value"

        # Test
        component = ComponentClass()
        result = component.method_using_external()

        # Verify
        assert result == "expected_value"
        mock_external.assert_called_once()
```

### **Naming Conventions**

- **Test files**: `test_[module_name].py`
- **Test classes**: `TestClassName`
- **Test methods**: `test_specific_behavior`
- **Fixtures**: `descriptive_fixture_name`

### **Best Practices**

- ✅ **Arrange-Act-Assert** pattern
- ✅ **Descriptive test names** that explain the scenario
- ✅ **Mock external dependencies** (APIs, file system, network)
- ✅ **Test both success and failure scenarios**
- ✅ **Use fixtures** for common setup/teardown
- ✅ **Assert specific behaviors** not just "no errors"

---

## 🐛 **Debugging Failed Tests**

### **Common Issues & Solutions**

#### **Import Errors**

```bash
# Error: ModuleNotFoundError
# Solution: Check import paths use src.mk_torrent.* format

# Wrong:
from api_qbittorrent import QBittorrentAPI

# Correct:
from src.mk_torrent.api.qbittorrent import QBittorrentAPI
```

#### **Mock Patch Errors**

```bash
# Error: AttributeError: module has no attribute 'function_name'
# Solution: Use full module path in @patch decorator

# Wrong:
@patch('module.function')

# Correct:
@patch('src.mk_torrent.module.function')
```

#### **Fixture Scope Issues**

```python
# Use appropriate fixture scope
@pytest.fixture(scope="function")  # Default, new instance per test
@pytest.fixture(scope="class")     # Shared within test class
@pytest.fixture(scope="session")   # Shared across entire test session
```

### **Debugging Commands**

```bash
# Run with detailed output
python -m pytest tests/ -v -s

# Stop on first failure
python -m pytest tests/ -x

# Show local variables on failure
python -m pytest tests/ --tb=long

# Run with pdb debugger
python -m pytest tests/ --pdb
```

---

## 📈 **Improving Test Coverage**

### **Priority Areas for New Tests**

1. **CLI Module** (0% coverage) - Command line interface testing
2. **Config Module** (0% coverage) - Configuration loading and validation
3. **Utils/Async** (0% coverage) - Async helper functions
4. **Workflows** (0% coverage) - Complete workflow testing
5. **Features** (50% coverage) - More metadata engine edge cases

### **Coverage Goals**

- **Immediate (2 weeks)**: 40% overall coverage
- **Short-term (1 month)**: 60% overall coverage
- **Long-term (3 months)**: 80% overall coverage

### **Coverage Analysis**

```bash
# Generate detailed coverage report
python -m pytest tests/ --cov=src --cov-report=html

# View HTML report
open test_results/coverage_html/index.html

# Find uncovered lines
python -m pytest tests/ --cov=src --cov-report=term-missing
```

---

## 🔄 **Continuous Testing**

### **Pre-commit Testing**

```bash
# Add to .git/hooks/pre-commit
#!/bin/bash
python -m pytest tests/ --maxfail=5 -q
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

### **Development Workflow**

```bash
# Test-driven development cycle
1. Write failing test
2. Run test to confirm it fails
3. Write minimum code to pass
4. Refactor while keeping tests green
5. Repeat
```

---

## 🎯 **Performance Testing**

### **Current Performance Tests**

- **Metadata processing** speed benchmarks
- **File I/O** operation timing
- **Memory usage** monitoring for large files

### **Adding Performance Tests**

```python
import time
import pytest

def test_metadata_processing_performance():
    """Ensure metadata processing completes within acceptable time"""
    start_time = time.time()

    # Run operation
    result = process_large_audiobook()

    execution_time = time.time() - start_time
    assert execution_time < 30.0  # Must complete within 30 seconds
```

---

**🎉 Happy testing! Remember: Good tests are the foundation of reliable software.**

**Questions?** Check the test files for examples or ask for help!
