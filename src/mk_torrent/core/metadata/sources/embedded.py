"""
Embedded metadata source - Core Modular Metadata System (Technical Focus).

Part of the new modular metadata architecture providing precise technical file
properties as one of three sources in the intelligent merging strategy. Focuses
exclusively on reliable technical data, avoiding inconsistent descriptive tags.

Extracts technical file properties (duration, bitrate, codec, chapters) using
ffprobe (preferred) or mutagen (fallback). Avoids unreliable descriptive tags.

Architecture Documentation:
- Source Specification: docs/core/metadata/07.6 — Embedded Source (Technical Focus).md
- Three-Source Strategy: docs/core/metadata/06 — Engine Pipeline.md
- Services Overview: docs/core/metadata/07 — Services Details.md (Section 7.6)
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Type aliases for untyped third-party libraries
MutagenFile = Any  # mutagen._file.File
FfprobeData = dict[str, Any]  # ffprobe JSON output structure


class EmbeddedSource:
    """
    Technical metadata extraction from audio files.

    Focuses exclusively on reliable technical properties:
    - File size, duration, bitrate, codec details
    - Chapter information and timing
    - Cover art detection and dimensions

    Avoids descriptive metadata (title, author, series) which varies
    wildly between encoders and is better handled by path + API sources.
    """

    def __init__(self, prefer_ffprobe: bool = True, require_tools: bool = False):
        """
        Initialize embedded metadata source.

        Args:
            prefer_ffprobe: Use ffprobe when available (more accurate)
            require_tools: Raise exception if no tools available
        """
        self.prefer_ffprobe = prefer_ffprobe
        self.require_tools = require_tools

        # Check tool availability
        self.ffprobe_available = self._check_ffprobe()
        self.mutagen_available = self._check_mutagen()

        if require_tools and not (self.ffprobe_available or self.mutagen_available):
            raise RuntimeError(
                "No embedded metadata tools available (ffprobe or mutagen)"
            )

    def _check_ffprobe(self) -> bool:
        """Check if ffprobe is available."""
        try:
            result = subprocess.run(
                ["ffprobe", "-version"], capture_output=True, timeout=5, check=False
            )
            available = result.returncode == 0
            if available:
                logger.debug("ffprobe available for embedded metadata extraction")
            return available
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def _check_mutagen(self) -> bool:
        """Check if mutagen is available."""
        import importlib.util

        if importlib.util.find_spec("mutagen") is not None:
            logger.debug("mutagen available for embedded metadata extraction")
            return True
        else:
            return False

    def extract(self, source: Path | str) -> dict[str, Any]:
        """
        Extract technical metadata from audio file.

        Args:
            source: Path to audio file

        Returns:
            Dict with technical metadata and "_src": "embedded"
        """
        file_path = Path(source)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return {"_src": "embedded", "source": "file_not_found"}

        # Try extraction methods in order of preference
        if self.prefer_ffprobe and self.ffprobe_available:
            try:
                result = self._extract_with_ffprobe(file_path)
                result["source"] = "ffprobe"
                return result
            except Exception as e:
                logger.warning(f"ffprobe extraction failed for {file_path}: {e}")

        if self.mutagen_available:
            try:
                result = self._extract_with_mutagen(file_path)
                result["source"] = "mutagen"
                return result
            except Exception as e:
                logger.warning(f"mutagen extraction failed for {file_path}: {e}")

        # Fallback to basic file info
        logger.info(f"Using basic file info for {file_path} (no tools available)")
        result = self._basic_file_info(file_path)
        result["source"] = "basic"
        return result

    def _extract_with_ffprobe(self, file_path: Path) -> dict[str, Any]:
        """Extract technical metadata using ffprobe."""
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            str(file_path),
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, check=True
            )

            data = json.loads(result.stdout)
            return self._normalize_ffprobe_data(data, file_path)

        except subprocess.CalledProcessError as e:
            logger.error(f"ffprobe failed with return code {e.returncode}: {e.stderr}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ffprobe JSON output: {e}")
            raise
        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe timed out processing {file_path}")
            raise

    def _extract_with_mutagen(self, file_path: Path) -> dict[str, Any]:
        """Extract technical metadata using mutagen."""
        try:
            from mutagen._file import File as MutagenFileModule  # type: ignore

            audio_file = MutagenFileModule(file_path)  # type: ignore
            if audio_file is None:
                raise ValueError(f"mutagen could not read file: {file_path}")

            return self._normalize_mutagen_data(audio_file, file_path)

        except ImportError:
            raise RuntimeError("mutagen not available")

    def _normalize_ffprobe_data(
        self, data: FfprobeData, file_path: Path
    ) -> dict[str, Any]:
        """Normalize ffprobe output to internal format."""
        result: dict[str, Any] = {"_src": "embedded"}

        # Get format information
        format_info: dict[str, Any] = data.get("format", {})

        # File size
        file_size: Any = format_info.get("size")
        if file_size:
            result["file_size_bytes"] = int(file_size)
            result["file_size_mb"] = round(int(file_size) / (1024 * 1024), 1)

        # Duration (prefer format duration as it's most reliable)
        duration: Any = format_info.get("duration")
        if duration:
            result["duration_sec"] = int(float(duration))

        # Audio stream information
        audio_streams: list[dict[str, Any]] = [
            s for s in data.get("streams", []) if s.get("codec_type") == "audio"
        ]
        if audio_streams:
            stream: dict[str, Any] = audio_streams[0]  # Use first audio stream

            # Codec information
            result["codec"] = stream.get("codec_name", "")
            result["codec_long_name"] = stream.get("codec_long_name", "")

            # Audio properties
            if "bit_rate" in stream:
                result["bitrate"] = int(stream["bit_rate"])
            elif "bit_rate" in format_info:
                result["bitrate"] = int(format_info["bit_rate"])

            if "sample_rate" in stream:
                result["sample_rate"] = int(stream["sample_rate"])

            if "channels" in stream:
                result["channels"] = int(stream["channels"])

            # Channel layout
            if "channel_layout" in stream:
                result["channel_layout"] = stream["channel_layout"]

        # Chapter information
        chapters: list[dict[str, Any]] = data.get("chapters", [])
        result["chapter_count"] = len(chapters)
        result["has_chapters"] = len(chapters) > 0

        if chapters:
            chapter_list = []
            for i, chapter in enumerate(chapters):
                chapter_info: dict[str, Any] = {
                    "number": i + 1,
                    "title": chapter.get("tags", {}).get("title", f"Chapter {i + 1}"),
                    "start_time": float(chapter.get("start_time", 0)),
                    "end_time": float(chapter.get("end_time", 0)),
                    "duration": float(chapter.get("end_time", 0))
                    - float(chapter.get("start_time", 0)),
                }
                chapter_list.append(chapter_info)  # type: ignore
            result["chapters"] = chapter_list

        # Cover art detection (look for attached pictures)
        video_streams: list[dict[str, Any]] = [
            s for s in data.get("streams", []) if s.get("codec_type") == "video"
        ]
        cover_streams: list[dict[str, Any]] = [
            s for s in video_streams if s.get("disposition", {}).get("attached_pic")
        ]

        result["has_cover_art"] = len(cover_streams) > 0
        if cover_streams:
            cover: dict[str, Any] = cover_streams[0]
            result["cover_dimensions"] = {
                "width": cover.get("width", 0),
                "height": cover.get("height", 0),
            }

        return result

    def _normalize_mutagen_data(
        self, audio_file: MutagenFile, file_path: Path
    ) -> dict[str, Any]:
        """Normalize mutagen data to internal format."""
        result: dict[str, Any] = {"_src": "embedded"}

        # File size
        file_size = file_path.stat().st_size
        result["file_size_bytes"] = file_size
        result["file_size_mb"] = round(file_size / (1024 * 1024), 1)

        # Format detection from file extension and mutagen type
        ext_formats = {
            ".mp3": "MP3",
            ".m4a": "AAC",
            ".m4b": "AAC",
            ".flac": "FLAC",
            ".ogg": "OGG",
            ".opus": "Opus",
        }
        result["format"] = ext_formats.get(file_path.suffix.lower(), "Unknown")

        # Audio properties from mutagen info
        if hasattr(audio_file, "info") and audio_file.info:
            info = audio_file.info

            # Duration
            if hasattr(info, "length") and info.length:
                result["duration_sec"] = int(info.length)

            # Bitrate and CBR/VBR detection
            if hasattr(info, "bitrate") and info.bitrate:
                result["bitrate"] = info.bitrate

                # Calculate actual bitrate from file size for CBR/VBR detection
                if info.length and info.length > 0:
                    calculated_bitrate = (file_size * 8) / info.length
                    result["calculated_bitrate"] = int(calculated_bitrate)

                    # Calculate variance percentage
                    variance = (
                        abs(calculated_bitrate - info.bitrate) / info.bitrate * 100
                    )
                    result["bitrate_variance"] = round(variance, 1)

                    # Determine encoding mode (CBR vs VBR) with format-specific thresholds
                    # AAC/M4B files are almost always VBR even with low variance
                    # MP3 files typically need higher variance to be considered VBR
                    file_ext = file_path.suffix.lower()
                    if file_ext in [".m4b", ".m4a", ".aac"]:
                        # AAC files: even small variance usually indicates VBR/CVBR
                        result["bitrate_mode"] = "CBR" if variance < 1.0 else "VBR"
                    elif file_ext == ".mp3":
                        # MP3 files: need more variance to be considered VBR
                        result["bitrate_mode"] = "CBR" if variance < 5.0 else "VBR"
                    else:
                        # Other formats: use conservative threshold
                        result["bitrate_mode"] = "CBR" if variance < 3.0 else "VBR"

            # Sample rate
            if hasattr(info, "sample_rate") and info.sample_rate:
                result["sample_rate"] = info.sample_rate

            # Channels
            if hasattr(info, "channels") and info.channels:
                result["channels"] = info.channels

        # Enhanced chapter detection for M4B files
        result["chapter_count"] = 0
        result["has_chapters"] = False
        result["chapters"] = []

        # Try to extract chapters from M4B/MP4 files
        if file_path.suffix.lower() in [".m4b", ".m4a"] and hasattr(audio_file, "tags"):
            total_length = None
            try:
                # For MP4/M4B files, try to get chapter information
                from mutagen.mp4 import MP4

                if isinstance(audio_file, MP4):
                    # Look for chapter information in various possible locations
                    chapters_found = []

                    # Method 1: Check for timed text tracks (chapters)
                    if hasattr(audio_file, "info") and hasattr(
                        audio_file.info, "length"
                    ):
                        total_length = audio_file.info.length

                        # Try to extract chapter count from tags
                        # Some M4B files store chapter info in custom atoms
                        if audio_file.tags:
                            # Look for chapter-related tags
                            for key, value in audio_file.tags.items():  # type: ignore
                                if (
                                    "chap" in str(key).lower()  # type: ignore
                                    or "toc" in str(key).lower()  # type: ignore
                                ):
                                    logger.debug(
                                        f"Found potential chapter tag: {key} = {value}"
                                    )

                            # Check for track number patterns that might indicate chapters
                            track_num: Any = audio_file.tags.get("trkn")  # type: ignore
                            if track_num and len(track_num) > 0:  # type: ignore
                                if len(track_num[0]) == 2:  # type: ignore
                                    total_tracks: int = track_num[0][1]  # type: ignore
                                    if total_tracks and total_tracks > 1:
                                        result["chapter_count"] = total_tracks
                                        result["has_chapters"] = True

                                        # Create basic chapter structure
                                        chapter_duration: float = (  # type: ignore
                                            total_length / total_tracks
                                            if total_tracks > 0
                                            else 0
                                        )
                                        for i in range(total_tracks):  # type: ignore
                                            chapter_info: dict[str, Any] = {  # type: ignore
                                                "number": i + 1,
                                                "title": f"Chapter {i + 1}",
                                                "start_time": i * chapter_duration,
                                                "end_time": (i + 1) * chapter_duration,
                                                "duration": chapter_duration,
                                            }
                                            chapters_found.append(chapter_info)  # type: ignore

                                        result["chapters"] = chapters_found
                                        logger.debug(
                                            f"Extracted {total_tracks} chapters from track info"
                                        )

                    # If no chapters found yet, make an educated guess for audiobooks
                    if not result["has_chapters"] and total_length:
                        # For large audiobooks (>30 minutes), estimate chapters
                        if total_length > 1800:  # 30 minutes
                            estimated_chapters = max(
                                1, int(total_length / 1800)
                            )  # ~30 min chapters
                            if (
                                estimated_chapters > 1 and estimated_chapters < 50
                            ):  # Reasonable range
                                result["chapter_count"] = estimated_chapters
                                result["has_chapters"] = True
                                logger.debug(
                                    f"Estimated {estimated_chapters} chapters for {total_length/60:.1f} minute audiobook"
                                )

            except Exception as e:
                logger.debug(f"Chapter detection failed: {e}")
                # Keep defaults if chapter detection fails

        # Cover art detection (basic)
        result["has_cover_art"] = False
        if hasattr(audio_file, "tags") and audio_file.tags:
            # Check for common cover art tags (format-specific)
            cover_keys = ["APIC", "covr", "METADATA_BLOCK_PICTURE"]
            for key in cover_keys:
                if key in audio_file.tags:
                    result["has_cover_art"] = True
                    break

        return result

    def _basic_file_info(self, file_path: Path) -> dict[str, Any]:
        """Minimal file information when tools unavailable."""
        result: dict[str, Any] = {"_src": "embedded"}

        try:
            # Basic file system info
            stat = file_path.stat()
            result["file_size_bytes"] = stat.st_size
            result["file_size_mb"] = round(stat.st_size / (1024 * 1024), 1)

            # File extension and format hint
            result["file_extension"] = file_path.suffix.lower()

            # Basic format detection from extension
            ext_formats = {
                ".mp3": "MP3",
                ".m4a": "AAC",
                ".m4b": "AAC",
                ".flac": "FLAC",
                ".ogg": "OGG",
                ".opus": "Opus",
            }
            result["format_hint"] = ext_formats.get(file_path.suffix.lower(), "Unknown")

        except OSError as e:
            logger.warning(f"Could not get basic file info for {file_path}: {e}")

        # Set defaults for missing technical data
        result.setdefault("duration_sec", None)
        result.setdefault("bitrate", None)
        result.setdefault("sample_rate", None)
        result.setdefault("channels", None)
        result.setdefault("chapter_count", 0)
        result.setdefault("has_chapters", False)
        result.setdefault("chapters", [])
        result.setdefault("has_cover_art", False)

        return result

    def get_backend_info(self) -> dict[str, Any]:
        """Get information about available backends."""
        return {
            "ffprobe_available": self.ffprobe_available,
            "mutagen_available": self.mutagen_available,
            "preferred_backend": "ffprobe" if self.prefer_ffprobe else "mutagen",
            "active_backend": self._get_active_backend(),
        }

    def _get_active_backend(self) -> str:
        """Determine which backend would be used."""
        if self.prefer_ffprobe and self.ffprobe_available:
            return "ffprobe"
        elif self.mutagen_available:
            return "mutagen"
        else:
            return "basic"

    def validate_file(self, file_path: Path) -> bool:
        """Quick validation that file can be processed."""
        if not file_path.exists():
            return False

        # Check if it's a supported audio format
        audio_extensions = {
            ".mp3",
            ".m4a",
            ".m4b",
            ".flac",
            ".ogg",
            ".opus",
            ".wav",
            ".aiff",
        }
        return file_path.suffix.lower() in audio_extensions
