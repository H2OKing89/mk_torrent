"""
Embedded metadata source using Mutagen for tag extraction.

Extracts metadata from file tags (ID3, MP4, FLAC, etc.) following
the recommended packages specification using Mutagen.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import re

from ..base import AudiobookMeta
from ..exceptions import SourceUnavailable

logger = logging.getLogger(__name__)


class EmbeddedSource:
    """
    Embedded metadata source using Mutagen for tag extraction.

    Extracts audiobook metadata from embedded file tags supporting
    multiple formats: MP3 (ID3), M4A/M4B (MP4), FLAC, OGG, etc.
    """

    # Common tag mappings across formats
    TAG_MAPPINGS = {
        "title": ["TIT2", "TITLE", "\xa9nam"],
        "album": ["TALB", "ALBUM", "\xa9alb"],
        "artist": ["TPE1", "ARTIST", "\xa9ART"],
        "albumartist": ["TPE2", "ALBUMARTIST", "aART"],
        "author": ["TPE1", "ARTIST", "\xa9ART", "TPE2"],  # Author often in artist field
        "narrator": ["TPE3", "CONDUCTOR", "\xa9con"],  # Narrator sometimes in conductor
        "date": ["TDRC", "DATE", "\xa9day"],
        "year": ["TYER", "YEAR", "\xa9day"],
        "genre": ["TCON", "GENRE", "\xa9gen"],
        "comment": ["COMM", "COMMENT", "\xa9cmt"],
        "description": ["COMM", "COMMENT", "\xa9cmt", "desc"],
        "publisher": ["TPUB", "PUBLISHER", "\xa9pub"],
        "track": ["TRCK", "TRACK", "trkn"],
        "disc": ["TPOS", "DISC", "disk"],
        "asin": ["TXXX:ASIN", "ASIN", "----:com.apple.iTunes:ASIN"],
        "isbn": ["TXXX:ISBN", "ISBN", "----:com.apple.iTunes:ISBN"],
        "language": ["TLAN", "LANGUAGE", "\xa9lng"],
        "series": ["TXXX:SERIES", "SERIES", "----:com.apple.iTunes:SERIES"],
        "series_position": [
            "TXXX:SERIES-PART",
            "SERIES-PART",
            "----:com.apple.iTunes:SERIES-PART",
        ],
    }

    def __init__(self, prefer_detailed_tags: bool = True):
        """
        Initialize embedded metadata source.

        Args:
            prefer_detailed_tags: Whether to prefer detailed audiobook-specific tags
        """
        self.prefer_detailed_tags = prefer_detailed_tags
        self._mutagen_available = self._check_mutagen()

    def _check_mutagen(self) -> bool:
        """Check if Mutagen is available."""
        import importlib.util

        if importlib.util.find_spec("mutagen") is not None:
            logger.debug("Mutagen available for embedded metadata extraction")
            return True
        else:
            raise SourceUnavailable(
                "embedded", "Mutagen package required for embedded metadata"
            )

    def extract_metadata(self, file_path: Union[str, Path]) -> AudiobookMeta:
        """
        Extract metadata from audio file tags.

        Args:
            file_path: Path to audio file

        Returns:
            AudiobookMeta object with extracted information
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        if not self._mutagen_available:
            raise SourceUnavailable("embedded", "Mutagen not available")

        try:
            from mutagen._file import File as MutagenFile

            audio_file = MutagenFile(file_path)

            if audio_file is None:
                logger.warning(f"Unable to read metadata from {file_path}")
                return AudiobookMeta()

            # Extract tags into a normalized format
            tags = self._extract_tags(audio_file)

            # Convert to AudiobookMeta
            return self._tags_to_metadata(tags, file_path)

        except Exception as e:
            logger.warning(f"Failed to extract metadata from {file_path}: {e}")
            return AudiobookMeta()

    def _extract_tags(self, audio_file) -> Dict[str, Any]:
        """Extract and normalize tags from audio file."""
        if not audio_file or not hasattr(audio_file, "tags") or not audio_file.tags:
            return {}

        tags = {}
        raw_tags = audio_file.tags

        # Map tags based on format
        for field, tag_keys in self.TAG_MAPPINGS.items():
            value = None

            for tag_key in tag_keys:
                if tag_key in raw_tags:
                    raw_value = raw_tags[tag_key]

                    # Handle different value types
                    if isinstance(raw_value, list) and raw_value:
                        value = str(raw_value[0])
                    elif raw_value:
                        value = str(raw_value)

                    if value and value.strip():
                        break

            if value and value.strip():
                tags[field] = value.strip()

        return tags

    def _tags_to_metadata(self, tags: Dict[str, Any], file_path: Path) -> AudiobookMeta:
        """Convert extracted tags to AudiobookMeta."""
        metadata = AudiobookMeta()

        # Basic information
        metadata.title = tags.get("title", "")
        metadata.album = tags.get("album", metadata.title)  # Default album to title

        # Authors and narrators
        if "author" in tags:
            metadata.author = tags["author"]
        elif "artist" in tags:
            metadata.author = tags["artist"]
        elif "albumartist" in tags:
            metadata.author = tags["albumartist"]

        metadata.narrator = tags.get("narrator", "")

        # Series information
        metadata.series = tags.get("series", "")
        metadata.volume = tags.get("series_position", "")

        # Publication details
        metadata.publisher = tags.get("publisher", "")
        metadata.language = tags.get("language", "en")

        # Date handling
        if "date" in tags:
            parsed_date = self._parse_date(tags["date"])
            if parsed_date:
                metadata.year = parsed_date.year
        elif "year" in tags:
            parsed_date = self._parse_date(tags["year"])
            if parsed_date:
                metadata.year = parsed_date.year

        # Identifiers
        metadata.asin = tags.get("asin", "")
        metadata.isbn = tags.get("isbn", "")

        # Description from comments
        if "description" in tags:
            metadata.description = tags["description"]
        elif "comment" in tags:
            metadata.description = tags["comment"]

        # Genres
        if "genre" in tags:
            # Split multiple genres if separated by common delimiters
            genre_text = tags["genre"]
            genres = re.split(r"[;,/&]", genre_text)
            metadata.genres = [g.strip() for g in genres if g.strip()]

        # Set source path
        metadata.source_path = file_path

        return metadata

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string from tags."""
        if not date_str:
            return None

        # Common date formats in tags
        date_formats = [
            "%Y-%m-%d",  # 2023-05-15
            "%Y-%m",  # 2023-05
            "%Y",  # 2023
            "%d/%m/%Y",  # 15/05/2023
            "%m/%d/%Y",  # 05/15/2023
        ]

        # Clean the date string
        date_str = date_str.strip()

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try to extract just the year
        year_match = re.search(r"\b(19|20)\d{2}\b", date_str)
        if year_match:
            try:
                year = int(year_match.group())
                return datetime(year, 1, 1)
            except ValueError:
                pass

        logger.warning(f"Unable to parse date: {date_str}")
        return None

    def extract_bulk_metadata(self, directory: Union[str, Path]) -> List[AudiobookMeta]:
        """
        Extract metadata from all audio files in a directory.

        Args:
            directory: Path to directory containing audio files

        Returns:
            List of AudiobookMeta objects
        """
        directory = Path(directory)

        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        results = []

        # Common audio extensions
        audio_extensions = {
            ".mp3",
            ".m4a",
            ".m4b",
            ".flac",
            ".ogg",
            ".opus",
            ".wav",
            ".aiff",
            ".ape",
            ".wv",
            ".tta",
        }

        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                try:
                    metadata = self.extract_metadata(file_path)
                    if metadata.title:  # Only include if we found some metadata
                        results.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to extract metadata from {file_path}: {e}")

        return results

    def get_chapter_information(
        self, file_path: Union[str, Path]
    ) -> List[Dict[str, Any]]:
        """
        Extract chapter information from audio file (if available).

        Args:
            file_path: Path to audio file

        Returns:
            List of chapter dictionaries with title, start_time, etc.
        """
        file_path = Path(file_path)

        try:
            from mutagen._file import File as MutagenFile

            audio_file = MutagenFile(file_path)

            if (
                audio_file is None
                or not hasattr(audio_file, "tags")
                or not audio_file.tags
            ):
                return []

            chapters = []

            # Look for chapter information (format-specific)
            if hasattr(audio_file, "info") and hasattr(audio_file.info, "chapters"):
                # Some formats have direct chapter support
                for i, chapter in enumerate(audio_file.info.chapters):
                    chapters.append(
                        {
                            "number": i + 1,
                            "title": getattr(chapter, "title", f"Chapter {i + 1}"),
                            "start_time": getattr(chapter, "start_time", 0),
                            "end_time": getattr(chapter, "end_time", None),
                        }
                    )

            return chapters

        except Exception as e:
            logger.warning(
                f"Failed to extract chapter information from {file_path}: {e}"
            )
            return []
