"""
Audiobook Metadata Field Merger - Declarative precedence-based merging.

Combines multiple metadata sources (path, embedded, API) into a single,
deterministic record using smart precedence rules and list union logic.

This module is specifically designed for audiobook metadata processing.
For future music or video support, create separate merge_music.py or
merge_video.py modules with media-specific precedence rules.

Features:
- Declarative per-field precedence configuration
- Smart list union for genres/tags with case-insensitive deduplication
- Source tagging for traceability
- Meaningful value detection (ignores empty/null values)
- Optimized for audiobook workflow with technical vs descriptive field separation
"""

from __future__ import annotations
from typing import Any
from collections.abc import Iterable

Scalar = Any

# Updated precedence for three-source strategy
DEFAULT_PRECEDENCE: dict[str, list[str]] = {
    # Descriptive fields (path + API primary, embedded fallback)
    "title": ["api", "path", "embedded"],  # Added embedded fallback
    "author": ["api", "path", "embedded"],  # Added embedded fallback
    "series": ["path", "api", "embedded"],  # Path wins for compliance
    "volume": ["path", "api", "embedded"],  # Path wins for compliance
    "year": ["api", "path", "embedded"],  # API more accurate
    "narrator": ["api", "embedded"],  # API primary, embedded fallback
    "publisher": ["api", "embedded"],  # API primary, embedded fallback
    "asin": ["path", "api", "embedded"],  # Path for tracker compliance
    "isbn": ["api", "embedded"],  # API primary, embedded fallback
    "description": ["api", "embedded"],  # API primary, embedded fallback
    "artwork_url": ["api", "embedded"],  # API primary, embedded fallback
    # Technical fields (embedded wins - most accurate)
    "duration_sec": [
        "embedded",
        "api",
        "path",
    ],  # Embedded precise seconds > API minutes
    "file_size_bytes": ["embedded"],  # Only embedded has this
    "file_size_mb": ["embedded"],  # Only embedded has this
    "bitrate": ["embedded"],  # Only embedded has this
    "sample_rate": ["embedded"],  # Only embedded has this
    "channels": ["embedded"],  # Only embedded has this
    "codec": ["embedded"],  # Only embedded has this
    "format_name": ["embedded"],  # Only embedded has this
    "codec_long_name": ["embedded"],  # Only embedded has this
    "profile": ["embedded"],  # Only embedded has this
    "channel_layout": ["embedded"],  # Only embedded has this
    "has_embedded_cover": ["embedded"],  # Only embedded has this
    "cover_codec": ["embedded"],  # Only embedded has this
    "cover_dimensions": ["embedded"],  # Only embedded has this
    "chapter_count": ["embedded", "api", "path"],  # Embedded count > API chapters
    "has_chapters": ["embedded", "api", "path"],  # Embedded detection > API
    "source": ["embedded"],  # Technical source info
    # Hybrid fields
    "album": ["embedded", "api", "path"],  # Embedded album tag > API fallback
    "subtitle": ["api", "embedded"],  # API primary, embedded fallback
    "format": ["embedded", "api", "path"],  # Technical > descriptive
    "encoding": ["embedded", "api", "path"],  # Technical > descriptive
    # List fields (API primary, with smart union from all sources)
    "genres": ["api", "embedded", "path"],  # API primary, union with others
    "tags": ["api", "embedded", "path"],  # API primary, union with others
    "chapters": ["api", "embedded", "path"],  # API structured data > embedded timing
}

# Fields that should be treated as lists for union logic
LIST_FIELDS = {"genres", "tags", "chapters"}


