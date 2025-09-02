#!/usr/bin/env python3
"""Comprehensive tests for metadata processing engine"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime
import json

from src.mk_torrent.features.metadata_engine import (
    MetadataEngine,
    HTMLCleaner,
    FormatDetector,
    AudnexusAPI,
    ImageURLFinder,
    TagNormalizer,
    AlbumArtwork,
    AudioFormat
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing"""
    return {
        "title": "Test Album",
        "artist": "Test Artist",
        "album": "Test Album",
        "year": "2023",
        "genre": "Rock",
        "format": "FLAC",
        "encoding": "Lossless",
        "bitrate": 1411000,
        "sample_rate": 44100,
        "channels": 2,
        "duration": 300.5,
        "files": [Path("/test/file.flac")],
        "directory": Path("/test")
    }


@pytest.fixture
def mock_audnexus_response():
    """Mock response from Audnexus API"""
    return {
        "asin": "B0123456789",
        "title": "Test Book Title",
        "subtitle": "Test Subtitle",
        "authors": [{"name": "Test Author", "asin": "B0987654321"}],
        "narrators": [{"name": "Test Narrator"}],
        "summary": "This is a test book summary with <b>HTML</b> content.",
        "publisherName": "Test Publisher",
        "releaseDate": "2023-01-01T00:00:00.000Z",
        "runtimeLengthMin": 360,
        "genres": [{"name": "Fiction", "type": "genre"}],
        "rating": 4.5,
        "isbn": "978-0123456789"
    }


class TestHTMLCleaner:
    """Test HTML cleaning functionality"""

    @pytest.fixture
    def cleaner(self):
        return HTMLCleaner()

    def test_clean_html_string_basic(self, cleaner):
        """Test basic HTML cleaning"""
        html_text = "This is <b>bold</b> and <i>italic</i> text."
        result = cleaner.clean_html_string(html_text)
        assert "<b>" not in result
        assert "<i>" not in result
        assert "bold" in result
        assert "italic" in result

    def test_clean_html_string_entities(self, cleaner):
        """Test HTML entity cleaning"""
        html_text = "Price: &amp; &lt; &gt; &quot;test&quot;"
        result = cleaner.clean_html_string(html_text)
        assert "&amp;" not in result
        assert "&lt;" not in result
        assert "&gt;" not in result
        assert "&quot;" not in result
        assert 'Price: & < > "test"' == result

    def test_clean_html_string_with_nh3(self, cleaner):
        """Test HTML cleaning with nh3 sanitizer"""
        html_text = '<script>alert("xss")</script><p>Safe content</p>'
        result = cleaner.clean_html_string(html_text)
        assert "<script>" not in result
        assert "alert" not in result
        assert "Safe content" in result

    def test_sanitize_metadata_dict(self, cleaner):
        """Test sanitizing entire metadata dictionary"""
        metadata = {
            "title": "Test <b>Title</b>",
            "description": "Test &amp; description",
            "nested": {
                "html": "<i>nested</i> content"
            },
            "list": ["<b>item1</b>", "<i>item2</i>"]
        }
        result = cleaner.sanitize(metadata)

        assert "<b>" not in result["title"]
        assert "<i>" not in result["nested"]["html"]
        assert all("<b>" not in item and "<i>" not in item for item in result["list"])


class TestFormatDetector:
    """Test audio format detection"""

    @pytest.fixture
    def detector(self):
        return FormatDetector()

    def test_supported_formats(self, detector):
        """Test format detection for supported file types"""
        assert detector.supported_formats[".flac"] == "FLAC"
        assert detector.supported_formats[".mp3"] == "MP3"
        assert detector.supported_formats[".m4b"] == "AAC"

    @pytest.mark.parametrize("file_ext,expected_format", [
        (".flac", "FLAC"),
        (".mp3", "MP3"),
        (".m4a", "AAC"),
        (".m4b", "AAC"),
        (".ogg", "Vorbis"),
        (".unknown", "Unknown")
    ])
    def test_format_mapping(self, detector, file_ext, expected_format):
        """Test format mapping for different extensions"""
        assert detector.supported_formats.get(file_ext, "Unknown") == expected_format

    def test_basic_format_detection_without_mutagen(self, detector, temp_dir):
        """Test basic format detection when mutagen is not available"""
        # Create test files
        flac_file = temp_dir / "test.flac"
        mp3_file = temp_dir / "test.mp3"
        flac_file.touch()
        mp3_file.touch()

        with patch('src.mk_torrent.features.metadata_engine.MUTAGEN_AVAILABLE', False):
            result = detector.analyze([flac_file, mp3_file])

        assert "format" in result
        assert result["format"] in ["FLAC", "MP3", "FLAC, MP3"]

    def test_mp3_quality_classification(self, detector):
        """Test MP3 quality classification"""
        # CBR tests
        assert detector._classify_mp3_quality(320000, 0) == "MP3 320k"
        assert detector._classify_mp3_quality(128000, 0) == "MP3 128k"

        # VBR tests
        assert detector._classify_mp3_quality(220000, 1) == "MP3 V0"
        assert detector._classify_mp3_quality(190000, 1) == "MP3 V1"
        assert detector._classify_mp3_quality(170000, 1) == "MP3 V2"


