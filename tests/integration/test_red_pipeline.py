"""
Comprehensive RED integration test using real audiobook files.

This test demonstrates the complete pipeline from audiobook analysis through
RED upload specification generation and dry run testing.
"""

import json
import logging
from pathlib import Path

import pytest

from mk_torrent.core.metadata.engine import MetadataEngine
from mk_torrent.core.metadata.mappers.red import REDMapper
from mk_torrent.trackers.red_adapter import REDAdapter, REDConfig
from mk_torrent.trackers.upload_spec import (
    BitrateEncoding,
    Category,
    Credits,
    ReleaseInfo,
    TorrentFile,
    UploadSpec,
)

# Configure logging for detailed output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestREDPipelineIntegration:
    """Test complete RED integration pipeline."""

    @pytest.fixture
    def samples_dir(self) -> Path:
        """Get samples directory."""
        return Path(__file__).parent.parent / "samples"

    @pytest.fixture
    def audiobook_dir(self, samples_dir: Path) -> Path:
        """Get audiobook sample directory."""
        audiobook_path = (
            samples_dir
            / "audiobook"
            / "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]"
        )
        assert audiobook_path.exists(), f"Audiobook sample not found: {audiobook_path}"
        return audiobook_path

    @pytest.fixture
    def torrent_file(self, samples_dir: Path) -> Path:
        """Get torrent file."""
        torrent_path = (
            samples_dir
            / "torrent_files"
            / "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing].torrent"
        )
        assert torrent_path.exists(), f"Torrent file not found: {torrent_path}"
        return torrent_path

    @pytest.fixture
    def red_config(self) -> REDConfig:
        """Get RED configuration."""
        # Read API key from environment
        env_file = Path(__file__).parent.parent / ".env"
        api_key = None

        if env_file.exists():
            content = env_file.read_text()
            for line in content.splitlines():
                if line.startswith("RED_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break

        if not api_key:
            pytest.skip("RED_API_KEY not found in tests/.env file")

        return REDConfig(api_key=api_key)

    def test_metadata_extraction(self, audiobook_dir: Path):
        """Test that metadata engine can extract audiobook information."""
        logger.info(f"Testing metadata extraction from: {audiobook_dir}")

        # Initialize metadata engine
        engine = MetadataEngine()

        # Extract metadata
        metadata = engine.extract_metadata(audiobook_dir)

        # Verify core metadata fields
        assert metadata is not None, "Metadata extraction failed"
        assert metadata.title, "Title not extracted"
        assert metadata.authors, "Authors not extracted"

        logger.info(f"Extracted metadata - Title: {metadata.title}")
        logger.info(f"Extracted metadata - Authors: {metadata.authors}")

        # Log full metadata for inspection
        logger.info("Full metadata structure:")
        logger.info(json.dumps(metadata.model_dump(), indent=2, default=str))

        return metadata

    def test_red_mapping(self, audiobook_dir: Path):
        """Test RED mapper can generate upload fields."""
        logger.info(f"Testing RED mapping for: {audiobook_dir}")

        # Extract metadata
        engine = MetadataEngine()
        metadata = engine.extract_metadata(audiobook_dir)

        # Initialize RED mapper
        red_mapper = REDMapper()

        # Generate RED fields
        red_fields = red_mapper.map_metadata(metadata)

        # Verify essential RED fields
        assert "artist" in red_fields, "Artist field missing"
        assert "title" in red_fields, "Title field missing"
        assert "year" in red_fields, "Year field missing"
        assert "description" in red_fields, "Description field missing"

        logger.info("Generated RED fields:")
        for key, value in red_fields.items():
            if key == "description":
                logger.info(f"  {key}: [BBCode description - {len(value)} characters]")
            else:
                logger.info(f"  {key}: {value}")

        return red_fields

    def test_upload_spec_creation(self, audiobook_dir: Path, torrent_file: Path):
        """Test creation of upload specification."""
        logger.info("Testing upload spec creation")

        # Extract metadata
        engine = MetadataEngine()
        metadata = engine.extract_metadata(audiobook_dir)

        # Generate RED fields
        red_mapper = REDMapper()
        red_fields = red_mapper.map_metadata(metadata)

        # Create upload specification
        upload_spec = UploadSpec(
            category=Category.AUDIOBOOKS,
            release_info=ReleaseInfo(
                artist=red_fields["artist"],
                title=red_fields["title"],
                year=int(red_fields["year"]) if red_fields.get("year") else None,
                label=red_fields.get("label"),
                catalog_number=red_fields.get("catalog_number"),
            ),
            bitrate_encoding=BitrateEncoding(
                bitrate=128,  # Common for audiobooks
                encoding="MP3",
                vbr=False,
            ),
            credits=Credits(
                ripper="H2OKing",  # From folder name
                encoder="H2OKing",
                uploader="mk_torrent_test",
            ),
            description=red_fields["description"],
            tags=red_fields.get("tags", []),
            torrent=TorrentFile(
                file_path=torrent_file,
                data_path=audiobook_dir,
            ),
        )

        # Verify upload spec
        assert upload_spec.category == Category.AUDIOBOOKS
        assert upload_spec.release_name
        assert upload_spec.torrent.file_path.exists()
        assert upload_spec.torrent.data_path.exists()

        logger.info(f"Created upload spec for: {upload_spec.release_name}")
        logger.info(f"Description length: {len(upload_spec.description)} characters")
        logger.info(f"Credits: {upload_spec.credits.to_credits_string()}")

        return upload_spec

    @pytest.mark.asyncio
    async def test_red_dry_run(
        self, audiobook_dir: Path, torrent_file: Path, red_config: REDConfig
    ):
        """Test RED dry run upload with real data."""
        logger.info("Testing RED dry run upload")

        # Create upload specification
        upload_spec = self.test_upload_spec_creation(audiobook_dir, torrent_file)

        # Initialize RED adapter
        red_adapter = REDAdapter(red_config)

        # Perform dry run
        result = await red_adapter.dry_run_upload(upload_spec)

        # Log result
        logger.info(f"Dry run result - Success: {result.success}")
        logger.info(f"Dry run result - Message: {result.message}")

        if result.raw_response:
            logger.info("Raw RED response:")
            logger.info(json.dumps(result.raw_response, indent=2))

        # Verify result structure
        assert isinstance(result.success, bool)
        assert result.message
        assert result.dry_run is True

        # For now, we don't assert success=True since we might not have valid RED credentials
        # But we can verify the upload specification was properly formatted
        return result

    @pytest.mark.asyncio
    async def test_complete_pipeline(
        self, audiobook_dir: Path, torrent_file: Path, red_config: REDConfig
    ):
        """Test complete end-to-end pipeline."""
        logger.info("=" * 60)
        logger.info("COMPLETE RED PIPELINE TEST")
        logger.info("=" * 60)

        # Step 1: Extract metadata
        logger.info("Step 1: Extracting metadata...")
        metadata = self.test_metadata_extraction(audiobook_dir)

        # Step 2: Generate RED fields
        logger.info("\nStep 2: Generating RED fields...")
        red_fields = self.test_red_mapping(audiobook_dir)

        # Step 3: Create upload spec
        logger.info("\nStep 3: Creating upload specification...")
        upload_spec = self.test_upload_spec_creation(audiobook_dir, torrent_file)

        # Step 4: Dry run upload
        logger.info("\nStep 4: Performing RED dry run...")
        result = await self.test_red_dry_run(audiobook_dir, torrent_file, red_config)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Source: {audiobook_dir.name}")
        logger.info(f"Release: {upload_spec.release_name}")
        logger.info(f"Category: {upload_spec.category}")
        logger.info(f"Bitrate: {upload_spec.bitrate_encoding.display_name}")
        logger.info(f"Description: {len(upload_spec.description)} characters")
        logger.info(f"Dry run success: {result.success}")
        logger.info(f"Message: {result.message}")
        logger.info("=" * 60)

        return {
            "metadata": metadata,
            "red_fields": red_fields,
            "upload_spec": upload_spec,
            "dry_run_result": result,
        }
