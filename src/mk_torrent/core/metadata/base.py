"""
Core protocols, interfaces, and data models - Core Modular Metadata System.

Foundation of the new modular metadata architecture providing type-safe interfaces
and canonical data structures that replace ad-hoc data handling with structured,
validated entity models.

This module defines the canonical data structures and interfaces that all
metadata processors, sources, and services must implement.

Architecture Documentation:
- Protocol Design: docs/core/metadata/05 — Protocol & Entity Design.md
- Entity Models: docs/core/metadata/04 — Comprehensive Entity Model.md
- Base Architecture: docs/core/metadata/03 — Foundation Architecture.md
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Protocol, Union


@dataclass
class AudiobookMeta:
    """Canonical audiobook metadata container.

    This is the primary data transfer object used throughout the metadata
    system. Uses dataclass for fast, zero-dependency operation with an
    optional pydantic mirror under schemas/ for strict validation.
    """

    title: str = ""
    subtitle: str = ""  # Enhanced field for book subtitles
    author: str = ""
    album: str = ""  # default: title
    series: str = ""
    volume: str = ""  # e.g., "08"
    year: int | None = None
    narrator: str = ""
    duration_sec: int | None = None
    format: str = ""  # AAC/FLAC/MP3/etc
    encoding: str = ""  # V0/CBR320/Lossless/etc
    asin: str = ""
    isbn: str = ""
    publisher: str = ""
    copyright: str = ""  # Enhanced field for copyright notice
    release_date: str = ""  # Enhanced field for release date (ISO format)
    rating: float | None = None  # Enhanced field for rating (0.0-5.0)
    language: str = "en"
    region: str = ""  # Enhanced field for region/country code
    literature_type: str = ""  # Enhanced field (fiction, non-fiction, etc.)
    format_type: str = ""  # Enhanced field (m4b, mp3, etc.)
    is_adult: bool | None = None  # Enhanced field for adult content flag
    description: str = ""
    description_html: str = ""  # Enhanced field for HTML description
    description_text: str = ""  # Enhanced field for plain text description
    genres: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    chapters: list[dict[str, Any]] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)
    source_path: Path | None = None
    artwork_url: str = ""
    cover_dimensions: dict[str, int] | None = (
        None  # Enhanced field {"width": 600, "height": 800}
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AudiobookMeta:
        """Create instance from dictionary data."""
        # Filter out unknown fields and convert Path objects
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}

        # Convert string paths back to Path objects
        if "source_path" in valid_fields and isinstance(
            valid_fields["source_path"], str
        ):
            valid_fields["source_path"] = Path(valid_fields["source_path"])

        if "files" in valid_fields:
            valid_fields["files"] = [
                Path(f) if isinstance(f, str) else f for f in valid_fields["files"]
            ]

        return cls(**valid_fields)


@dataclass
class ValidationResult:
    """Result of metadata validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    completeness: float = 0.0  # 0.0 to 1.0

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Merge another validation result into this one."""
        return ValidationResult(
            valid=self.valid and other.valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            completeness=min(self.completeness, other.completeness),
        )


class MetadataSource(Protocol):
    """Protocol for metadata extraction sources."""

    def extract(self, source: Path | str) -> dict[str, Any]:
        """Extract metadata from a source (file path, URL, etc.)."""
        ...

    def is_available(self) -> bool:
        """Check if this source is available (dependencies, network, etc.)."""
        ...


class MetadataService(Protocol):
    """Protocol for metadata processing services."""

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process/transform metadata."""
        ...


class MetadataValidator(Protocol):
    """Protocol for metadata validation."""

    def validate(self, metadata: AudiobookMeta | dict[str, Any]) -> ValidationResult:
        """Validate metadata and return detailed results."""
        ...


class MetadataProcessor(Protocol):
    """Protocol for content-type specific metadata processors."""

    def extract(self, source: Path | str) -> dict[str, Any]:
        """Extract metadata from source using all available sources/services."""
        ...

    def validate(self, metadata: dict[str, Any]) -> ValidationResult:
        """Validate extracted metadata."""
        ...

    def enhance(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Add derived/computed fields to metadata."""
        ...


class MetadataMapper(Protocol):
    """Protocol for tracker-specific field mapping."""

    def map_to_tracker(self, metadata: AudiobookMeta) -> dict[str, Any]:
        """Map internal metadata model to tracker-specific format."""
        ...

    def map_from_tracker(self, tracker_data: dict[str, Any]) -> dict[str, Any]:
        """Map tracker-specific data back to internal format."""
        ...


# Type aliases for clarity
Source = Union[Path, str]
MetadataDict = "dict[str, Any]"
