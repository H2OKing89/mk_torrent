#!/usr/bin/env python3
"""Pytest configuration and shared fixtures for metadata testing"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import real data fixtures
from tests.utils.real_data_helpers import real_three_source_metadata


@pytest.fixture(scope="session")
def temp_workspace():
    """Create a temporary workspace directory for the entire test session"""
    temp_path = Path(tempfile.mkdtemp(prefix="metadata_test_"))
    yield temp_path

    # Cleanup after session
    import shutil

    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for individual tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path

    # Cleanup
    import shutil

    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_audio_file(temp_dir):
    """Create a mock audio file for testing"""
    audio_file = temp_dir / "test_audio.flac"
    audio_file.write_text("mock audio content")
    return audio_file


@pytest.fixture
def mock_m4b_file(temp_dir):
    """Create a mock M4B audiobook file"""
    m4b_file = temp_dir / "test_audiobook.m4b"
    m4b_file.write_text("mock m4b content")
    return m4b_file


@pytest.fixture
def sample_audiobook_metadata():
    """Sample audiobook metadata for testing"""
    return {
        "asin": "B0123456789",
        "title": "Test Audiobook",
        "subtitle": "A Test Subtitle",
        "authors": ["Test Author"],
        "narrators": ["Test Narrator"],
        "publisherName": "Test Publisher",
        "releaseDate": "2023-01-01T00:00:00.000Z",
        "runtimeLengthMin": 360,
        "genres": [{"name": "Fiction", "type": "genre"}],
        "summary": "This is a test audiobook summary.",
        "rating": 4.5,
        "isbn": "978-0123456789",
    }


@pytest.fixture
def mock_mutagen_file():
    """Mock mutagen File object"""
    mock_file = MagicMock()
    mock_file.info.length = 300.5
    mock_file.info.bitrate = 1411000
    mock_file.info.sample_rate = 44100
    mock_file.info.channels = 2
    mock_file.info.bits_per_sample = 16

    # Mock tag access
    mock_file.get.side_effect = lambda key, default=None: {
        "TITLE": "Test Title",
        "ARTIST": "Test Artist",
        "ALBUM": "Test Album",
        "DATE": "2023",
        "GENRE": "Rock",
    }.get(key, default)

    return mock_file


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for API testing"""

    def _mock_get(url, **kwargs):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None

        if "audnex.us" in url:
            mock_response.json.return_value = {
                "asin": "B0123456789",
                "title": "Mock Book Title",
                "authors": [{"name": "Mock Author"}],
                "summary": "Mock summary",
            }
        else:
            mock_response.json.return_value = {}

        return mock_response

    return _mock_get


@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock external dependencies that might not be available in test environment"""
    with pytest.MonkeyPatch().context() as m:
        # Mock optional dependencies
        m.setattr("src.mk_torrent.features.metadata_engine.NH3_AVAILABLE", True)
        m.setattr("src.mk_torrent.features.metadata_engine.MUTAGEN_AVAILABLE", True)
        m.setattr(
            "src.mk_torrent.features.metadata_engine.MUSICBRAINZ_AVAILABLE", False
        )
        yield


# Custom markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "metadata: marks tests related to metadata processing"
    )
    config.addinivalue_line("markers", "health: marks tests related to health checks")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "slow: marks tests as slow")


# Test utilities
class MetadataTestUtils:
    """Utility functions for metadata testing"""

    @staticmethod
    def create_mock_audio_file(path: Path, format_type: str = "FLAC"):
        """Create a mock audio file with metadata"""
        path.write_text(f"mock {format_type} content")
        return path

    @staticmethod
    def create_test_directory_with_files(base_path: Path, files_config: dict):
        """Create a test directory with specified files"""
        for filename, content in files_config.items():
            file_path = base_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, str):
                file_path.write_text(content)
            else:
                file_path.write_bytes(content)
        return base_path

    @staticmethod
    def assert_metadata_contains_required_fields(metadata: dict):
        """Assert that metadata contains all required fields"""
        required_fields = ["title", "artist", "album"]
        for field in required_fields:
            assert field in metadata, f"Missing required field: {field}"

    @staticmethod
    def assert_valid_audnexus_response(response: dict):
        """Assert that a response looks like a valid Audnexus API response"""
        assert "asin" in response
        assert "title" in response
        assert isinstance(response.get("authors", []), list)


# Make utilities available as fixture
@pytest.fixture
def test_utils():
    """Provide test utilities"""
    return MetadataTestUtils()


@pytest.fixture
def engine():
    """Create a MetadataEngine instance for testing"""
    try:
        from src.mk_torrent.features.metadata_engine import MetadataEngine

        return MetadataEngine()
    except ImportError:
        pytest.skip("MetadataEngine not available")


# Custom pytest hooks for better reporting
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Add custom reporting for metadata tests"""
    outcome = yield
    report = outcome.get_result()

    if "metadata" in str(item.keywords):
        if report.when == "call" and report.failed:
            # Add metadata-specific failure information
            report.nodeid = f"[METADATA] {report.nodeid}"
