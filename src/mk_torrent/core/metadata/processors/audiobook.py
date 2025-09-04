"""
Audiobook metadata processor.

Combines multiple sources (Audnexus API, embedded metadata, filename parsing)
to provide comprehensive audiobook metadata extraction.
"""

import logging
from pathlib import Path
from typing import Any

from ..base import ValidationResult
from ..sources.audnexus import AudnexusSource
from ..exceptions import SourceUnavailable

logger = logging.getLogger(__name__)


class AudiobookProcessor:
    """
    Comprehensive audiobook metadata processor.

    Uses multiple sources in priority order:
    1. Audnexus API (if ASIN available)
    2. Embedded metadata from file
    3. Filename/path parsing
    """

    def __init__(self, region: str = "us"):
        """
        Initialize audiobook processor.

        Args:
            region: Default region for Audnexus API queries
        """
        self.region = region
        self._audnexus = None

    def _get_audnexus_source(self) -> AudnexusSource:
        """Get or create Audnexus source instance."""
        if self._audnexus is None:
            self._audnexus = AudnexusSource(region=self.region)
        return self._audnexus

    def extract(self, source: str | Path) -> dict[str, Any]:
        """
        Extract audiobook metadata from source.

        Args:
            source: File path or directory containing audiobook

        Returns:
            Dict containing extracted metadata
        """
        metadata = {}
        source_path = Path(source) if isinstance(source, str) else source

        # Try Audnexus API first (if ASIN pattern found)
        try:
            audnexus_source = self._get_audnexus_source()
            audnexus_metadata = audnexus_source.extract(str(source_path))
            metadata.update(audnexus_metadata)
            logger.info("Successfully extracted metadata from Audnexus API")
        except SourceUnavailable as e:
            logger.debug(f"Audnexus extraction failed: {e.reason}")
        except Exception as e:
            logger.warning(f"Audnexus extraction error: {e}")

        # Fall back to filename parsing if no API data
        if not metadata.get("title"):
            filename_metadata = self._extract_from_filename(source_path)
            metadata.update(filename_metadata)
            logger.info("Extracted metadata from filename parsing")

        # Try embedded metadata extraction (future implementation)
        # embedded_metadata = self._extract_embedded(source_path)
        # metadata.update(embedded_metadata)

        # Ensure we have basic required fields
        if not metadata.get("title"):
            metadata["title"] = source_path.stem
        if not metadata.get("author"):
            metadata["author"] = "Unknown"

        # Add processing metadata
        metadata["source_path"] = source_path
        metadata["processor"] = "audiobook"

        return metadata

    def _extract_from_filename(self, source_path: Path) -> dict[str, Any]:
        """
        Extract metadata from filename patterns.

        Supports patterns like:
        - "Series Title - vol_XX (YEAR) (Author) {ASIN.XXX} [Uploader]"
        - "Author - Title"
        - Basic filename
        """
        stem = source_path.stem
        metadata = {}

        # Complex audiobook pattern: "Series - vol_XX (YEAR) (Author) {ASIN.XXX} [Uploader]"
        if " - vol_" in stem and "(" in stem:
            parts = stem.split(" - vol_")
            series_title = parts[0].strip()
            vol_part = parts[1]

            # Extract volume
            vol_match = vol_part.split(" ")[0]
            metadata["series"] = series_title
            metadata["volume"] = vol_match
            metadata["title"] = f"{series_title} - vol_{vol_match}"

            # Extract year
            if "(" in vol_part and ")" in vol_part:
                year_part = vol_part.split("(")[1].split(")")[0]
                if year_part.isdigit() and len(year_part) == 4:
                    metadata["year"] = int(year_part)

            # Extract author
            if ") (" in vol_part:
                author_part = vol_part.split(") (")[1].split(")")[0]
                metadata["author"] = author_part.strip()

            # Extract ASIN
            if "{ASIN." in vol_part and "}" in vol_part:
                asin_part = vol_part.split("{ASIN.")[1].split("}")[0]
                metadata["asin"] = asin_part.strip()

        # Simple "Author - Title" pattern
        elif " - " in stem:
            parts = stem.split(" - ", 1)
            metadata["author"] = parts[0].strip()
            metadata["title"] = parts[1].strip()

        # Fallback to just filename
        else:
            metadata["title"] = stem

        return metadata

    def validate(self, metadata: dict[str, Any]) -> ValidationResult:
        """
        Validate audiobook metadata using comprehensive validator.

        Args:
            metadata: Metadata dict to validate

        Returns:
            ValidationResult with validation status and details
        """
        # Import here to avoid circular imports
        from ..validators.audiobook_validator import validate_audiobook

        # Use the comprehensive validator
        validation_result = validate_audiobook(metadata)

        # Convert to ValidationResult format
        result = ValidationResult(valid=validation_result["valid"])

        # Add errors
        for error in validation_result["errors"]:
            result.add_error(error)

        # Add warnings
        for warning in validation_result["warnings"]:
            result.add_warning(warning)

        # Set completeness
        result.completeness = validation_result["completeness"]

        logger.debug(
            f"Validation completed: valid={result.valid}, "
            f"errors={len(result.errors)}, warnings={len(result.warnings)}, "
            f"completeness={result.completeness:.2f}"
        )

        return result

    def enhance(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Enhance metadata with derived fields and cleanup.

        Args:
            metadata: Raw metadata dict

        Returns:
            Enhanced metadata dict
        """
        enhanced = dict(metadata)

        # Create album field (for music player compatibility)
        if not enhanced.get("album"):
            title = enhanced.get("title", "")
            if title:
                enhanced["album"] = title

        # Create display name
        title = enhanced.get("title", "")
        author = enhanced.get("author", "")

        if title and author:
            enhanced["display_name"] = f"{title} by {author}"
        elif title:
            enhanced["display_name"] = title
        elif author:
            enhanced["display_name"] = f"Unknown by {author}"
        else:
            enhanced["display_name"] = "Unknown"

        # Format runtime if we have seconds
        duration_sec = enhanced.get("duration_seconds")
        if duration_sec and not enhanced.get("duration"):
            hours = duration_sec // 3600
            minutes = (duration_sec % 3600) // 60
            enhanced["duration"] = f"{hours}h {minutes}m"

        # Normalize genres to list
        if enhanced.get("genre") and not enhanced.get("genres"):
            enhanced["genres"] = [enhanced["genre"]]

        # Clean up string fields
        for field in [
            "title",
            "author",
            "narrator",
            "publisher",
            "description",
            "summary",
        ]:
            value = enhanced.get(field)
            if isinstance(value, str):
                enhanced[field] = value.strip()

        return enhanced
