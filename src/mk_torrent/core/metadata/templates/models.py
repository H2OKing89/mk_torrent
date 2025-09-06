"""
Template data models for BBCode description generation.

These Pydantic models provide type safety and validation for template rendering,
ensuring consistent and well-formatted descriptions across different trackers.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    field_validator,
    ValidationInfo,
    ConfigDict,
)
import re

if TYPE_CHECKING:
    pass


class Series(BaseModel):
    """Book series information."""

    name: str = Field(..., min_length=1, description="Series name")
    number: str = Field(
        ..., description="Volume number, can be '1', '0.5', 'Omnibus', etc."
    )


class Identifiers(BaseModel):
    """Book identifiers and catalog numbers."""

    asin: str | None = None
    isbn10: str | None = None
    isbn13: str | None = None
    goodreads_id: str | None = None

    @field_validator("isbn10")
    @classmethod
    def validate_isbn10(cls, v: str | None) -> str | None:
        if v and not re.match(r"^\d{9}[\dX]$", v.replace("-", "")):
            raise ValueError("Invalid ISBN-10 format")
        return v

    @field_validator("isbn13")
    @classmethod
    def validate_isbn13(cls, v: str | None) -> str | None:
        if v and not re.match(r"^\d{13}$", v.replace("-", "")):
            raise ValueError("Invalid ISBN-13 format")
        return v


class BookInfo(BaseModel):
    """Core book metadata for template rendering."""

    authors: list[str] = Field(default_factory=list, min_length=1)
    narrators: list[str] = Field(default_factory=list)
    publisher: str = ""
    release_date: str | None = Field(None, pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$")
    genre: list[str] = Field(default_factory=list)
    audible_url: HttpUrl | None = None
    identifiers: Identifiers = Field(default_factory=Identifiers)
    language: str = Field(default="en", min_length=2, max_length=5)
    copyright_year: int | None = Field(None, ge=1800, le=2100)


class Chapter(BaseModel):
    """Chapter information for detailed listings."""

    index: int = Field(..., ge=1)
    start: str = Field(
        ...,
        pattern=r"^\d{1,2}:\d{2}:\d{2}$",
        description="Timestamp in HH:MM:SS format",
    )
    title: str
    duration_ms: int | None = Field(
        None, ge=0, description="Chapter duration in milliseconds"
    )


class Release(BaseModel):
    """Technical release information."""

    container: str = Field(..., description="File container format (M4B, MP3, etc.)")
    codec: str = Field(..., description="Audio codec (AAC, MP3, FLAC, etc.)")
    bitrate_kbps: int = Field(..., ge=8, le=2000, description="Bitrate in kbps")
    bitrate_mode: str = Field(default="cbr", pattern=r"^(vbr|cbr)$")
    sample_rate_hz: int = Field(
        ..., ge=8000, le=192000, description="Sample rate in Hz"
    )
    channels: int = Field(..., ge=1, le=8, description="Number of audio channels")
    channel_layout: str | None = Field(
        None, description="Channel layout (stereo, mono, etc.)"
    )
    duration_ms: int = Field(..., ge=0, description="Total duration in milliseconds")
    filesize_bytes: int = Field(..., ge=0, description="Total file size in bytes")
    chapters_present: bool = Field(
        default=False, description="Whether file contains chapter markers"
    )

    # Encoding lineage and source info
    encoder: str | None = Field(
        None, description="Encoder used (libfdk_aac, lame, etc.)"
    )
    encoder_settings: str | None = Field(
        None, description="Encoding settings/parameters"
    )
    source_type: str | None = Field(
        None, description="Source type (CD, Digital, Web, etc.)"
    )
    lineage: list[str] = Field(
        default_factory=list, description="Processing chain steps"
    )


class Description(BaseModel):
    """Complete description template data model."""

    title: str = Field(..., min_length=1)
    subtitle: str | None = None
    series: list[Series] = Field(default_factory=list)  # type: ignore[name-defined]
    summary: list[str] = Field(default_factory=list, description="Summary paragraphs")
    narration_notes: str | None = Field(
        None, description="Notes about narration quality/style"
    )
    book_info: BookInfo
    chapters: list[Chapter] = Field(default_factory=list)  # type: ignore[name-defined]
    chapter_count: int | None = Field(
        None, ge=0, description="Total number of chapters"
    )

    @field_validator("chapter_count")
    @classmethod
    def validate_chapter_count(cls, v: int | None, info: ValidationInfo) -> int | None:
        if v is not None and info.data and "chapters" in info.data:
            actual_count = len(info.data["chapters"])
            if v != actual_count and actual_count > 0:
                # Auto-correct to actual chapter count if chapters are provided
                return actual_count
        return v

    def model_post_init(self, __context: None) -> None:
        """Auto-set chapter_count if not provided but chapters exist."""
        if self.chapter_count is None and self.chapters:
            self.chapter_count = len(self.chapters)


class TemplateData(BaseModel):
    """Root template data containing all sections."""

    description: Description
    release: Release

    model_config = ConfigDict(
        extra="forbid",  # Prevent accidental extra fields
        validate_assignment=True,  # Validate on assignment
        str_strip_whitespace=True,  # Auto-strip whitespace
    )
