"""
Shared upload specification types and base classes.

This module provides common types and base structures that tracker-specific
upload specs extend. It centralizes shared validation logic and common fields
to reduce duplication across tracker implementations.

Architecture:
- Base types shared across all trackers (Artist, RemasterInfo, etc.)
- Common enums for standardized values (AudioFormat, MediaType, etc.)
- Validation utilities for consistent data quality
- Abstract base classes for tracker-specific extensions

Tracker-specific modules (e.g., trackers/red/upload_spec.py) import and extend
these shared types rather than reimplementing common functionality.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator


class AudioFormat(str, Enum):
    """Supported audio formats across trackers."""

    FLAC = "FLAC"
    MP3 = "MP3"
    AAC = "AAC"
    AC3 = "AC-3"
    DTS = "DTS"
    OGG = "OGG Vorbis"
    OPUS = "Opus"


class MediaType(str, Enum):
    """Media source types common across trackers."""

    CD = "CD"
    DVD = "DVD"
    VINYL = "Vinyl"
    WEB = "WEB"
    SOUNDBOARD = "Soundboard"
    SACD = "SACD"
    CASSETTE = "Cassette"
    RADIO = "Radio"
    UNKNOWN = "Unknown"


class ReleaseType(str, Enum):
    """Release type classifications."""

    ALBUM = "Album"
    SOUNDTRACK = "Soundtrack"
    EP = "EP"
    ANTHOLOGY = "Anthology"
    COMPILATION = "Compilation"
    SINGLE = "Single"
    LIVE_ALBUM = "Live album"
    REMIX = "Remix"
    INTERVIEW = "Interview"
    MIXTAPE = "Mixtape"
    DEMO = "Demo"
    CONCERT_RECORDING = "Concert Recording"
    DJ_MIX = "DJ Mix"
    UNKNOWN = "Unknown"


class ArtistType(str, Enum):
    """Artist role classifications."""

    MAIN = "main"
    GUEST = "guest"
    COMPOSER = "composer"
    CONDUCTOR = "conductor"
    PRODUCER = "producer"
    REMIXER = "remixer"
    FEATURING = "featuring"
    ARRANGER = "arranger"
    WITH = "with"


class Artist(BaseModel):
    """Artist information with type classification."""

    name: str = Field(..., min_length=1, description="Artist name")
    type: ArtistType = Field(default=ArtistType.MAIN, description="Artist role type")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate artist name is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("Artist name cannot be empty or contain only whitespace")
        return v.strip()


class RemasterInfo(BaseModel):
    """Remaster edition information."""

    year: int | None = Field(None, ge=1800, le=2030, description="Remaster year")
    title: str | None = Field(None, description="Remaster title/edition")
    record_label: str | None = Field(None, description="Remaster record label")
    catalogue_number: str | None = Field(None, description="Remaster catalogue number")

    @field_validator("year")
    @classmethod
    def validate_remaster_year(cls, v: int | None) -> int | None:
        """Validate remaster year is in reasonable range."""
        if v is not None and not (1800 <= v <= 2030):
            raise ValueError(f"Remaster year must be between 1800 and 2030, got {v}")
        return v


class TorrentFileInfo(BaseModel):
    """Torrent file and data path information."""

    torrent_path: Path = Field(..., description="Path to .torrent file")
    data_path: Path = Field(..., description="Path to actual data directory/file")

    @model_validator(mode="after")
    def validate_paths_exist(self) -> TorrentFileInfo:
        """Validate that both torrent file and data path exist."""
        if not self.torrent_path.exists():
            raise ValueError(f"Torrent file does not exist: {self.torrent_path}")
        if not self.data_path.exists():
            raise ValueError(f"Data path does not exist: {self.data_path}")
        return self


class BaseUploadSpec(BaseModel):
    """Base upload specification with common fields."""

    # Identity
    title: str = Field(..., min_length=1, description="Release title")
    artists: list[Artist] = Field(
        ..., min_length=1, description="Artist information with roles"
    )
    year: int = Field(..., ge=1800, le=2030, description="Release year")

    # Format and technical
    format: AudioFormat = Field(..., description="Audio format")
    media: MediaType = Field(default=MediaType.WEB, description="Media source")
    release_type: ReleaseType = Field(
        default=ReleaseType.ALBUM, description="Type of release"
    )

    # Content
    description: str = Field(..., min_length=1, description="Release description")
    tags: list[str] = Field(default_factory=list, description="Genre/style tags")

    # Optional metadata
    remaster: RemasterInfo | None = Field(None, description="Remaster information")

    # Files
    torrent_info: TorrentFileInfo = Field(..., description="Torrent and data files")

    # Tracker-specific extensions
    extra_fields: dict[str, Any] = Field(
        default_factory=dict, description="Tracker-specific fields"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or contain only whitespace")
        return v.strip()

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Validate release year is in reasonable range."""
        if not (1800 <= v <= 2030):
            raise ValueError(f"Year must be between 1800 and 2030, got {v}")
        return v

    @field_validator("artists")
    @classmethod
    def validate_artists_not_empty(cls, v: list[Artist]) -> list[Artist]:
        """Validate at least one artist is provided."""
        if not v:
            raise ValueError("At least one artist must be provided")
        return v

    def add_extra_field(self, key: str, value: Any) -> None:
        """Add tracker-specific field."""
        self.extra_fields[key] = value

    def get_extra_field(self, key: str, default: Any = None) -> Any:
        """Get tracker-specific field with optional default."""
        return self.extra_fields.get(key, default)

    @property
    def primary_artist(self) -> str:
        """Get the primary (main) artist name."""
        main_artists = [a.name for a in self.artists if a.type == ArtistType.MAIN]
        return main_artists[0] if main_artists else self.artists[0].name

    @property
    def release_name(self) -> str:
        """Generate standardized release name: 'Artist - Title (Year)'."""
        return f"{self.primary_artist} - {self.title} ({self.year})"


