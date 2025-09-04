"""
Embedded metadata source - Technical Focus.

Extracts technical file properties (duration, bitrate, codec, chapters) using
ffprobe (preferred) or mutagen (fallback). Avoids unreliable descriptive tags.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Union

logger = logging.getLogger(__name__)


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

    def extract(self, source: Union[Path, str]) -> Dict[str, Any]:
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

    def _extract_with_ffprobe(self, file_path: Path) -> Dict[str, Any]:
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

    def _extract_with_mutagen(self, file_path: Path) -> Dict[str, Any]:
        """Extract technical metadata using mutagen."""
        try:
            from mutagen._file import File as MutagenFile

            audio_file = MutagenFile(file_path)
            if audio_file is None:
                raise ValueError(f"mutagen could not read file: {file_path}")

            return self._normalize_mutagen_data(audio_file, file_path)

        except ImportError:
            raise RuntimeError("mutagen not available")

    def _normalize_ffprobe_data(self, data: dict, file_path: Path) -> Dict[str, Any]:
        """Normalize ffprobe output to internal format."""
        result: Dict[str, Any] = {"_src": "embedded"}

        # Get format information
        format_info = data.get("format", {})

        # File size
        file_size = format_info.get("size")
        if file_size:
            result["file_size_bytes"] = int(file_size)
            result["file_size_mb"] = round(int(file_size) / (1024 * 1024), 1)

        # Duration (prefer format duration as it's most reliable)
        duration = format_info.get("duration")
        if duration:
            result["duration_sec"] = int(float(duration))

        # Audio stream information
        audio_streams = [
            s for s in data.get("streams", []) if s.get("codec_type") == "audio"
        ]
        if audio_streams:
            stream = audio_streams[0]  # Use first audio stream

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
        chapters = data.get("chapters", [])
        result["chapter_count"] = len(chapters)
        result["has_chapters"] = len(chapters) > 0

        if chapters:
            chapter_list = []
            for i, chapter in enumerate(chapters):
                chapter_info = {
                    "number": i + 1,
                    "title": chapter.get("tags", {}).get("title", f"Chapter {i + 1}"),
                    "start_time": float(chapter.get("start_time", 0)),
                    "end_time": float(chapter.get("end_time", 0)),
                    "duration": float(chapter.get("end_time", 0))
                    - float(chapter.get("start_time", 0)),
                }
                chapter_list.append(chapter_info)
            result["chapters"] = chapter_list

        # Cover art detection (look for attached pictures)
        video_streams = [
            s for s in data.get("streams", []) if s.get("codec_type") == "video"
        ]
        cover_streams = [
            s for s in video_streams if s.get("disposition", {}).get("attached_pic")
        ]

        result["has_cover_art"] = len(cover_streams) > 0
        if cover_streams:
            cover = cover_streams[0]
            result["cover_dimensions"] = {
                "width": cover.get("width", 0),
                "height": cover.get("height", 0),
            }

        return result

    def _normalize_mutagen_data(self, audio_file, file_path: Path) -> Dict[str, Any]:
        """Normalize mutagen data to internal format."""
        result: Dict[str, Any] = {"_src": "embedded"}

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

            # Bitrate
            if hasattr(info, "bitrate") and info.bitrate:
                result["bitrate"] = info.bitrate

            # Sample rate
            if hasattr(info, "sample_rate") and info.sample_rate:
                result["sample_rate"] = info.sample_rate

            # Channels
            if hasattr(info, "channels") and info.channels:
                result["channels"] = info.channels

        # Basic chapter detection (limited with mutagen)
        # This is format-specific and limited compared to ffprobe
        result["chapter_count"] = 0
        result["has_chapters"] = False
        result["chapters"] = []

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

    def _basic_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Minimal file information when tools unavailable."""
        result: Dict[str, Any] = {"_src": "embedded"}

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

    def get_backend_info(self) -> Dict[str, Any]:
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
