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
from typing import Any, Protocol, Union, Literal

BitrateMode = Literal["cbr", "vbr", "abr", "unknown"]


@dataclass
class TechnicalAudio:
    """Technical audio metadata container.

    Captures stream-level technical details with no data loss.
    Provides convenience properties for common conversions.
    """

    # Container & codec
    container: str = ""  # m4b, mp3, flac, mka, m4a...
    codec: str = ""  # aac, mp3, flac, opus...
    profile: str = ""  # LC, HE-AAC, etc (when available)

    # Core signal
    sample_rate: int | None = None  # Hz
    channels: int | None = None  # 1, 2, …
    channel_layout: str = ""  # mono, stereo, 5.1, …

    # Bitrate
    bitrate_bps: int | None = None  # declared bitrate
    bitrate_mode: BitrateMode = "unknown"
    bitrate_variance: float | None = None  # 0.0..1.0, fraction or %
    calculated_bitrate_bps: int | None = None  # derived from size/time

    # Duration & size
    duration_ms: int | None = None
    file_size_bytes: int | None = None
    chapters_present: bool = False

    # Lineage / encoder
    encoder: str = ""  # libfdk_aac, qaac, lame, ffmpeg, …
    encoder_settings: str = ""
    source_type: str = ""  # Web, CD, Digital, Cassette (hey, it happens)
    lineage: list[str] = field(default_factory=list)  # type: ignore[type-arg]  # processing chain steps

    # Keep anything else we haven't modeled yet
    extras: dict[str, Any] = field(default_factory=dict)  # type: ignore[type-arg]

    # Convenience computed properties
    @property
    def bitrate_kbps(self) -> int | None:
        """Get bitrate in kbps from bps."""
        return None if self.bitrate_bps is None else round(self.bitrate_bps / 1000)

    @property
    def calculated_bitrate_kbps(self) -> int | None:
        """Get calculated bitrate in kbps from bps."""
        return (
            None
            if self.calculated_bitrate_bps is None
            else round(self.calculated_bitrate_bps / 1000)
        )

    @property
    def is_lossless(self) -> bool:
        """Check if this is a lossless codec."""
        return self.codec.lower() in {"flac", "alac", "ape", "wav", "aiff"}

    @property
    def is_cbr(self) -> bool:
        """Check if this uses constant bitrate."""
        return self.bitrate_mode == "cbr"

    def runtime_hms(self) -> str:
        """Get runtime in HH:MM:SS format."""
        if not self.duration_ms:
            return "0:00:00"

        total_seconds = int(self.duration_ms // 1000)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}"


@dataclass
class AudiobookMeta:
    """Canonical audiobook metadata container.

    This is the primary data transfer object used throughout the metadata
    system. Uses dataclass for fast, zero-dependency operation with an
    optional pydantic mirror under schemas/ for strict validation.

    ⚠️  FIELD USAGE GUIDELINES ⚠️

    DESCRIPTION FIELD - POST-PROCESSED:
    🔄 description: Canonical text content (merger selects best from API summary/description)
    ✅ Use this field for templates and output - it contains the best available text
    ❌ Do NOT use raw 'summary' field from sources - description is post-processed

    TECHNICAL FIELDS - USE .technical CONTAINER:
    🔧 For audio specs: Use metadata.technical.bitrate_kbps, NOT metadata.encoding
    🔧 For file info: Use metadata.technical.file_size_bytes, NOT legacy fields
    🔧 For timing: Use metadata.technical.duration_ms, NOT duration_sec
    ✅ Always prefer .technical.* fields for accurate technical data

    LEGACY COMPATIBILITY:
    📊 Some legacy fields maintained for backward compatibility
    📊 Technical container is authoritative source
    📊 to_dict() method creates flat mirrors for legacy code
    """

    title: str = ""
    subtitle: str = ""  # Enhanced field for book subtitles
    author: str = ""
    album: str = ""  # default: title
    series: str = ""
    volume: str = ""  # e.g., "08"
    year: int | None = None
    narrator: str = ""
    duration_sec: int | None = None  # Legacy - prefer technical.duration_ms
    format: str = ""  # Legacy - prefer technical.codec
    encoding: str = ""  # Legacy - prefer technical.bitrate_* fields
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
    description: str = (
        ""  # 🔄 POST-PROCESSED: Best text content (summary vs description)
    )
    description_html: str = ""  # Enhanced field for HTML description
    description_text: str = ""  # Enhanced field for plain text description
    genres: list[str] = field(default_factory=list)  # type: ignore[type-arg]
    tags: list[str] = field(default_factory=list)  # type: ignore[type-arg]
    chapters: list[dict[str, Any]] = field(default_factory=list)  # type: ignore[type-arg]
    files: list[Path] = field(default_factory=list)  # type: ignore[type-arg]
    source_path: Path | None = None
    artwork_url: str = ""
    cover_dimensions: dict[str, int] | None = (
        None  # Enhanced field {"width": 600, "height": 800}
    )

    # 🔧 TECHNICAL CONTAINER - AUTHORITATIVE SOURCE FOR TECHNICAL DATA
    technical: TechnicalAudio = field(default_factory=TechnicalAudio)
    extras: dict[str, Any] = field(default_factory=dict)  # type: ignore[type-arg]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        d = asdict(self)
        # Optional: keep a flat mirror of a few popular technicals for legacy code
        d.setdefault("bitrate", self.technical.bitrate_bps)
        d.setdefault("bitrate_mode", self.technical.bitrate_mode)
        d.setdefault("sample_rate", self.technical.sample_rate)
        d.setdefault("channels", self.technical.channels)
        d.setdefault("file_size_bytes", self.technical.file_size_bytes)
        d.setdefault("calculated_bitrate", self.technical.calculated_bitrate_bps)
        d.setdefault("codec", self.technical.codec)
        d.setdefault("container", self.technical.container)
        return d

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        strict: bool = False,
        passthrough_unknowns: bool = True,
    ) -> AudiobookMeta:
        """Lenient by default: never drop unknowns; capture them in .extras."""
        # Normalize path-ish inputs
        files_raw = data.get("files", [])
        files: list[Path] = []
        if isinstance(files_raw, list):
            for f in files_raw:  # type: ignore[misc]
                if f:
                    files.append(Path(f) if isinstance(f, str) else f)  # type: ignore[arg-type]

        source_path = data.get("source_path")
        if isinstance(source_path, str):
            source_path = Path(source_path)

        # Create technical object from both flat and nested inputs
        tech_data = data.get("technical", {})
        if not isinstance(tech_data, dict):
            tech_data = {}

        # Build technical object with safe defaults and type conversion
        duration_sec = data.get("duration_sec")
        duration_ms = data.get("duration_ms")
        if not duration_ms and duration_sec:
            try:
                duration_ms = int(duration_sec) * 1000
            except (TypeError, ValueError):
                duration_ms = None

        bitrate = data.get("bitrate") or data.get("bitrate_bps")
        if bitrate and isinstance(bitrate, str):
            try:
                bitrate = int(bitrate)
            except (ValueError, TypeError):
                bitrate = None

        sample_rate = data.get("sample_rate")
        if sample_rate and isinstance(sample_rate, str):
            try:
                sample_rate = int(sample_rate)
            except (ValueError, TypeError):
                sample_rate = None

        channels = data.get("channels")
        if channels and isinstance(channels, str):
            try:
                channels = int(channels)
            except (ValueError, TypeError):
                channels = None

        file_size_bytes = data.get("file_size_bytes")
        if file_size_bytes and isinstance(file_size_bytes, str):
            try:
                file_size_bytes = int(file_size_bytes)
            except (ValueError, TypeError):
                file_size_bytes = None

        # Normalize bitrate mode to valid literal
        raw_mode = str(data.get("bitrate_mode") or "unknown").lower()
        bitrate_mode: BitrateMode = "unknown"
        if raw_mode in {"cbr", "vbr", "abr"}:
            bitrate_mode = raw_mode  # type: ignore[assignment]

        # Build technical audio object
        tech = TechnicalAudio(
            container=str(
                data.get("container")
                or data.get("format_type")
                or data.get("format")
                or ""
            ),
            codec=str(data.get("codec") or ""),
            profile=str(data.get("profile") or ""),
            sample_rate=sample_rate,
            channels=channels,
            channel_layout=str(data.get("channel_layout") or ""),
            bitrate_bps=bitrate,
            bitrate_mode=bitrate_mode,
            bitrate_variance=data.get("bitrate_variance"),
            calculated_bitrate_bps=data.get("calculated_bitrate")
            or data.get("calculated_bitrate_bps"),
            duration_ms=duration_ms,
            file_size_bytes=file_size_bytes,
            chapters_present=bool(
                data.get("chapters_present", bool(data.get("chapters")))
            ),
            encoder=str(data.get("encoder") or ""),
            encoder_settings=str(data.get("encoder_settings") or ""),
            source_type=str(data.get("source_type") or ""),
            lineage=data.get("lineage", [])
            if isinstance(data.get("lineage"), list)
            else [],
            extras=dict(tech_data) if tech_data else {},  # type: ignore[arg-type]
        )

        # Build top-level fields with explicit types
        known_fields = set(cls.__dataclass_fields__.keys())

        # Get genres safely
        genres_raw = data.get("genres", [])
        if not isinstance(genres_raw, list):
            if isinstance(data.get("genre"), str):
                genres = [str(data["genre"])]
            else:
                genres = []
        else:
            genres = [str(g) for g in genres_raw if g]  # type: ignore[misc]

        # Create the instance directly with explicit typing
        unknown_top = {
            k: v for k, v in data.items() if k not in known_fields and k != "technical"
        }
        extras: dict[str, Any] = {}
        if passthrough_unknowns:
            extras.update(unknown_top)
        elif strict and unknown_top:
            raise ValueError(
                f"Unknown fields in AudiobookMeta: {sorted(unknown_top.keys())}"
            )

        return cls(
            title=str(data.get("title") or ""),
            subtitle=str(data.get("subtitle") or ""),
            author=str(data.get("author") or ""),
            album=str(data.get("album") or data.get("title") or ""),
            series=str(data.get("series") or ""),
            volume=str(data.get("volume") or ""),
            year=data.get("year") if isinstance(data.get("year"), int) else None,
            narrator=str(data.get("narrator") or ""),
            duration_sec=data.get("duration_sec")
            if isinstance(data.get("duration_sec"), int)
            else None,
            format=str(data.get("format") or ""),
            encoding=str(data.get("encoding") or ""),
            asin=str(data.get("asin") or ""),
            isbn=str(data.get("isbn") or ""),
            publisher=str(data.get("publisher") or ""),
            copyright=str(data.get("copyright") or ""),
            release_date=str(data.get("release_date") or ""),
            rating=data.get("rating")
            if isinstance(data.get("rating"), (int, float))
            else None,
            language=str(data.get("language") or "en"),
            region=str(data.get("region") or ""),
            literature_type=str(data.get("literature_type") or ""),
            format_type=str(data.get("format_type") or ""),
            is_adult=data.get("is_adult")
            if isinstance(data.get("is_adult"), bool)
            else None,
            description=str(data.get("description") or ""),
            description_html=str(data.get("description_html") or ""),
            description_text=str(data.get("description_text") or ""),
            genres=genres,
            tags=data.get("tags", []) if isinstance(data.get("tags"), list) else [],
            chapters=data.get("chapters", [])
            if isinstance(data.get("chapters"), list)
            else [],
            files=files,
            source_path=source_path,
            artwork_url=str(data.get("artwork_url") or ""),
            cover_dimensions=data.get("cover_dimensions")
            if isinstance(data.get("cover_dimensions"), dict)
            else None,
            technical=tech,
            extras=extras,
        )


@dataclass
class ValidationResult:
    """Result of metadata validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)  # type: ignore[type-arg]
    warnings: list[str] = field(default_factory=list)  # type: ignore[type-arg]
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
