"""
Core protocols, interfaces, and data models for the metadata system.

This module defines the canonical data structures and interfaces that all
metadata processors, sources, and services must implement.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Union


@dataclass
class AudiobookMeta:
    """Canonical audiobook metadata container.

    This is the primary data transfer object used throughout the metadata
    system. Uses dataclass for fast, zero-dependency operation with an
    optional pydantic mirror under schemas/ for strict validation.
    """

    title: str = ""
    author: str = ""
    album: str = ""  # default: title
    series: str = ""
    volume: str = ""  # e.g., "08"
    year: Optional[int] = None
    narrator: str = ""
    duration_sec: Optional[int] = None
    format: str = ""  # AAC/FLAC/MP3/etc
    encoding: str = ""  # V0/CBR320/Lossless/etc
    asin: str = ""
    isbn: str = ""
    publisher: str = ""
    language: str = "en"
    description: str = ""
    genres: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    chapters: List[Dict[str, Any]] = field(default_factory=list)
    files: List[Path] = field(default_factory=list)
    source_path: Optional[Path] = None
    artwork_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudiobookMeta":
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
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    completeness: float = 0.0  # 0.0 to 1.0

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another validation result into this one."""
        return ValidationResult(
            valid=self.valid and other.valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            completeness=min(self.completeness, other.completeness),
        )


class MetadataSource(Protocol):
    """Protocol for metadata extraction sources."""

    def extract(self, source: Union[Path, str]) -> Dict[str, Any]:
        """Extract metadata from a source (file path, URL, etc.)."""
        ...

    def is_available(self) -> bool:
        """Check if this source is available (dependencies, network, etc.)."""
        ...


class MetadataService(Protocol):
    """Protocol for metadata processing services."""

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process/transform metadata."""
        ...


class MetadataValidator(Protocol):
    """Protocol for metadata validation."""

    def validate(
        self, metadata: Union[AudiobookMeta, Dict[str, Any]]
    ) -> ValidationResult:
        """Validate metadata and return detailed results."""
        ...


class MetadataProcessor(Protocol):
    """Protocol for content-type specific metadata processors."""

    def extract(self, source: Union[Path, str]) -> Dict[str, Any]:
        """Extract metadata from source using all available sources/services."""
        ...

    def validate(self, metadata: Dict[str, Any]) -> ValidationResult:
        """Validate extracted metadata."""
        ...

    def enhance(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Add derived/computed fields to metadata."""
        ...


class MetadataMapper(Protocol):
    """Protocol for tracker-specific field mapping."""

    def map_to_tracker(self, metadata: AudiobookMeta) -> Dict[str, Any]:
        """Map internal metadata model to tracker-specific format."""
        ...

    def map_from_tracker(self, tracker_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map tracker-specific data back to internal format."""
        ...


# Type aliases for clarity
Source = Union[Path, str]
MetadataDict = Dict[str, Any]