class TestAudnexusAPI:
    """Test Audnexus API integration"""

    @pytest.fixture
    def api(self):
        return AudnexusAPI()

    def test_extract_asin_from_filename(self, api):
        """Test ASIN extraction from filenames"""
        test_cases = [
            ("Test Book {ASIN.B012345678}.m4b", "B012345678"),
            ("{ASIN.B098765432} Test Book.mp3", "B098765432"),
            ("No ASIN here.txt", None),
            ("{ASIN.B012345678} Multiple {ASIN.B098765432}", "B012345678")
        ]

        for filename, expected in test_cases:
            result = api.extract_asin(filename)
            assert result == expected

    @pytest.mark.integration
    def test_get_book_metadata_real_api(self, api):
        """Test real API call (requires internet)"""
        # This would be a real API test
        pass

    def test_normalize_audnexus_data(self, api, mock_audnexus_response):
        """Test normalization of Audnexus API response"""
        result = api._normalize_audnexus_data(mock_audnexus_response)

        assert result["asin"] == "B0123456789"
        assert result["title"] == "Test Book Title"
        assert result["subtitle"] == "Test Subtitle"
        assert result["authors"] == ["Test Author"]
        assert result["narrators"] == ["Test Narrator"]
        assert "<b>" not in result["summary"]  # HTML should be cleaned
        assert result["publisherName"] == "Test Publisher"
        assert result["year"] == "2023"
        assert result["runtime_formatted"] == "6h 0m"

    def test_clean_html_summary(self, api):
        """Test HTML cleaning in summary"""
        summary = 'Test <b>bold</b> and <script>alert("xss")</script>safe content.'
        result = api._clean_html_summary(summary)

        assert "<b>" not in result
        assert "<script>" not in result
        assert "alert" not in result
        assert "bold" in result
        assert "safe content" in result


class TestTagNormalizer:
    """Test tag normalization"""

    @pytest.fixture
    def normalizer(self):
        return TagNormalizer()

    def test_normalize_basic_tags(self, normalizer):
        """Test basic tag normalization"""
        tags = ["rap", "hiphop", "hip hop", "rnb", "rhythm and blues"]
        result = normalizer.normalize(tags)

        assert "Hip-Hop" in result
        assert "R&B" in result
        assert "rap" not in result
        assert "hiphop" not in result

    def test_normalize_case_insensitive(self, normalizer):
        """Test case-insensitive normalization"""
        tags = ["RAP", "HipHop", "R&B"]
        result = normalizer.normalize(tags)

        assert "Hip-Hop" in result
        assert "R&B" in result

    def test_remove_duplicates(self, normalizer):
        """Test duplicate removal"""
        tags = ["rock", "Rock", "ROCK"]
        result = normalizer.normalize(tags)

        assert len(result) == 1
        assert result[0] == "Rock"

    def test_red_genre_filtering(self, normalizer):
        """Test RED genre filtering"""
        tags = ["rock", "unknown_genre", "pop", "invalid"]
        result = normalizer.normalize(tags)

        assert "Rock" in result
        assert "Pop" in result
        assert "unknown_genre" not in result  # Should be filtered out
        assert "invalid" not in result


