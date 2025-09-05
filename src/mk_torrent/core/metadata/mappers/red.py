"""
RED Tracker metadata mapper.

Converts AudiobookMeta to RED upload fields with detailed BBCode descriptions
using the template system.
"""

from __future__ import annotations
from typing import Any
from pathlib import Path
import logging

from ..base import AudiobookMeta

# Import template system with fallback
templates_available = False
TemplateRenderer = None

try:
    from ..templates import TemplateRenderer

    templates_available = True
except ImportError:
    logging.warning("Template system not available - descriptions will be basic")


logger = logging.getLogger(__name__)


class REDMapper:
    """Maps AudiobookMeta to RED tracker upload format."""

    # RED tracker field mappings
    CATEGORY_AUDIOBOOKS = 3
    RELEASE_TYPE_AUDIOBOOK = 1  # Album type for audiobooks

    # Format mappings (RED format field)
    FORMAT_MAPPINGS = {
        "mp3": "MP3",
        "m4a": "AAC",
        "m4b": "AAC",
        "aac": "AAC",
        "flac": "FLAC",
        "ogg": "Vorbis",
        "opus": "Opus",
    }

    # Bitrate mappings for RED bitrate field
    BITRATE_MAPPINGS = {
        # VBR mappings
        "v0": "V0 (VBR)",
        "v1": "V1 (VBR)",
        "v2": "V2 (VBR)",
        "aps": "APS (VBR)",
        "apx": "APX (VBR)",
        # CBR mappings
        "128": "128",
        "192": "192",
        "256": "256",
        "320": "320",
        # Lossless
        "lossless": "Lossless",
        "24bit": "24bit Lossless",
    }

    # Media mappings
    MEDIA_MAPPINGS = {
        "cd": "CD",
        "digital": "WEB",
        "web": "WEB",
        "vinyl": "Vinyl",
        "cassette": "Cassette",
        "dat": "DAT",
    }

    def __init__(self, template_dir: Path | None = None):
        """
        Initialize RED mapper.

        Args:
            template_dir: Optional custom template directory
        """
        self.template_renderer = None
        if templates_available and TemplateRenderer:
            self.template_renderer = TemplateRenderer(template_dir)

    def map_to_red_upload(
        self, metadata: AudiobookMeta, include_description: bool = True
    ) -> dict[str, Any]:
        """
        Convert AudiobookMeta to RED upload fields.

        Args:
            metadata: Audiobook metadata to convert
            include_description: Whether to generate detailed BBCode description

        Returns:
            Dictionary of RED upload fields
        """
        logger.debug(f"Mapping metadata for '{metadata.title}' to RED format")

        # Required fields
        upload_data = {
            "type": self.CATEGORY_AUDIOBOOKS,
            "artists[]": self._map_authors(metadata),
            "title": metadata.album or metadata.title,
            "year": self._map_year(metadata),
            "releasetype": self.RELEASE_TYPE_AUDIOBOOK,
            "format": self._map_format(metadata),
            "bitrate": self._map_bitrate(metadata),
            "media": self._map_media(metadata),
            "tags": self._map_tags(metadata),
        }

        # Optional fields
        if metadata.description and include_description:
            if self.template_renderer:
                upload_data["album_desc"] = self._generate_detailed_description(
                    metadata
                )
            else:
                upload_data["album_desc"] = self._generate_basic_description(metadata)

        if metadata.description:
            upload_data["release_desc"] = self._clean_html(metadata.description)

        # Image/artwork
        if metadata.artwork_url:
            upload_data["image"] = str(metadata.artwork_url)

        # Edition/remaster info - using available fields
        # Note: RED remaster fields map to enhanced edition info when available
        if metadata.publisher:
            upload_data["remaster_record_label"] = metadata.publisher

        logger.debug(f"Mapped {len(upload_data)} fields for RED upload")
        return upload_data

    def _map_authors(self, metadata: AudiobookMeta) -> list[str]:
        """Map authors to RED artists array."""
        if metadata.author:
            if isinstance(metadata.author, list):
                return metadata.author
            return [metadata.author]
        return ["Unknown Author"]

    def _map_year(self, metadata: AudiobookMeta) -> int:
        """Map year, ensuring it's valid."""
        year = metadata.year
        if year and 1800 <= year <= 2100:
            return year
        return 2024  # Default fallback

    def _map_format(self, metadata: AudiobookMeta) -> str:
        """Map audio format to RED format field."""
        if not metadata.format:
            return "AAC"  # Default for audiobooks

        format_lower = metadata.format.lower()
        return self.FORMAT_MAPPINGS.get(format_lower, metadata.format.upper())

    def _map_bitrate(self, metadata: AudiobookMeta) -> str:
        """Map bitrate information to RED bitrate field."""
        # AudiobookMeta uses 'encoding' field for bitrate info
        encoding = metadata.encoding
        if not encoding:
            return "Other"

        # Handle common encoding patterns
        encoding_lower = encoding.lower()

        # Try direct mapping first
        if encoding_lower in self.BITRATE_MAPPINGS:
            return self.BITRATE_MAPPINGS[encoding_lower]

        # Pattern matching for common formats
        if "vbr" in encoding_lower or "v0" in encoding_lower:
            return "V0 (VBR)"
        elif "v1" in encoding_lower:
            return "V1 (VBR)"
        elif "v2" in encoding_lower:
            return "V2 (VBR)"
        elif "320" in encoding_lower:
            return "320"
        elif "256" in encoding_lower:
            return "256"
        elif "192" in encoding_lower:
            return "192"
        elif "lossless" in encoding_lower or "flac" in encoding_lower:
            return "Lossless"

        return "Other"

    def _map_media(self, metadata: AudiobookMeta) -> str:
        """Map media source to RED media field."""
        media = getattr(metadata, "media_source", "web")
        if not media:
            return "WEB"

        media_lower = media.lower()
        return self.MEDIA_MAPPINGS.get(media_lower, "WEB")

    def _map_tags(self, metadata: AudiobookMeta) -> str:
        """Map genres and tags to comma-separated string."""
        tags: list[str] = []

        # Add genres
        if metadata.genres:
            tags.extend(metadata.genres)

        # Add additional tags
        if metadata.tags:
            tags.extend(metadata.tags)

        # Add audiobook tag
        if "audiobook" not in [t.lower() for t in tags]:
            tags.append("audiobook")

        # Clean and deduplicate
        clean_tags: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            clean_tag = str(tag).strip().lower()
            if clean_tag and clean_tag not in seen:
                clean_tags.append(str(tag).strip())
                seen.add(clean_tag)

        return ", ".join(clean_tags)

    def _generate_detailed_description(self, metadata: AudiobookMeta) -> str:
        """Generate detailed BBCode description using templates."""
        if not self.template_renderer:
            return self._generate_basic_description(metadata)

        try:
            # Build template data structure
            template_data = self._build_template_data(metadata)

            # Render using templates
            return self.template_renderer.render_description(template_data)

        except Exception as e:
            logger.warning(
                f"Template rendering failed: {e}, falling back to basic description"
            )
            return self._generate_basic_description(metadata)

    def _generate_basic_description(self, metadata: AudiobookMeta) -> str:
        """Generate basic description when templates aren't available."""
        lines: list[str] = []

        lines.append(f"[b]{metadata.title}[/b]")

        if metadata.author:
            authors = (
                metadata.author
                if isinstance(metadata.author, list)
                else [metadata.author]
            )
            lines.append(f"[b]Author(s):[/b] {', '.join(authors)}")

        if metadata.narrator:
            narrators = (
                metadata.narrator
                if isinstance(metadata.narrator, list)
                else [metadata.narrator]
            )
            lines.append(f"[b]Narrator(s):[/b] {', '.join(narrators)}")

        if metadata.year:
            lines.append(f"[b]Year:[/b] {metadata.year}")

        if metadata.publisher:
            lines.append(f"[b]Publisher:[/b] {metadata.publisher}")

        if metadata.description:
            lines.append("")
            lines.append("[b]Description[/b]")
            lines.append(self._clean_html(metadata.description))

        if metadata.duration_sec:
            duration_str = self._format_duration(metadata.duration_sec * 1000)
            lines.append(f"[b]Duration:[/b] {duration_str}")

        return "\n".join(lines)

    def _build_template_data(self, metadata: AudiobookMeta) -> dict[str, Any]:
        """Build template data structure from AudiobookMeta."""
        # This is a simplified mapping - in practice you'd want more comprehensive mapping
        template_data = {
            "description": {
                "title": metadata.title,
                "subtitle": getattr(metadata, "subtitle", None),
                "series": self._map_series(metadata),
                "summary": self._split_summary(metadata.description or ""),
                "narration_notes": getattr(metadata, "narration_notes", None),
                "book_info": {
                    "authors": metadata.author
                    if isinstance(metadata.author, list)
                    else [metadata.author]
                    if metadata.author
                    else [],
                    "narrators": metadata.narrator
                    if isinstance(metadata.narrator, list)
                    else [metadata.narrator]
                    if metadata.narrator
                    else [],
                    "publisher": metadata.publisher or "",
                    "release_date": self._format_date(metadata.year),
                    "copyright_year": getattr(metadata, "copyright_year", None),
                    "genre": metadata.genres
                    if hasattr(metadata, "genres") and metadata.genres
                    else [],
                    "audible_url": getattr(metadata, "audible_url", None),
                    "identifiers": {
                        "asin": metadata.asin,
                        "isbn10": getattr(metadata, "isbn10", None),
                        "isbn13": getattr(metadata, "isbn13", None),
                        "goodreads_id": getattr(metadata, "goodreads_id", None),
                    },
                    "language": metadata.language or "en",
                },
                "chapters": self._map_chapters(metadata),
                "chapter_count": getattr(metadata, "chapter_count", None),
            },
            "release": {
                "container": self._get_container_format(metadata),
                "codec": metadata.format or "AAC",
                "bitrate_kbps": 64,  # Default for audiobooks
                "bitrate_mode": getattr(metadata, "bitrate_mode", "cbr"),
                "sample_rate_hz": getattr(metadata, "sample_rate_hz", 44100),
                "channels": getattr(metadata, "channels", 2),
                "channel_layout": getattr(metadata, "channel_layout", "stereo"),
                "duration_ms": (metadata.duration_sec or 0) * 1000,
                "filesize_bytes": getattr(metadata, "filesize_bytes", 0),
                "chapters_present": bool(getattr(metadata, "chapter_count", 0) > 0),
                "encoder": getattr(metadata, "encoder", None),
                "encoder_settings": getattr(metadata, "encoder_settings", None),
                "source_type": getattr(metadata, "media_source", "Digital"),
                "lineage": getattr(metadata, "lineage", ["Digital Release"]),
            },
        }

        return template_data

    def _map_series(self, metadata: AudiobookMeta) -> list[dict[str, Any]]:
        """Map series information."""
        series_list: list[dict[str, Any]] = []
        if metadata.series:
            series_list.append(
                {"name": metadata.series, "number": str(metadata.volume or 1)}
            )
        return series_list

    def _split_summary(self, text: str) -> list[str]:
        """Split summary into paragraphs."""
        if not text:
            return []

        # Clean HTML first
        clean_text = self._clean_html(text)

        # Split into paragraphs
        paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
        return paragraphs or [clean_text] if clean_text else []

    def _format_date(self, year: int | None) -> str | None:
        """Format year as date string."""
        return str(year) if year else None

    def _map_chapters(self, metadata: AudiobookMeta) -> list[dict[str, Any]]:
        """Map chapter information."""
        # This would need to be enhanced based on your actual chapter data structure
        chapters: list[dict[str, Any]] = []
        chapter_count = getattr(metadata, "chapter_count", 0)

        if chapter_count and chapter_count > 0:
            # Generate placeholder chapters if we don't have detailed chapter info
            for i in range(min(chapter_count, 20)):  # Limit display
                chapters.append(
                    {
                        "index": i + 1,
                        "start": f"{i * 30 // 60:02d}:{(i * 30) % 60:02d}:00",  # Placeholder timestamps
                        "title": f"Chapter {i + 1}",
                        "duration_ms": 30 * 60 * 1000,  # 30 min placeholder
                    }
                )

        return chapters

    def _get_container_format(self, metadata: AudiobookMeta) -> str:
        """Get container format from metadata."""
        format_str = metadata.format or "M4B"
        return format_str.upper()

    def _format_duration(self, duration_ms: int) -> str:
        """Format duration for display."""
        if duration_ms <= 0:
            return "0:00:00"

        total_seconds = int(duration_ms // 1000)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return f"{hours}:{minutes:02d}:{seconds:02d}"

    def _clean_html(self, text: str) -> str:
        """Clean HTML tags from text."""
        if not text:
            return ""

        # Simple HTML cleaning - could be enhanced with nh3
        import re

        clean_text = re.sub(r"<[^>]+>", "", text)
        clean_text = re.sub(r"\s+", " ", clean_text)
        return clean_text.strip()


# Convenience function for direct mapping
def map_audiobook_to_red(
    metadata: AudiobookMeta,
    template_dir: Path | None = None,
    include_description: bool = True,
) -> dict[str, Any]:
    """
    Convenience function to map audiobook metadata to RED format.

    Args:
        metadata: Audiobook metadata to convert
        template_dir: Optional custom template directory
        include_description: Whether to generate detailed description

    Returns:
        Dictionary of RED upload fields
    """
    mapper = REDMapper(template_dir)
    return mapper.map_to_red_upload(metadata, include_description)
