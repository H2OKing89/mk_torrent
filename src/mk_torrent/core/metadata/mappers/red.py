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

    def map_to_tracker(self, metadata: AudiobookMeta) -> dict[str, Any]:
        """Map AudiobookMeta to RED tracker format (Protocol implementation)."""
        return self.map_to_red_upload(metadata, include_description=True)

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
            "title": f"{metadata.author} - {metadata.title}",  # RED audiobook format: Author - Title
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
        if year:
            # Convert to int if it's a string
            try:
                year_int = int(year) if isinstance(year, str) else year
                if 1800 <= year_int <= 2100:
                    return year_int
            except (ValueError, TypeError):
                pass
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

        # Default to 192 for audiobooks instead of "Other"
        return "192"

    def _map_media(self, metadata: AudiobookMeta) -> str:
        """Map media source to RED format."""
        media = getattr(metadata, "media_source", "web").lower()
        return self.MEDIA_MAPPINGS.get(media, "WEB")

    def _get_bitrate_kbps(self, metadata: AudiobookMeta) -> int:
        """Get bitrate in kbps from metadata, converting from bps if needed."""
        if metadata.bitrate:
            # Convert from bits per second to kilobits per second
            return int(metadata.bitrate / 1000)

        # Fallback to parsing from encoding string if available
        if metadata.encoding:
            encoding_lower = metadata.encoding.lower()
            if "320" in encoding_lower:
                return 320
            elif "256" in encoding_lower:
                return 256
            elif "192" in encoding_lower:
                return 192
            elif "128" in encoding_lower:
                return 128
            elif "64" in encoding_lower:
                return 64

        # Default for audiobooks
        return 64

    def _map_tags(self, metadata: AudiobookMeta) -> list[str]:
        """Map genres and tags to list of strings."""
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

        return clean_tags

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
        # Format publisher properly
        publisher_formatted = self._format_publisher(metadata)

        # Generate Audible URL if we have ASIN
        audible_url = None
        if metadata.asin:
            audible_url = f"https://www.audible.com/pd/{metadata.asin}"

        template_data = {
            "description": {
                "title": metadata.title,
                "subtitle": self._format_subtitle(metadata),
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
                    "publisher": publisher_formatted,
                    "release_date": self._format_date(metadata.year),
                    "copyright_year": getattr(metadata, "copyright_year", None),
                    "genre": self._clean_genres(metadata.genres)
                    if hasattr(metadata, "genres") and metadata.genres
                    else [],
                    "audible_url": audible_url,
                    "identifiers": {
                        "asin": metadata.asin,
                        "isbn10": getattr(metadata, "isbn10", None),
                        "isbn13": getattr(metadata, "isbn13", None),
                        "goodreads_id": getattr(metadata, "goodreads_id", None),
                    },
                    "language": self._clean_language(metadata.language) or "en",
                },
                "chapters": self._map_chapters(metadata),
                "chapter_count": getattr(metadata, "chapter_count", None),
            },
            "release": {
                "container": self._get_container_format(metadata),
                "codec": self._get_codec_with_profile(metadata),
                "codec_profile": self._get_codec_profile(metadata),
                "bitrate_kbps": self._get_bitrate_kbps(metadata),
                "bitrate_mode": metadata.bitrate_mode.lower()
                if metadata.bitrate_mode
                else "cbr",
                "sample_rate_hz": metadata.sample_rate or 44100,
                "channels": metadata.channels or 2,
                "channel_layout": metadata.channel_layout or "stereo",
                "duration_ms": (metadata.duration_sec or 0) * 1000,
                "filesize_bytes": metadata.file_size_bytes or 0,
                "chapters_present": bool(len(metadata.chapters) > 0),
                "chapter_count": len(metadata.chapters) if metadata.chapters else None,
                "artwork_info": self._get_artwork_info(metadata),
                "extras": self._get_extras_info(metadata),
                "encoder": getattr(metadata, "encoder", None),
                "encoder_settings": getattr(metadata, "encoder_settings", None),
                "lineage": self._get_lineage(metadata),
            },
        }

        return template_data

    def _format_publisher(self, metadata: AudiobookMeta) -> str:
        """Format publisher with imprint in parentheses."""
        if not metadata.publisher:
            return ""

        # Check if publisher contains both publisher and imprint
        if "," in metadata.publisher:
            parts = [p.strip() for p in metadata.publisher.split(",")]
            if len(parts) == 2:
                return f"{parts[0]} ({parts[1]})"

        return metadata.publisher

    def _format_subtitle(self, metadata: AudiobookMeta) -> str:
        """Format subtitle in the pattern Series Name (Book X)."""
        if metadata.series and metadata.volume:
            return f"{metadata.series} (Book {metadata.volume})"
        elif metadata.series:
            return f"{metadata.series} (Book 1)"
        else:
            # Fallback to just title if no series
            return metadata.title

    def _clean_genres(self, genres: list[str]) -> list[str]:
        """Clean and format genre list."""
        if not genres:
            return []

        cleaned: list[str] = []
        for genre in genres:
            # Clean up common separators and normalize
            clean_genre = str(genre).strip()
            if clean_genre:
                cleaned.append(clean_genre)

        return cleaned

    def _get_codec_with_profile(self, metadata: AudiobookMeta) -> str:
        """Get codec name with profile information."""
        codec = metadata.format or "AAC"
        codec_upper = codec.upper()

        # Add LC profile for AAC if not specified
        if codec_upper == "AAC":
            return "AAC LC"

        return codec_upper

    def _get_codec_profile(self, metadata: AudiobookMeta) -> str | None:
        """Get codec profile separately (not used in current template)."""
        codec = metadata.format or "AAC"
        if codec.upper() == "AAC":
            return None  # Don't return profile separately to avoid duplication
        return None

    def _get_artwork_info(self, metadata: AudiobookMeta) -> str | None:
        """Get artwork information."""
        if metadata.artwork_url or hasattr(metadata, "artwork_width"):
            width = getattr(metadata, "artwork_width", 2400)
            height = getattr(metadata, "artwork_height", 2400)
            return f"Embedded cover ({width}×{height})"
        return None

    def _get_extras_info(self, metadata: AudiobookMeta) -> str | None:
        """Get extras information."""
        extras: list[str] = []

        # Check for common M4B extras
        if self._get_container_format(metadata) == "M4B":
            extras.append("Embedded Apple text/chapters stream")

        return ", ".join(extras) if extras else None

    def _get_lineage(self, metadata: AudiobookMeta) -> list[str] | None:
        """Get encoding lineage information."""
        lineage_parts: list[str] = []

        # Start with source
        media_source = getattr(metadata, "media_source", "digital").lower()
        if media_source == "digital" or media_source == "web":
            lineage_parts.append("Digital retail source")
        else:
            lineage_parts.append(f"{media_source.title()} source")

        # Add encoding info
        container = self._get_container_format(metadata)
        codec = self._get_codec_with_profile(metadata)
        bitrate_kbps = self._get_bitrate_kbps(metadata)
        bitrate_mode = metadata.bitrate_mode.upper() if metadata.bitrate_mode else "CBR"
        sample_rate = (metadata.sample_rate or 44100) / 1000
        channels = metadata.channel_layout or "stereo"

        encoding_info = f"Packaged as {container} ({codec} {bitrate_mode} ~{bitrate_kbps} kb/s, {sample_rate} kHz, {channels})"

        # Add artwork info if available
        artwork_info = self._get_artwork_info(metadata)
        if artwork_info:
            encoding_info += f". {artwork_info.replace('Embedded cover', 'Chapters and cover embedded')}"
        else:
            encoding_info += ". Chapters embedded" if len(metadata.chapters) > 0 else ""

        # Add extras info
        extras = self._get_extras_info(metadata)
        if extras:
            encoding_info += f"; {extras}"

        lineage_parts.append(encoding_info)

        return lineage_parts

    def _clean_language(self, language: str | None) -> str | None:
        """Clean and normalize language field."""
        if not language:
            return None

        # Clean up common issues
        clean_lang = str(language).strip().lower()

        # Fix common duplications like "englishglish"
        if "englishglish" in clean_lang:
            return "english"
        elif "english" in clean_lang:
            return "english"
        elif clean_lang in ["en", "eng"]:
            return "english"
        elif clean_lang in ["es", "spa", "spanish"]:
            return "spanish"
        elif clean_lang in ["fr", "fra", "french"]:
            return "french"
        elif clean_lang in ["de", "ger", "german"]:
            return "german"
        elif clean_lang in ["it", "ita", "italian"]:
            return "italian"

        return clean_lang

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
        """Map chapter information from actual chapter data."""
        chapters: list[dict[str, Any]] = []

        if metadata.chapters:
            # Use actual chapter data if available
            for i, chapter_data in enumerate(
                metadata.chapters[:20]
            ):  # Limit display to 20
                # Extract start time from chapter data (try both formats)
                start_time = chapter_data.get("startOffsetSec") or chapter_data.get(
                    "start_time", 0
                )
                if isinstance(start_time, (int, float)):
                    # Convert seconds to HH:MM:SS format
                    hours = int(start_time // 3600)
                    minutes = int((start_time % 3600) // 60)
                    seconds = int(start_time % 60)
                    start_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    start_str = f"{i * 30 // 60:02d}:{(i * 30) % 60:02d}:00"  # Fallback

                # Extract title from chapter data
                title = chapter_data.get("title", f"Chapter {i + 1}")

                # Extract or calculate duration (try multiple formats)
                duration_ms = chapter_data.get("lengthMs") or chapter_data.get(
                    "duration", 0
                )
                if (
                    not duration_ms
                    and chapter_data.get("end_time")
                    and chapter_data.get("start_time")
                ):
                    duration_ms = (
                        chapter_data["end_time"] - chapter_data["start_time"]
                    ) * 1000

                chapters.append(
                    {
                        "index": i + 1,
                        "start": start_str,
                        "title": title,
                        "duration_ms": int(duration_ms) if duration_ms else None,
                    }
                )

        return chapters

    def _get_container_format(self, metadata: AudiobookMeta) -> str:
        """Get container format from metadata."""
        # For audiobooks, the container is typically M4B even if format shows AAC
        format_str = metadata.format or "M4B"
        format_upper = format_str.upper()

        # Map codec formats to proper container formats
        if format_upper in ["AAC", "M4A"]:
            return "M4B"  # Audiobooks are typically M4B containers

        return format_upper

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
