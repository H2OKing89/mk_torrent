"""
The main metadata engine - Core Modular Metadata System.

Central orchestrator that replaces legacy monolithic processing with a clean,
extensible architecture supporting multiple content types and processing strategies.

Orchestrates processors, sources, and services through dependency injection and
registry patterns for maximum flexibility and testability.

This is the "one true engine" that provides a clean interface for extracting,
validating, and mapping metadata across different content types.

Architecture Documentation:
- Engine Pipeline: docs/core/metadata/06 — Engine Pipeline.md
- Services Overview: docs/core/metadata/07 — Services Details.md
- Base Protocols: docs/core/metadata/05 — Protocol & Entity Design.md
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

from .base import (
    AudiobookMeta,
    MetadataProcessor,
    MetadataMapper,
    ValidationResult,
    Source,
)
from .exceptions import ProcessorNotFound, MetadataError

logger = logging.getLogger(__name__)


class MetadataEngine:
    """Main metadata processing engine with dependency injection and registry pattern."""

    def __init__(self):
        self._processors: dict[str, MetadataProcessor] = {}
        self._mappers: dict[str, MetadataMapper] = {}
        self._default_processor: str | None = None

    def register_processor(
        self, content_type: str, processor: MetadataProcessor
    ) -> None:
        """Register a processor for a specific content type."""
        self._processors[content_type] = processor
        logger.debug(f"Registered processor for content type: {content_type}")

    def register_mapper(self, tracker_name: str, mapper: MetadataMapper) -> None:
        """Register a mapper for a specific tracker."""
        self._mappers[tracker_name] = mapper
        logger.debug(f"Registered mapper for tracker: {tracker_name}")

    def set_default_processor(self, content_type: str) -> None:
        """Set the default processor to use when content type cannot be detected."""
        if content_type not in self._processors:
            raise ProcessorNotFound(content_type, list(self._processors.keys()))
        self._default_processor = content_type

    def detect_content_type(self, source: Source) -> str:
        """Detect content type from file extension or directory contents."""
        if isinstance(source, str):
            source = Path(source)

        # Check file extension first (works for both real and hypothetical files)
        suffix = source.suffix.lower()
        if suffix in {".m4b"}:  # Dedicated audiobook format
            return "audiobook"
        elif suffix in {".mp4", ".mkv", ".avi", ".mov"}:
            return "video"
        elif suffix in {".m4a", ".mp3", ".flac", ".aac", ".ogg"}:
            # Could be audiobook or music, check context if file exists
            if source.exists() and self._is_music_context(source):
                return "music"
            else:
                return "audiobook"  # Default for audio files

        # If no suffix match, check if it's a directory
        if source.exists() and source.is_dir():
            # Check directory contents
            audio_files = list(source.glob("**/*.m4b")) + list(source.glob("**/*.m4a"))
            if audio_files:
                return "audiobook"

        # Fall back to default if set
        if self._default_processor:
            return self._default_processor

        # Default to audiobook for now
        return "audiobook"

    def _is_music_context(self, file_path: Path) -> bool:
        """Heuristic to detect if this is music vs audiobook based on context."""
        # Simple heuristic: check parent directory names
        parent_parts = [p.lower() for p in file_path.parts]
        music_indicators = {"music", "songs", "albums", "tracks", "artist"}
        audiobook_indicators = {"audiobook", "audiobooks", "books", "chapters"}

        if any(indicator in parent_parts for indicator in audiobook_indicators):
            return False
        if any(indicator in parent_parts for indicator in music_indicators):
            return True

        # Default to audiobook for ambiguous cases
        return False

    def extract_metadata(
        self, source: Source, content_type: str | None = None, enhance: bool = True
    ) -> dict[str, Any]:
        """Extract metadata from a source using the appropriate processor."""
        try:
            # Detect content type if not provided
            if content_type is None:
                content_type = self.detect_content_type(source)

            # Get the processor
            if content_type not in self._processors:
                raise ProcessorNotFound(content_type, list(self._processors.keys()))

            processor = self._processors[content_type]

            logger.info(
                f"Extracting metadata from {source} using {content_type} processor"
            )

            # Extract metadata
            metadata = processor.extract(source)

            # Enhance with derived fields if requested
            if enhance:
                metadata = processor.enhance(metadata)

            logger.debug(f"Successfully extracted metadata: {len(metadata)} fields")
            return metadata

        except Exception as e:
            logger.error(f"Failed to extract metadata from {source}: {e}")
            raise MetadataError(f"Extraction failed: {e}") from e

    def validate_metadata(
        self,
        metadata: dict[str, Any] | AudiobookMeta,
        content_type: str | None = None,
    ) -> ValidationResult:
        """Validate metadata using the appropriate processor."""
        try:
            # Convert to dict if needed
            if isinstance(metadata, AudiobookMeta):
                metadata_dict = metadata.to_dict()
                content_type = content_type or "audiobook"
            else:
                metadata_dict = metadata

            # Use default processor if content type not specified
            if content_type is None:
                content_type = self._default_processor or "audiobook"

            if content_type not in self._processors:
                raise ProcessorNotFound(content_type, list(self._processors.keys()))

            processor = self._processors[content_type]

            logger.debug(f"Validating metadata using {content_type} processor")
            result = processor.validate(metadata_dict)

            logger.info(
                f"Validation result: valid={result.valid}, "
                f"errors={len(result.errors)}, warnings={len(result.warnings)}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to validate metadata: {e}")
            raise MetadataError(f"Validation failed: {e}") from e

    def map_to_tracker(
        self, metadata: dict[str, Any] | AudiobookMeta, tracker_name: str
    ) -> dict[str, Any]:
        """Map metadata to tracker-specific format."""
        try:
            if tracker_name not in self._mappers:
                available = list(self._mappers.keys())
                raise MetadataError(
                    f"No mapper found for tracker '{tracker_name}'. "
                    f"Available: {available}"
                )

            mapper = self._mappers[tracker_name]

            # Convert to AudiobookMeta if needed
            if isinstance(metadata, dict):
                audiobook_meta = AudiobookMeta.from_dict(metadata)
            else:
                audiobook_meta = metadata

            logger.debug(f"Mapping metadata for tracker: {tracker_name}")
            result = mapper.map_to_tracker(audiobook_meta)

            logger.info(
                f"Successfully mapped metadata for {tracker_name}: "
                f"{len(result)} fields"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to map metadata for {tracker_name}: {e}")
            raise MetadataError(f"Mapping failed: {e}") from e

    def process_full_pipeline(
        self,
        source: Source,
        content_type: str | None = None,
        tracker_name: str | None = None,
        validate: bool = True,
    ) -> dict[str, Any]:
        """Run the full pipeline: extract -> validate -> (optionally) map."""
        result = {
            "source": str(source),
            "content_type": content_type,
            "metadata": {},
            "validation": None,
            "tracker_data": None,
            "success": False,
        }

        try:
            # Extract metadata
            metadata = self.extract_metadata(source, content_type)
            result["metadata"] = metadata
            result["content_type"] = content_type or self.detect_content_type(source)

            # Validate if requested
            if validate:
                validation_result = self.validate_metadata(
                    metadata, result["content_type"]
                )
                result["validation"] = {
                    "valid": validation_result.valid,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                    "completeness": validation_result.completeness,
                }

            # Map to tracker format if requested
            if tracker_name:
                tracker_data = self.map_to_tracker(metadata, tracker_name)
                result["tracker_data"] = tracker_data

            result["success"] = True
            logger.info(f"Full pipeline completed successfully for {source}")

        except Exception as e:
            logger.error(f"Pipeline failed for {source}: {e}")
            result["error"] = str(e)

        return result

    def get_available_processors(self) -> list[str]:
        """Get list of available content type processors."""
        return list(self._processors.keys())

    def get_available_mappers(self) -> list[str]:
        """Get list of available tracker mappers."""
        return list(self._mappers.keys())


# Convenience function for backward compatibility
def process_metadata(
    source: Path | list[Path], content_type: str | None = None
) -> dict[str, Any]:
    """Convenience function to process metadata (legacy interface)."""
    engine = MetadataEngine()
    # Auto-register basic processors if none exist
    if not engine.get_available_processors():
        engine.set_default_processor("audiobook")

    if isinstance(source, list):
        source = source[0] if source else Path()

    return engine.process_full_pipeline(source, content_type)