class TestMetadataEngine:
    """Test the main metadata engine"""

    @pytest.fixture
    def engine(self):
        return MetadataEngine()

    def test_process_metadata_basic(self, engine, temp_dir):
        """Test basic metadata processing"""
        # Create a mock audio file
        audio_file = temp_dir / "test.flac"
        audio_file.touch()

        with patch('src.mk_torrent.features.metadata_engine.MUTAGEN_AVAILABLE', False):
            result = engine.process_metadata([audio_file])

        assert "validation" in result
        assert "format" in result
        assert "artwork" in result

    def test_validate_red_compliance(self, engine, sample_metadata):
        """Test RED compliance validation"""
        result = engine._validate_red_compliance(sample_metadata)

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["score"] == 100

    def test_validate_red_compliance_missing_fields(self, engine):
        """Test validation with missing required fields"""
        incomplete_metadata = {"title": "Test"}
        result = engine._validate_red_compliance(incomplete_metadata)

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("artist" in error for error in result["errors"])
        assert any("album" in error for error in result["errors"])

    def test_build_enhanced_description(self, engine, mock_audnexus_response):
        """Test building enhanced description"""
        result = engine._build_enhanced_description(mock_audnexus_response)

        assert "Test Book Title" in result
        assert "Test Subtitle" in result
        assert "Test Author" in result
        assert "Test Publisher" in result
        assert "6h 0m" in result

    @patch('src.mk_torrent.features.metadata_engine.requests.Session.get')
    def test_enrich_with_audnexus(self, mock_get, engine, temp_dir, mock_audnexus_response):
        """Test Audnexus enrichment"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_audnexus_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Create test file with ASIN
        audio_file = temp_dir / "{ASIN.B0123456789} Test Book.m4b"
        audio_file.touch()

        result = engine._enrich_with_audnexus([audio_file], {})

        assert "asin" in result
        assert result["asin"] == "B0123456789"
        assert "authors" in result
        assert "Test Author" in result["authors"]

    def test_basic_metadata_extraction(self, engine, temp_dir):
        """Test basic metadata extraction from folder names"""
        # Create test directory with pattern: "Artist - Album (Year)"
        test_dir = temp_dir / "Test Artist - Test Album (2023)"
        test_dir.mkdir()

        result = engine._basic_metadata_extraction([test_dir])

        assert result["artist"] == "Test Artist"
        assert result["album"] == "Test Album"
        assert result["year"] == "2023"


class TestAlbumArtwork:
    """Test AlbumArtwork dataclass"""

    def test_artwork_creation(self):
        """Test creating AlbumArtwork instance"""
        artwork = AlbumArtwork(
            url="https://example.com/cover.jpg",
            width=500,
            height=500,
            format="JPEG",
            source="audnexus_api",
            confidence=0.9
        )

        assert artwork.url == "https://example.com/cover.jpg"
        assert artwork.width == 500
        assert artwork.height == 500
        assert artwork.format == "JPEG"
        assert artwork.source == "audnexus_api"
        assert artwork.confidence == 0.9

    def test_artwork_defaults(self):
        """Test AlbumArtwork default values"""
        artwork = AlbumArtwork(url="https://example.com/cover.jpg")

        assert artwork.width is None
        assert artwork.height is None
        assert artwork.format is None
        assert artwork.source == "unknown"
        assert artwork.confidence == 0.0


class TestAudioFormat:
    """Test AudioFormat dataclass"""

    def test_audio_format_creation(self):
        """Test creating AudioFormat instance"""
        audio_format = AudioFormat(
            codec="FLAC",
            bitrate=1411000,
            sample_rate=44100,
            channels=2,
            bit_depth=16,
            vbr=False,
            lossless=True
        )

        assert audio_format.codec == "FLAC"
        assert audio_format.bitrate == 1411000
        assert audio_format.sample_rate == 44100
        assert audio_format.channels == 2
        assert audio_format.bit_depth == 16
        assert audio_format.vbr is False
        assert audio_format.lossless is True

    def test_audio_format_defaults(self):
        """Test AudioFormat default values"""
        audio_format = AudioFormat(codec="MP3")

        assert audio_format.bitrate is None
        assert audio_format.sample_rate is None
        assert audio_format.channels is None
        assert audio_format.bit_depth is None
        assert audio_format.vbr is False
        assert audio_format.lossless is False


# Integration tests
@pytest.mark.integration
class TestMetadataIntegration:
    """Integration tests for metadata processing"""

    def test_full_metadata_pipeline(self, engine, temp_dir):
        """Test complete metadata processing pipeline"""
        # This would test the full pipeline with real files
        pass

    def test_audnexus_api_integration(self, engine):
        """Test real Audnexus API integration"""
        # This would test actual API calls
        pass


if __name__ == "__main__":
    pytest.main([__file__])