class BitrateInfo(BaseModel):
    """Bitrate information with validation."""

    bitrate: str = Field(
        ..., description="Bitrate value (e.g., '320', 'V0', 'Lossless')"
    )
    mode: str = Field(default="", description="Bitrate mode (CBR, VBR, etc.)")

    @field_validator("bitrate")
    @classmethod
    def validate_bitrate(cls, v: str) -> str:
        """Validate bitrate format."""
        if not v or not v.strip():
            raise ValueError("Bitrate cannot be empty")
        return v.strip()


class UploadCredits(BaseModel):
    """Upload credits and attribution information."""

    ripper: str = Field(default="", description="Ripper/uploader credit")
    source: str = Field(default="", description="Source information")
    additional_info: dict[str, str] = Field(
        default_factory=dict, description="Additional credit fields"
    )

    def add_credit(self, key: str, value: str) -> None:
        """Add additional credit field."""
        self.additional_info[key] = value

    def get_credit(self, key: str, default: str = "") -> str:
        """Get credit field with optional default."""
        return self.additional_info.get(key, default)


# Utility functions for common validation patterns
def validate_year_range(
    year: int | None, min_year: int = 1800, max_year: int = 2030
) -> int | None:
    """Validate year is within reasonable range."""
    if year is not None and not (min_year <= year <= max_year):
        raise ValueError(f"Year must be between {min_year} and {max_year}, got {year}")
    return year


def validate_non_empty_string(
    value: str | None, field_name: str = "Field"
) -> str | None:
    """Validate string is not empty or just whitespace."""
    if value is not None:
        value = value.strip()
        if not value:
            raise ValueError(f"{field_name} cannot be empty or contain only whitespace")
    return value


def normalize_artist_list(artists: list[str | Artist]) -> list[Artist]:
    """Normalize mixed artist input to Artist objects."""
    result: list[Artist] = []
    for artist in artists:
        if isinstance(artist, str):
            result.append(Artist(name=artist, type=ArtistType.MAIN))
        else:
            result.append(artist)
    return result
