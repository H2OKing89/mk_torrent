"""
Path Info Source - Core Modular Metadata System (Canonical Filename Parsing).

Part of the new modular metadata architecture providing compliance-focused
metadata extraction from standardized audiobook filenames and directory structures
as one of three sources in the intelligent merging strategy.

Extracts metadata from standardized audiobook filenames and directory structures.
Zero I/O design for fast, deterministic parsing.

Architecture Documentation:
- Source Specification: docs/core/metadata/07.4 — Path Info Source.md
- Three-Source Strategy: docs/core/metadata/06 — Engine Pipeline.md
- Services Overview: docs/core/metadata/07 — Services Details.md (Section 7.4)

Format: Title - vol_XX (YYYY) (Author) {ASIN.ABC} [Uploader]
"""

from __future__ import annotations
import re
import unicodedata
from pathlib import Path
from typing import Any


class PathInfoSource:
    """
    Filename and directory structure parser for audiobook metadata.

    Supports the canonical format:
    Title - vol_XX (YYYY) (Author) {ASIN.ABC} [Uploader]

    With graceful degradation for various naming patterns.
    """

    # Primary canonical pattern
    PRIMARY_PATTERN = re.compile(
        r"^(?P<title>.*?)"  # Title (non-greedy)
        r"(?:\s*-\s*vol_(?P<volume>\d+))?"  # Optional volume
        r"(?:\s*\((?P<year>\d{4})\))?"  # Optional year
        r"(?:\s*\((?P<author>[^)]+)\))?"  # Optional author
        r"(?:\s*\{ASIN\.(?P<asin>[A-Z0-9]{10})\})?"  # Optional ASIN with ASIN. prefix
        r"(?:\s*\[(?P<uploader>[^\]]+)\])?"  # Optional uploader
        r"(?:\.[^.]+)?$",  # Optional file extension
        re.IGNORECASE | re.UNICODE,
    )

    # Alternative patterns for less standardized filenames
    SERIES_PATTERN = re.compile(
        r"^(?P<series>.*?)\s+(?:Book|Vol\.?|Part)\s+(?P<volume>\d+)"
        r"(?:\s*-\s*(?P<title>[^(]+?))?"
        r"(?:\s*\((?P<year>\d{4})\))?"
        r"(?:\s*\((?P<author>[^)]+)\))?",
        re.IGNORECASE,
    )

    SIMPLE_PATTERN = re.compile(
        r"^(?P<title>.*?)"
        r"(?:\s*\((?P<author>[^)]+)\))?"
        r"(?:\s*\{(?P<asin>[A-Z0-9]{10})\})?",
        re.IGNORECASE,
    )

    def __init__(self, strict: bool = False):
        """
        Initialize path info parser.

        Args:
            strict: Require canonical format (fail on non-standard patterns)
        """
        self.strict = strict

    def extract(self, source: Path | str) -> dict[str, Any]:
        """
        Parse metadata from filename or path.

        Args:
            source: File path or filename string

        Returns:
            Dict with extracted metadata and "_src": "path"
        """
        if isinstance(source, Path):
            # Use just the filename, not the full path
            filename = source.name
            directory = source.parent.name if source.parent.name != "." else ""
        else:
            # Handle string input
            path_obj = Path(source)
            filename = path_obj.name
            directory = path_obj.parent.name if path_obj.parent.name != "." else ""

        # Remove file extension for parsing (only if it looks like a valid extension)
        basename = filename
        if "." in filename:
            # Split on last dot
            name_part, ext_part = filename.rsplit(".", 1)
            # Only treat as extension if it's 2-4 alphanumeric characters
            if len(ext_part) <= 4 and ext_part.isalnum():
                basename = name_part
            else:
                basename = filename

        result = {"_src": "path"}

        # Try parsing with primary pattern first
        match = self.PRIMARY_PATTERN.match(basename)
        if match:
            extracted = self._extract_primary(match.groupdict())
            result.update(extracted)
        else:
            # Try alternative patterns
            result.update(self._fallback_parse(basename))

        # Enhance with directory information if available
        if directory:
            dir_info = self._parse_directory(directory)
            # Merge directory info, but don't override filename data
            for key, value in dir_info.items():
                if key not in result or not result[key]:
                    result[key] = value

        # Clean and normalize extracted fields
        result = self._clean_extracted_data(result)

        return result

    def _extract_primary(self, groups: dict[str, Any]) -> dict[str, Any]:
        """Extract from canonical format match."""
        result: dict[str, Any] = {}

        if groups.get("title"):
            title: str = groups["title"]
            result["title"] = self._clean_title(title)

        if groups.get("volume"):
            volume_str: str = groups["volume"]
            result["volume"] = self._normalize_volume(volume_str)

        if groups.get("year"):
            try:
                year = int(groups["year"])
                if 1900 <= year <= 2100:  # Reasonable year range
                    result["year"] = year
            except ValueError:
                pass

        if groups.get("author"):
            author: str = groups["author"]
            result["author"] = self._clean_author(author)

        if groups.get("asin"):
            asin: str = groups["asin"].upper()
            if self._validate_asin(asin):
                result["asin"] = asin

        if groups.get("uploader"):
            uploader: str = groups["uploader"]
            result["uploader"] = uploader.strip()

        # If we have both title and volume, treat title as series name
        if result.get("title") and result.get("volume"):
            result["series"] = result["title"]

        return result

    def _fallback_parse(self, basename: str) -> dict[str, Any]:
        """Try alternative parsing patterns."""
        result: dict[str, Any] = {}

        # Try series pattern
        match = self.SERIES_PATTERN.match(basename)
        if match:
            groups: dict[str, Any] = match.groupdict()

            if groups.get("series"):
                result["series"] = self._clean_title(groups["series"])

            if groups.get("volume"):
                result["volume"] = self._normalize_volume(groups["volume"])

            if groups.get("title"):
                result["title"] = self._clean_title(groups["title"])
            else:
                # Construct title from series + volume
                series = result.get("series", "")
                volume = result.get("volume", "")
                if series and volume:
                    result["title"] = f"{series} - Book {volume}"

            if groups.get("year"):
                try:
                    result["year"] = int(groups["year"])
                except ValueError:
                    pass

            if groups.get("author"):
                result["author"] = self._clean_author(groups["author"])

            return result

        # Try simple pattern
        match = self.SIMPLE_PATTERN.match(basename)
        if match:
            groups: dict[str, Any] = match.groupdict()

            if groups.get("title"):
                result["title"] = self._clean_title(groups["title"])

            if groups.get("author"):
                result["author"] = self._clean_author(groups["author"])

            if groups.get("asin"):
                asin = groups["asin"].upper()
                if self._validate_asin(asin):
                    result["asin"] = asin

            return result

        # Last resort: treat entire basename as title
        if basename and not self.strict:
            result["title"] = self._clean_title(basename)

        return result

    def _parse_directory(self, directory: str) -> dict[str, Any]:
        """Extract metadata from directory structure."""
        result: dict[str, Any] = {}

        # Look for series patterns in directory name
        series_match = re.search(
            r"^(.+?)(?:\s+(?:Series|Collection))?$", directory, re.IGNORECASE
        )
        if series_match:
            potential_series = series_match.group(1).strip()
            if self._looks_like_series(potential_series):
                result["series"] = self._clean_title(potential_series)

        return result

    def _clean_title(self, title: str) -> str:
        """Clean and normalize title."""
        if not title:
            return ""

        # Normalize Unicode
        title = unicodedata.normalize("NFKC", title)

        # Remove extra whitespace
        title = " ".join(title.split())

        # Remove common filename artifacts
        title = re.sub(r"\s*[-_]\s*$", "", title)  # Trailing separators
        title = re.sub(r"^\s*[-_]\s*", "", title)  # Leading separators

        return title.strip()

    def _clean_author(self, author: str) -> str:
        """Clean and normalize author names."""
        if not author:
            return ""

        # Normalize Unicode
        author = unicodedata.normalize("NFKC", author)

        # Handle multiple authors separated by common delimiters
        authors = re.split(r"[,;&]", author)
        if len(authors) > 1:
            # For now, just take the first author
            # TODO: Support multiple authors in the data model
            author = authors[0]

        return author.strip()

    def _normalize_volume(self, volume_str: str) -> str:
        """Normalize volume numbers."""
        if not volume_str:
            return ""

        try:
            volume_num = int(volume_str)
            return f"{volume_num:02d}"  # Zero-pad to 2 digits
        except ValueError:
            return volume_str

    def _validate_asin(self, asin: str) -> bool:
        """Validate ASIN format."""
        if not asin or len(asin) != 10:
            return False

        # ASINs start with B and have 9 alphanumeric characters
        return asin.startswith("B") and asin[1:].isalnum()

    def _looks_like_series(self, text: str) -> bool:
        """Heuristic check if text looks like a series name."""
        if not text or len(text) < 3:
            return False

        # Exclude common non-series directory names
        excluded = {
            "audiobooks",
            "books",
            "downloads",
            "media",
            "audio",
            "music",
            "files",
            "data",
            "tmp",
            "temp",
        }

        return text.lower() not in excluded

    def _looks_like_author(self, text: str) -> bool:
        """Heuristic check if text looks like an author name."""
        if not text or len(text) < 3:
            return False

        # Basic checks for author-like text
        # Has at least one letter
        if not re.search(r"[a-zA-Z]", text):
            return False

        # Not all caps (unless short)
        if len(text) > 10 and text.isupper():
            return False

        # Common author name patterns
        author_patterns = [
            r"^[A-Z][a-z]+\s+[A-Z][a-z]+",  # First Last
            r"^[A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+",  # A. B. Last
            r"^[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+",  # First M. Last
        ]

        return any(re.match(pattern, text) for pattern in author_patterns)

    def _clean_extracted_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Final cleanup and normalization of extracted data."""
        cleaned: dict[str, Any] = {}

        for key, value in data.items():
            if key == "_src":
                cleaned[key] = value
                continue

            if isinstance(value, str):
                value = value.strip()
                if value:  # Only include non-empty strings
                    cleaned[key] = value
            elif value is not None:
                cleaned[key] = value

        return cleaned

    def validate_filename(self, filename: str) -> tuple[bool, list[str]]:
        """
        Validate filename against canonical format.

        Args:
            filename: Filename to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues: list[str] = []

        # Remove extension for validation
        basename = filename
        if "." in filename:
            basename = filename.rsplit(".", 1)[0]

        # Check if it matches primary pattern
        match = self.PRIMARY_PATTERN.match(basename)
        if not match:
            issues.append("Does not match canonical format")
            return False, issues

        groups: dict[str, Any] = match.groupdict()

        # Check for required components
        if not groups.get("title"):
            issues.append("Missing title")

        # Check ASIN format if present
        if groups.get("asin"):
            if not self._validate_asin(groups["asin"]):
                issues.append("Invalid ASIN format")

        # Check year format if present
        if groups.get("year"):
            try:
                year = int(groups["year"])
                if not (1900 <= year <= 2100):
                    issues.append("Year out of reasonable range")
            except ValueError:
                issues.append("Invalid year format")

        return len(issues) == 0, issues

    def suggest_canonical_format(self, filename: str) -> str:
        """
        Suggest canonical format for a filename.

        Args:
            filename: Original filename

        Returns:
            Suggested canonical filename
        """
        # Parse the existing filename
        extracted = self.extract(filename)

        # Build canonical format
        parts: list[str] = []

        # Title (required)
        title = extracted.get("title", "Unknown Title")
        parts.append(title)

        # Volume
        if extracted.get("volume"):
            parts.append(f"vol_{extracted['volume']}")

        # Year
        if extracted.get("year"):
            parts.append(f"({extracted['year']})")

        # Author
        if extracted.get("author"):
            parts.append(f"({extracted['author']})")

        # ASIN
        if extracted.get("asin"):
            parts.append(f"{{{extracted['asin']}}}")

        # Uploader
        if extracted.get("uploader"):
            parts.append(f"[{extracted['uploader']}]")

        return " ".join(parts)
