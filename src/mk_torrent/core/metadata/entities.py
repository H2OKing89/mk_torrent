"""
Rich entity model for comprehensive metadata representation - Core Modular Metadata System.

Part of the new modular metadata architecture providing enhanced type safety
and structured data modeling beyond the basic AudiobookMeta dataclass.

This module defines detailed entity classes that provide enhanced type safety
and structured data modeling beyond the basic AudiobookMeta dataclass.
These entities represent the future comprehensive model outlined in Document #04.

Architecture Documentation:
- Entity Design: docs/core/metadata/04 — Comprehensive Entity Model.md
- Protocol Design: docs/core/metadata/05 — Protocol & Entity Design.md
- Base Architecture: docs/core/metadata/03 — Foundation Architecture.md
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
from datetime import date, datetime


@dataclass
class PersonRef:
    """Reference to a person (author, narrator, etc.)."""

    name: str
    asin: str | None = None  # Audnexus author ASIN when present
    role: str = ""  # "author", "narrator"


@dataclass
class GenreTag:
    """Genre or tag classification."""

    name: str
    type: str = "genre"  # "genre" | "tag" (Audnexus); others allowed
    asin: str | None = None


@dataclass
class SeriesRef:
    """Series information with position tracking."""

    name: str = ""
    position_str: str = ""  # e.g. "3"
    position_num: float | None = None  # 3.0, 3.5 if needed
    asin: str | None = None


@dataclass
class Chapter:
    """Chapter information with timing."""

    index: int
    title: str
    start_ms: int  # milliseconds from 00:00:00.000
    kind: str = "chapter"  # "chapter" | "intermission" | "credits" | "extra"


@dataclass
class ImageAsset:
    """Image asset (cover art, embedded images, etc.)."""

    url: str = ""  # remote art (Audnexus)
    embedded: bool = False
    width: int | None = None
    height: int | None = None
    format: str = ""  # "JPEG" etc.
    size_bytes: int | None = None


@dataclass
class AudioStream:
    """Audio stream technical information."""

    codec: str = ""  # "AAC", "FLAC", "MP3"
    profile: str = ""  # "LC" etc.
    bitrate_bps: int | None = None
    bitrate_mode: str = ""  # "CBR" | "VBR"
    channels: int | None = None
    layout: str = ""  # "L R"
    sample_rate_hz: int | None = None
    duration_sec: float | None = None
    compression: str = ""  # "Lossy" | "Lossless"


@dataclass
class FileRef:
    """File reference with metadata."""

    path: Path
    size_bytes: int | None = None
    container: str = ""  # "MPEG-4"
    extension: str = ""  # "m4b"


@dataclass
class Provenance:
    """Data source provenance tracking."""

    source: str  # "mediainfo" | "audnexus" | "pathinfo"
    fetched_at: datetime | None = None
    version: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AudiobookMetaRich:
    """
    Comprehensive audiobook metadata container with rich entities.

    This is the enhanced version of AudiobookMeta that uses structured
    entities for better type safety and data modeling. This represents
    the future direction for the metadata system.
    """

    # Identity & naming
    title: str = ""
    subtitle: str = ""  # Often available from Audnexus/embedded
    series: SeriesRef = field(default_factory=SeriesRef)
    volume: str = ""  # zero-padded (e.g., "03")

    # People
    author_primary: str = ""  # convenience field
    narrator_primary: str = ""  # convenience field
    authors: list[PersonRef] = field(default_factory=list)
    narrators: list[PersonRef] = field(default_factory=list)

    # Publishing & identification
    asin: str = ""
    isbn: str = ""
    publisher: str = ""
    copyright: str = ""  # NEW: Copyright information
    release_date: date | None = None  # NEW: Full release date
    year: int | None = None

    # Content classification
    language: str = "en"  # ISO-639-1 where possible
    region: str = ""  # "us" etc.
    literature_type: str = ""  # "fiction"|"nonfiction"|...
    format_type: str = ""  # "unabridged"|"abridged"
    is_adult: bool | None = None
    rating: float | None = None  # 0.0 to 5.0 scale

    # Time & runtime
    runtime_min: int | None = None  # remote (Audnexus)
    duration_sec: int | None = None  # embedded (file trumps remote)

    # Description & topics
    description_html: str = ""  # raw HTML
    description_text: str = ""  # sanitized/plain text
    genres: list[GenreTag] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # Media & structure
    cover: ImageAsset = field(default_factory=ImageAsset)
    images: list[ImageAsset] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)
    audio: AudioStream = field(default_factory=AudioStream)

    # Files & paths
    files: list[FileRef] = field(default_factory=list)
    source_path: Path | None = None  # the "main" file's path

    # Derived for pipeline consumers (slugging, compliance, UI)
    display_title: str = ""  # e.g., "How a Realist Hero… — vol_03"
    safe_slug: str = ""  # ASCII safe; tracker/FS compliant
    artwork_url: str = ""  # kept for convenience

    # Provenance (keep originals for troubleshooting)
    provenance: list[Provenance] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AudiobookMetaRich:
        """Create instance from dictionary data."""
        # Handle cover_dimensions BEFORE filtering (it's not a dataclass field)
        cover_dimensions = data.get("cover_dimensions", None)

        # Filter out unknown fields and convert complex objects
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}

        # Convert string paths back to Path objects
        if "source_path" in valid_fields and isinstance(
            valid_fields["source_path"], str
        ):
            valid_fields["source_path"] = Path(valid_fields["source_path"])

        # Convert release_date string to date object
        if "release_date" in valid_fields and isinstance(
            valid_fields["release_date"], str
        ):
            try:
                if valid_fields["release_date"]:
                    from datetime import datetime

                    parsed_date = datetime.fromisoformat(
                        valid_fields["release_date"]
                    ).date()
                    valid_fields["release_date"] = parsed_date
                else:
                    valid_fields["release_date"] = None
            except (ValueError, TypeError):
                valid_fields["release_date"] = None

        # Handle cover_dimensions BEFORE processing cover field
        # (cover_dimensions was extracted earlier, before filtering)

        # Convert nested objects if they're dicts
        if "series" in valid_fields and isinstance(valid_fields["series"], dict):
            valid_fields["series"] = SeriesRef(**valid_fields["series"])

        if "cover" in valid_fields and isinstance(valid_fields["cover"], dict):
            valid_fields["cover"] = ImageAsset(**valid_fields["cover"])

        # Apply cover_dimensions if present
        if cover_dimensions and isinstance(cover_dimensions, dict):
            if "cover" not in valid_fields or not valid_fields["cover"]:
                valid_fields["cover"] = ImageAsset(
                    width=cover_dimensions.get("width"),
                    height=cover_dimensions.get("height"),
                )
            else:
                # Update existing cover with dimensions
                existing_cover = valid_fields["cover"]
                valid_fields["cover"] = ImageAsset(
                    url=existing_cover.url if hasattr(existing_cover, "url") else "",
                    embedded=(
                        existing_cover.embedded
                        if hasattr(existing_cover, "embedded")
                        else False
                    ),
                    width=cover_dimensions.get("width"),
                    height=cover_dimensions.get("height"),
                    format=(
                        existing_cover.format
                        if hasattr(existing_cover, "format")
                        else ""
                    ),
                    size_bytes=(
                        existing_cover.size_bytes
                        if hasattr(existing_cover, "size_bytes")
                        else None
                    ),
                )

        if "files" in valid_fields:
            files = []
            for f in valid_fields["files"]:
                if isinstance(f, dict):
                    files.append(FileRef(**f))
                elif isinstance(f, FileRef):
                    files.append(f)
                else:
                    files.append(FileRef(path=Path(f)))
            valid_fields["files"] = files

        if "audio" in valid_fields and isinstance(valid_fields["audio"], dict):
            valid_fields["audio"] = AudioStream(**valid_fields["audio"])

        # Convert lists of entities
        if "authors" in valid_fields:
            authors = []
            for author_data in valid_fields["authors"]:
                if isinstance(author_data, dict):
                    authors.append(PersonRef(**author_data))
                elif isinstance(author_data, PersonRef):
                    authors.append(author_data)
            valid_fields["authors"] = authors

        if "narrators" in valid_fields:
            narrators = []
            for narrator_data in valid_fields["narrators"]:
                if isinstance(narrator_data, dict):
                    narrators.append(PersonRef(**narrator_data))
                elif isinstance(narrator_data, PersonRef):
                    narrators.append(narrator_data)
            valid_fields["narrators"] = narrators

        if "genres" in valid_fields:
            genres = []
            for genre_data in valid_fields["genres"]:
                if isinstance(genre_data, dict):
                    genres.append(GenreTag(**genre_data))
                elif isinstance(genre_data, GenreTag):
                    genres.append(genre_data)
            valid_fields["genres"] = genres

        if "chapters" in valid_fields:
            chapters = []
            for chapter_data in valid_fields["chapters"]:
                if isinstance(chapter_data, dict):
                    chapters.append(Chapter(**chapter_data))
                elif isinstance(chapter_data, Chapter):
                    chapters.append(chapter_data)
            valid_fields["chapters"] = chapters

        return cls(**valid_fields)

    def to_simple_audiobook_meta(self) -> dict[str, Any]:
        """Convert to simple AudiobookMeta format for backward compatibility."""

        # Extract cover dimensions from cover image asset
        cover_dimensions = None
        if self.cover and self.cover.width and self.cover.height:
            cover_dimensions = {"width": self.cover.width, "height": self.cover.height}

        # Convert release_date to string format
        release_date = None
        if self.release_date:
            if hasattr(self.release_date, "isoformat"):
                release_date = self.release_date.isoformat()
            else:
                release_date = str(self.release_date)

        # Extract simple fields from rich entities
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "author": self.author_primary,
            "album": self.title,  # default: title
            "series": self.series.name if self.series else "",
            "volume": self.volume,
            "year": self.year,
            "release_date": release_date,
            "publisher": self.publisher,
            "copyright": self.copyright,
            "narrator": self.narrator_primary,
            "duration_sec": self.duration_sec,
            "format": self.audio.codec if self.audio else "",
            "encoding": (
                f"{self.audio.bitrate_mode}@{self.audio.bitrate_bps}"
                if self.audio and self.audio.bitrate_bps
                else ""
            ),
            "asin": self.asin,
            "isbn": self.isbn,
            "language": self.language,
            "description": self.description_text,
            "rating": self.rating,
            "genres": [g.name for g in self.genres],
            "tags": self.tags,
            "chapters": [
                {
                    "index": c.index,
                    "title": c.title,
                    "start_ms": c.start_ms,
                    "kind": c.kind,
                }
                for c in self.chapters
            ],
            "files": [f.path for f in self.files],
            "source_path": self.source_path,
            "artwork_url": self.cover.url if self.cover else "",
            "cover_dimensions": cover_dimensions,
        }
