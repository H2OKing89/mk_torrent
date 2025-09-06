"""
Upload specification system for tracker-agnostic upload data.

This module provides a clean, structured way to represent upload data that can be
converted to tracker-specific formats (like RED's multipart form data).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class Category(str, Enum):
    """Upload categories."""

    AUDIOBOOKS = "audiobooks"
    MUSIC = "music"
    E_BOOKS = "e-books"
    E_LEARNING = "e-learning-videos"
    COMEDY = "comedy"
    PODCASTS = "podcasts"


class BitrateEncoding(BaseModel):
    """Bitrate and encoding information."""

    bitrate: int = Field(..., description="Bitrate in kbps")
    encoding: str = Field(..., description="Encoding type (MP3, FLAC, etc.)")
    vbr: bool = Field(default=False, description="Variable bitrate")

    @property
    def display_name(self) -> str:
        """Generate display name for bitrate/encoding combination."""
        vbr_suffix = " (VBR)" if self.vbr else ""
        return f"{self.encoding} {self.bitrate}{vbr_suffix}"


class Credits(BaseModel):
    """Upload credits and attribution."""

    ripper: str | None = Field(None, description="Original ripper")
    encoder: str | None = Field(None, description="Audio encoder")
    uploader: str | None = Field(None, description="Uploader")

    def to_credits_string(self) -> str:
        """Convert to standard credits format."""
        parts: list[str] = []
        if self.ripper:
            parts.append(f"Ripped by {self.ripper}")
        if self.encoder:
            parts.append(f"Encoded by {self.encoder}")
        if self.uploader and self.uploader != self.encoder:
            parts.append(f"Uploaded by {self.uploader}")
        return " | ".join(parts)


class ReleaseInfo(BaseModel):
    """Basic release information."""

    artist: str = Field(..., description="Artist/Author name")
    title: str = Field(..., description="Release title")
    year: int | None = Field(None, description="Release year")
    label: str | None = Field(None, description="Record label/Publisher")
    catalog_number: str | None = Field(None, description="Catalog number")


class TorrentFile(BaseModel):
    """Torrent file information."""

    file_path: Path = Field(..., description="Path to .torrent file")
    data_path: Path = Field(..., description="Path to actual data directory/file")

    @model_validator(mode="after")
    def validate_paths(self) -> TorrentFile:
        """Validate that paths exist."""
        if not self.file_path.exists():
            raise ValueError(f"Torrent file does not exist: {self.file_path}")
        if not self.data_path.exists():
            raise ValueError(f"Data path does not exist: {self.data_path}")
        return self


class UploadSpec(BaseModel):
    """Complete upload specification."""

    # Core identification
    category: Category = Field(..., description="Upload category")
    release_info: ReleaseInfo = Field(..., description="Basic release information")

    # Technical specs
    bitrate_encoding: BitrateEncoding = Field(..., description="Bitrate and encoding")
    credits: Credits = Field(
        default_factory=Credits, description="Credits and attribution"
    )  # type: ignore[misc]

    # Content
    description: str = Field(..., description="Release description (BBCode)")
    tags: list[str] = Field(default_factory=list, description="Genre tags")

    # Files
    torrent: TorrentFile = Field(..., description="Torrent and data files")

    # Metadata
    extra_fields: dict[str, Any] = Field(
        default_factory=dict, description="Tracker-specific fields"
    )

    @property
    def release_name(self) -> str:
        """Generate standardized release name."""
        year_part = f" ({self.release_info.year})" if self.release_info.year else ""
        return f"{self.release_info.artist} - {self.release_info.title}{year_part}"

    def add_extra_field(self, key: str, value: Any) -> None:
        """Add tracker-specific field."""
        self.extra_fields[key] = value

    def get_extra_field(self, key: str, default: Any = None) -> Any:
        """Get tracker-specific field."""
        return self.extra_fields.get(key, default)


class UploadResult(BaseModel):
    """Result of upload operation."""

    success: bool = Field(..., description="Upload success status")
    tracker_id: str | None = Field(None, description="Tracker-assigned ID")
    url: str | None = Field(None, description="Upload URL")
    message: str = Field(..., description="Result message")
    dry_run: bool = Field(default=False, description="Was this a dry run")
    raw_response: dict[str, Any] = Field(
        default_factory=dict, description="Raw tracker response"
    )
