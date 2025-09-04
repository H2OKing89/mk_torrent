"""
Audio format detection and analysis service - Core Modular Metadata System.

Part of the new modular metadata architecture providing detailed audio format
information using Mutagen (preferred) with fallback detection methods.

Provides detailed audio format information using Mutagen (preferred) with
fallback detection methods following the recommended packages specification.

Architecture Documentation:
- Service Specification: docs/core/metadata/07.2 — Format Detector Service.md
- Services Overview: docs/core/metadata/07 — Services Details.md (Section 7.2)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AudioFormat:
    """Audio format information container."""

    def __init__(
        self,
        format_name: str,
        codec: str | None = None,
        encoding: str | None = None,
        bitrate: int | None = None,
        sample_rate: int | None = None,
        channels: int | None = None,
        bit_depth: int | None = None,
        duration: float | None = None,
        is_lossless: bool | None = None,
        is_vbr: bool | None = None,
        quality_score: float = 0.0,
        source: str = "mutagen",
    ):
        self.format_name = format_name
        self.codec = codec
        self.encoding = encoding  # CBR320, V0, V1, Lossless, etc.
        self.bitrate = bitrate  # in kbps
        self.sample_rate = sample_rate  # in Hz
        self.channels = channels
        self.bit_depth = bit_depth
        self.duration = duration  # in seconds
        self.is_lossless = is_lossless
        self.is_vbr = is_vbr
        self.quality_score = quality_score  # 0.0-1.0 quality rating
        self.source = source  # "mutagen" or "extension"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "format": self.format_name,
            "codec": self.codec,
            "encoding": self.encoding,
            "bitrate": self.bitrate,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bit_depth": self.bit_depth,
            "duration": self.duration,
            "is_lossless": self.is_lossless,
            "is_vbr": self.is_vbr,
            "quality_score": self.quality_score,
            "source": self.source,
        }

    def __str__(self) -> str:
        """Human-readable format description."""
        parts = [self.format_name]

        if self.codec:
            parts.append(f"({self.codec})")

        if self.encoding:
            parts.append(self.encoding)
        elif self.bitrate:
            vbr_suffix = " VBR" if self.is_vbr else ""
            parts.append(f"{self.bitrate}kbps{vbr_suffix}")
        elif self.is_lossless:
            parts.append("lossless")

        if self.sample_rate:
            parts.append(f"{self.sample_rate/1000:.1f}kHz")

        if self.channels:
            channel_desc = {1: "mono", 2: "stereo", 6: "5.1", 8: "7.1"}.get(
                self.channels, f"{self.channels}ch"
            )
            parts.append(channel_desc)

        return " ".join(parts)


class FormatDetector:
    """
    Audio format detection service with Mutagen support.

    Provides detailed analysis of audio files including format, codec,
    bitrate, quality metrics, and technical specifications.
    """

    # Lossless formats
    LOSSLESS_FORMATS = {"flac", "alac", "ape", "wv", "tta", "wav", "aiff"}

    # MP3 VBR classification ranges (bitrate ranges in kbps)
    MP3_VBR_RANGES = {
        "V0": (220, 260),  # Average bitrate ranges
        "V1": (190, 230),
        "V2": (170, 210),
        "V3": (150, 190),
        "V4": (130, 170),
        "V5": (110, 150),
    }

    # Format mappings for common extensions
    FORMAT_MAPPINGS = {
        ".mp3": "MP3",
        ".m4a": "M4A",
        ".m4b": "M4B",
        ".aac": "AAC",
        ".flac": "FLAC",
        ".ogg": "OGG",
        ".oga": "OGG",
        ".opus": "Opus",
        ".wav": "WAV",
        ".aiff": "AIFF",
        ".ape": "APE",
        ".wv": "WavPack",
        ".tta": "TTA",
    }

    def __init__(self):
        """Initialize format detector."""
        self._mutagen_available = self._check_mutagen()

    def _check_mutagen(self) -> bool:
        """Check if Mutagen is available."""
        import importlib.util

        if importlib.util.find_spec("mutagen") is not None:
            logger.debug("Mutagen available for format detection")
            return True
        else:
            logger.warning("Mutagen not available, using basic format detection")
            return False

    def detect_format(self, file_path: str | Path) -> AudioFormat:
        """
        Detect audio format and extract technical information.

        Args:
            file_path: Path to audio file

        Returns:
            AudioFormat object with detected information
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        if self._mutagen_available:
            return self._detect_with_mutagen(file_path)
        else:
            return self._detect_basic(file_path)

    def get_duration(self, file_path: str | Path) -> int | None:
        """
        Get audio duration in seconds.

        Args:
            file_path: Path to audio file

        Returns:
            Duration in seconds, None if unavailable
        """
        try:
            if self._mutagen_available:
                from mutagen._file import File as MutagenFile

                audio_file = MutagenFile(file_path)
                if (
                    audio_file
                    and hasattr(audio_file, "info")
                    and hasattr(audio_file.info, "length")
                ):
                    return int(audio_file.info.length)
            return None
        except Exception:
            return None

    def _detect_with_mutagen(self, file_path: Path) -> AudioFormat:
        """Detect format using Mutagen for detailed analysis."""
        try:
            from mutagen._file import File as MutagenFile

            audio_file = MutagenFile(file_path)

            if audio_file is None:
                return self._detect_basic(file_path)

            # Get format name
            format_name = self._get_format_name_mutagen(audio_file)

            # Extract technical information
            info = audio_file.info if hasattr(audio_file, "info") else None

            # Basic properties
            duration = getattr(info, "length", None)
            bitrate = getattr(info, "bitrate", None)
            sample_rate = getattr(info, "sample_rate", None)
            channels = getattr(info, "channels", None)

            # Advanced properties
            bit_depth = self._get_bit_depth(info)
            is_vbr = self._detect_vbr(info)
            is_lossless = self._detect_lossless(format_name, info)
            codec = self._get_codec_info(audio_file, info)

            # Encoding classification
            encoding = self._classify_encoding(
                format_name, info, bitrate, is_vbr, is_lossless
            )

            # Quality scoring
            quality_score = self._calculate_quality_score(
                format_name, bitrate, is_lossless
            )

            return AudioFormat(
                format_name=format_name,
                codec=codec,
                encoding=encoding,
                bitrate=bitrate,
                sample_rate=sample_rate,
                channels=channels,
                bit_depth=bit_depth,
                duration=duration,
                is_lossless=is_lossless,
                is_vbr=is_vbr,
                quality_score=quality_score,
                source="mutagen",
            )

        except Exception as e:
            logger.warning(f"Mutagen format detection failed: {e}")
            return self._detect_basic(file_path)

    def _detect_basic(self, file_path: Path) -> AudioFormat:
        """Basic format detection using file extension and MIME type."""
        ext = file_path.suffix.lower()
        format_name = self.FORMAT_MAPPINGS.get(ext, ext.lstrip(".").upper())

        # Basic lossless detection
        is_lossless = format_name.lower() in self.LOSSLESS_FORMATS

        # Basic encoding classification
        encoding = "Lossless" if is_lossless else "Unknown"

        return AudioFormat(
            format_name=format_name,
            encoding=encoding,
            is_lossless=is_lossless,
            quality_score=0.5,  # Neutral score for unknown
            source="extension",
        )

    def _get_format_name_mutagen(self, audio_file) -> str:
        """Extract format name from Mutagen file object."""
        # Get the class name and map to readable format
        class_name = audio_file.__class__.__name__.lower()

        format_map = {
            "mp3": "MP3",
            "mp4": "M4A",
            "flac": "FLAC",
            "oggvorbis": "OGG",
            "oggopus": "Opus",
            "wave": "WAV",
            "aiff": "AIFF",
            "monkeysaudio": "APE",
            "wavpack": "WavPack",
            "trueaudio": "TTA",
        }

        return format_map.get(class_name) or class_name.upper()

    def _get_bit_depth(self, info) -> int | None:
        """Extract bit depth information."""
        if hasattr(info, "bits_per_sample"):
            return info.bits_per_sample
        elif hasattr(info, "bitspersample"):
            return info.bitspersample
        return None

    def _detect_vbr(self, info) -> bool | None:
        """Detect if audio uses variable bitrate."""
        if hasattr(info, "bitrate_mode"):
            # Some formats explicitly indicate VBR mode
            return "vbr" in str(info.bitrate_mode).lower()
        elif hasattr(info, "mode"):
            return "vbr" in str(info.mode).lower()
        return None

    def _detect_lossless(self, format_name: str, info) -> bool | None:
        """Detect if format is lossless."""
        # Check format-based lossless detection
        if format_name.lower() in self.LOSSLESS_FORMATS:
            return True

        # For MP3/AAC/OGG, definitely lossy
        if format_name.lower() in {"mp3", "aac", "ogg", "opus"}:
            return False

        # For M4A, could be ALAC (lossless) or AAC (lossy)
        if format_name.lower() in {"m4a", "m4b"}:
            if hasattr(info, "codec"):
                return "alac" in str(info.codec).lower()

        return None

    def _get_codec_info(self, audio_file, info) -> str | None:
        """Extract codec information."""
        if hasattr(info, "codec"):
            return str(info.codec)
        elif hasattr(info, "codec_name"):
            return str(info.codec_name)

        # Infer from format
        class_name = audio_file.__class__.__name__.lower()
        if "mp3" in class_name:
            return "MPEG-1 Layer 3"
        elif "mp4" in class_name:
            return "AAC"  # Could also be ALAC

        return None

    def _classify_encoding(
        self,
        format_name: str,
        info,
        bitrate: int | None,
        is_vbr: bool | None,
        is_lossless: bool | None,
    ) -> str:
        """Classify encoding type (CBR, VBR, Lossless, etc.)."""
        if is_lossless:
            return "Lossless"

        if format_name.lower() == "mp3" and bitrate and is_vbr:
            # MP3 VBR classification
            for vbr_class, (min_br, max_br) in self.MP3_VBR_RANGES.items():
                if min_br <= bitrate <= max_br:
                    return vbr_class
            return f"VBR{bitrate}"
        elif bitrate and not is_vbr:
            return f"CBR{bitrate}"
        elif is_vbr:
            return "VBR"
        else:
            return "Unknown"

    def _calculate_quality_score(
        self, format_name: str, bitrate: int | None, is_lossless: bool | None
    ) -> float:
        """Calculate relative quality score (0.0-1.0)."""
        if is_lossless:
            return 1.0

        if not bitrate:
            return 0.5

        # Quality thresholds based on bitrate
        if bitrate >= 320:
            return 0.9
        elif bitrate >= 256:
            return 0.8
        elif bitrate >= 192:
            return 0.7
        elif bitrate >= 128:
            return 0.6
        else:
            return 0.4

    def analyze_directory(self, directory: str | Path) -> dict[str, list[AudioFormat]]:
        """
        Analyze all audio files in a directory.

        Args:
            directory: Path to directory containing audio files

        Returns:
            Dictionary mapping format names to lists of AudioFormat objects
        """
        directory = Path(directory)

        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        results: dict[str, list[AudioFormat]] = {}

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
                    format_info = self.detect_format(file_path)
                    format_name = format_info.format_name

                    if format_name not in results:
                        results[format_name] = []

                    results[format_name].append(format_info)

                except Exception as e:
                    logger.warning(f"Failed to analyze {file_path}: {e}")

        return results

    def get_quality_summary(self, formats: list[AudioFormat]) -> dict[str, Any]:
        """
        Generate quality summary from format analysis.

        Args:
            formats: List of AudioFormat objects

        Returns:
            Summary dictionary with quality metrics
        """
        if not formats:
            return {}

        # Count formats
        format_counts = {}
        lossless_count = 0
        total_duration = 0
        bitrates = []

        for fmt in formats:
            format_counts[fmt.format_name] = format_counts.get(fmt.format_name, 0) + 1

            if fmt.is_lossless:
                lossless_count += 1

            if fmt.duration:
                total_duration += fmt.duration

            if fmt.bitrate:
                bitrates.append(fmt.bitrate)

        summary = {
            "total_files": len(formats),
            "formats": format_counts,
            "lossless_files": lossless_count,
            "total_duration_seconds": total_duration,
        }

        if bitrates:
            summary.update(
                {
                    "avg_bitrate": sum(bitrates) / len(bitrates),
                    "min_bitrate": min(bitrates),
                    "max_bitrate": max(bitrates),
                }
            )

        return summary
