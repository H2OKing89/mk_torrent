"""
Audiobook metadata processor.

Orchestrates metadata extraction from multiple sources (Audnexus API, embedded
metadata, filename parsing) and uses sophisticated merging to combine them into
a comprehensive audiobook metadata record.
"""

import logging
from pathlib import Path
from typing import Any

from ..base import ValidationResult
from ..sources.audnexus import AudnexusSource
from ..sources.embedded import EmbeddedSource
from ..sources.pathinfo import PathInfoSource
from ..exceptions import SourceUnavailable

logger = logging.getLogger(__name__)


class AudiobookProcessor:
    """
    Comprehensive audiobook metadata processor.

    Orchestrates extraction from multiple sources and uses sophisticated
    merging to combine results into a comprehensive metadata record.

    Sources used (in precedence order):
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
        self._embedded = None
        self._pathinfo = None

    def _get_audnexus_source(self) -> AudnexusSource:
        """Get or create Audnexus source instance."""
        if self._audnexus is None:
            self._audnexus = AudnexusSource(region=self.region)
        return self._audnexus

    def _get_embedded_source(self) -> EmbeddedSource:
        """Get or create embedded metadata source instance."""
        if self._embedded is None:
            self._embedded = EmbeddedSource()
        return self._embedded

    def _get_pathinfo_source(self) -> PathInfoSource:
        """Get or create path info source instance."""
        if self._pathinfo is None:
            self._pathinfo = PathInfoSource()
        return self._pathinfo

    def extract(self, source: "str | Path") -> "dict[str, Any]":
        """
        Extract audiobook metadata from all sources and merge intelligently.

        Uses sophisticated three-source architecture:
        1. Extract from API (Audnexus) if ASIN available
        2. Extract from embedded metadata in file
        3. Extract from filename/path patterns
        4. Merge using declarative precedence rules

        Args:
            source: File path or directory containing audiobook

        Returns:
            Dict containing merged metadata from all sources
        """
        source_path = Path(source) if isinstance(source, str) else source
        candidates = []

        # Extract from Audnexus API
        try:
            audnexus_source = self._get_audnexus_source()
            api_metadata = audnexus_source.extract(str(source_path))
            api_metadata["_src"] = "api"
            candidates.append(api_metadata)
            logger.info("Successfully extracted metadata from Audnexus API")
        except SourceUnavailable as e:
            logger.debug(f"Audnexus extraction failed: {e.reason}")
        except Exception as e:
            logger.warning(f"Audnexus extraction error: {e}")

        # Extract from embedded metadata
        try:
            embedded_source = self._get_embedded_source()
            embedded_metadata = embedded_source.extract(str(source_path))
            embedded_metadata["_src"] = "embedded"
            candidates.append(embedded_metadata)
            logger.info("Successfully extracted embedded metadata")
        except SourceUnavailable as e:
            logger.debug(f"Embedded extraction failed: {e.reason}")
        except Exception as e:
            logger.warning(f"Embedded extraction error: {e}")

        # Extract from path/filename
        try:
            pathinfo_source = self._get_pathinfo_source()
            path_metadata = pathinfo_source.extract(str(source_path))
            path_metadata["_src"] = "path"
            candidates.append(path_metadata)
            logger.info("Successfully extracted path metadata")
        except Exception as e:
            logger.warning(f"Path extraction error: {e}")

        # Merge using sophisticated merger
        if candidates:
            from ..services.merge_audiobook import merge_metadata

            merged = merge_metadata(candidates)
            logger.info(f"Merged metadata from {len(candidates)} sources")
        else:
            # Fallback if no sources worked
            merged = {
                "title": source_path.stem,
                "author": "Unknown",
            }
            logger.warning("No metadata sources available, using fallback")

        # Add processing metadata
        merged["source_path"] = str(source_path)
        merged["processor"] = "audiobook"

        return merged

    def validate(self, metadata: "dict[str, Any]") -> ValidationResult:
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

    def enhance(self, metadata: "dict[str, Any]") -> "dict[str, Any]":
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