def _is_meaningful(value: Any) -> bool:
    """
    Check if a value contains meaningful content.

    Returns False for None, empty strings (including whitespace-only),
    empty collections, but True for valid scalars and non-empty collections.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _values_for_field(
    candidates: list[dict[str, Any]], field: str, src: str
) -> Any | None:
    """
    Extract field value from candidates matching the specified source.

    Args:
        candidates: List of source metadata dictionaries
        field: Field name to extract
        src: Source identifier to match ("path", "embedded", "api")

    Returns:
        First meaningful value found for the field in the specified source
    """
    for candidate in candidates:
        if candidate.get("_src") == src and field in candidate:
            value = candidate[field]
            if _is_meaningful(value):
                return value
    return None


def _dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    """
    Deduplicate list items while preserving order, case-insensitive.

    Args:
        items: Iterable of string items to deduplicate

    Returns:
        List with duplicates removed, order preserved, empty items filtered
    """
    seen = set()
    result: list[str] = []

    for item in items:
        # Normalize the item
        normalized = item.strip() if isinstance(item, str) else str(item).strip()
        if not normalized:
            continue

        # Case-insensitive deduplication
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            result.append(normalized)

    return result


class FieldMerger:
    """
    Declarative precedence-based metadata merger.

    Features:
    - Scalars: Pick first meaningful value by precedence order
    - Lists: Union with stable order and case-insensitive deduplication
    - Source tracking: All inputs must have "_src" field
    - Configurable: Custom precedence rules can be provided

    Usage:
        merger = FieldMerger()
        result = merger.merge([path_md, embedded_md, api_md])
    """

    def __init__(self, precedence: dict[str, list[str]] | None = None):
        """
        Initialize merger with optional custom precedence rules.

        Args:
            precedence: Dict mapping field names to ordered list of sources.
                       Defaults to DEFAULT_PRECEDENCE if not provided.
        """
        self.precedence = precedence or DEFAULT_PRECEDENCE.copy()

    def merge(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Merge multiple metadata candidates into single result.

        Args:
            candidates: List of metadata dicts, each with "_src" field

        Returns:
            Merged metadata dictionary with resolved precedence

        Raises:
            ValueError: If any candidate is missing "_src" field
        """
        # Validate input
        for candidate in candidates:
            if "_src" not in candidate:
                raise ValueError(f"Candidate missing '_src' field: {candidate}")

        # Collect all possible fields from precedence config and candidates
        fields = set(self.precedence.keys())
        for candidate in candidates:
            fields.update(key for key in candidate.keys() if key != "_src")

        merged: dict[str, Any] = {}

        # Process each field according to its type and precedence
        for field in fields:
            # Get precedence order for this field (fallback to common order)
            order = self.precedence.get(field, ["api", "embedded", "path"])

            if field in LIST_FIELDS:
                # List field: union with stable order
                merged_value = self._merge_list_field(candidates, field, order)
                if merged_value:  # Only include non-empty lists
                    merged[field] = merged_value
            else:
                # Scalar field: pick first meaningful value
                value = self._pick_scalar_field(candidates, field, order)
                if _is_meaningful(value):
                    merged[field] = value

        return merged

    def _pick_scalar_field(
        self, candidates: list[dict[str, Any]], field: str, order: list[str]
    ) -> Scalar | None:
        """
        Pick the first meaningful scalar value according to precedence order.

        Args:
            candidates: List of metadata candidates
            field: Field name to resolve
            order: Precedence order of sources

        Returns:
            First meaningful value found, or None if no meaningful values
        """
        for src in order:
            value = _values_for_field(candidates, field, src)
            if _is_meaningful(value):
                return value
        return None

    def _merge_list_field(
        self, candidates: list[dict[str, Any]], field: str, order: list[str]
    ) -> list[Any]:
        """
        Merge list field values with stable union and deduplication.

        Starts with highest-precedence list, then appends unique items
        from lower-precedence lists. Handles both actual lists and
        comma/semicolon-separated strings.

        Args:
            candidates: List of metadata candidates
            field: Field name to merge
            order: Precedence order of sources

        Returns:
            Merged list with stable order and no duplicates
        """
        combined_items: list[Any] = []

        for src in order:
            value = _values_for_field(candidates, field, src)
            if not _is_meaningful(value):
                continue

            # Handle different input types
            if isinstance(value, str):
                # Parse comma/semicolon-separated string
                items = [
                    item.strip()
                    for item in value.replace(";", ",").split(",")
                    if item.strip()
                ]
            elif isinstance(value, (list, tuple)):
                # Already a list/tuple
                items = list(value)
            else:
                # Single item, treat as list
                items = [value]

            combined_items.extend(items)

        # Deduplicate while preserving order
        return _dedupe_preserve_order(combined_items)

    def get_precedence_for_field(self, field: str) -> list[str]:
        """
        Get precedence order for a specific field.

        Args:
            field: Field name to look up

        Returns:
            List of sources in precedence order
        """
        return self.precedence.get(field, ["api", "embedded", "path"])

    def set_precedence_for_field(self, field: str, order: list[str]) -> None:
        """
        Override precedence order for a specific field.

        Args:
            field: Field name to configure
            order: New precedence order of sources
        """
        self.precedence[field] = order.copy()

    def add_list_field(self, field: str) -> None:
        """
        Mark a field as a list field for union merging.

        Args:
            field: Field name to treat as list
        """
        global LIST_FIELDS
        LIST_FIELDS = LIST_FIELDS | {field}


# Convenience function for simple usage
def merge_metadata(
    candidates: list[dict[str, Any]], precedence: dict[str, list[str]] | None = None
) -> dict[str, Any]:
    """
    Convenience function to merge metadata with default or custom precedence.

    Args:
        candidates: List of metadata dicts with "_src" fields
        precedence: Optional custom precedence rules

    Returns:
        Merged metadata dictionary
    """
    merger = FieldMerger(precedence)
    return merger.merge(candidates)
