"""
Common validation primitives and utilities.

Basic validation functions that can be reused across different content types.
These provide the building blocks for more complex validators.
"""

from __future__ import annotations
import re
from datetime import datetime
from typing import Any


def is_year(value: Any) -> bool:
    """Check if value is a valid year (1800-2100)."""
    try:
        year = int(value)
        return 1800 <= year <= 2100
    except (ValueError, TypeError):
        return False


def is_language_iso(value: Any) -> bool:
    """Check if value is a valid ISO 639-1 language code."""
    # Common language codes - extend as needed
    valid_codes = {
        "en",
        "es",
        "fr",
        "de",
        "it",
        "pt",
        "ru",
        "ja",
        "ko",
        "zh",
        "ar",
        "hi",
        "tr",
        "pl",
        "nl",
        "sv",
        "da",
        "no",
        "fi",
        "he",
    }
    if not isinstance(value, str):
        return False
    return value.lower() in valid_codes


def duration_sanity(value: Any) -> bool:
    """Check if duration is reasonable (30 seconds to 200 hours)."""
    try:
        duration = float(value)
        # 30 seconds to 200 hours (720,000 seconds)
        return 30 <= duration <= 720000
    except (ValueError, TypeError):
        return False


def non_empty(value: Any) -> bool:
    """Check if value is not empty/None/whitespace."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)  # type: ignore[arg-type]
    return True


def is_valid_asin(value: Any) -> bool:
    """Check if value looks like a valid Amazon ASIN.

    Accepts any input, but only string values will be validated.
    """
    # ASIN is typically 10 characters, alphanumeric
    # Pattern: B followed by 9 alphanumeric characters
    if not isinstance(value, str):
        return False
    asin_pattern = re.compile(r"^B[A-Z0-9]{9}$")
    return bool(asin_pattern.match(value.upper()))


def is_valid_isbn(value: Any) -> bool:
    """Check if value looks like a valid ISBN (10 or 13 digits)."""
    if not isinstance(value, str):
        return False
    # Remove hyphens and spaces
    clean_isbn = re.sub(r"[-\s]", "", value)

    # Check for 10 or 13 digit ISBN
    if len(clean_isbn) == 10:
        return clean_isbn[:-1].isdigit() and (
            clean_isbn[-1].isdigit() or clean_isbn[-1].upper() == "X"
        )
    elif len(clean_isbn) == 13:
        return clean_isbn.isdigit()

    return False


def normalize_volume(value: Any) -> str | None:
    """Normalize volume to zero-padded string (e.g., '03', '12')."""
    if value is None:
        return None

    try:
        # Extract numeric part
        if isinstance(value, str):
            # Handle formats like "vol_03", "Volume 3", "03", etc.
            match = re.search(r"(\d+)", value)
            if match:
                num = int(match.group(1))
            else:
                return None
        else:
            num = int(value)

        # Zero-pad to 2 digits
        return f"{num:02d}"
    except (ValueError, TypeError):
        return None


def validate_year_drift(
    value: Any, max_future_years: int = 2
) -> tuple[bool, str | None]:
    """
    Check if year is reasonable, allowing some future drift.

    Returns (is_valid, warning_message)
    """
    if not is_year(value):
        return False, "Invalid year format"

    year = int(value)
    current_year = datetime.now().year

    if year > current_year + max_future_years:
        return True, f"Year {year} is unusually far in the future"
    elif year < 1900:
        return True, f"Year {year} is very old, please verify"

    return True, None


def clean_genre_tags(tags: list[Any]) -> list[str]:
    """
    Normalize genre/tag list: lowercase, dedupe, ASCII-friendly.

    Args:
        tags: List of genre/tag strings (non-string values are ignored)

    Returns:
        Cleaned and normalized list
    """
    cleaned: list[str] = []
    seen: set[str] = set()

    for tag in tags:
        if not isinstance(tag, str):
            continue
        # Clean and normalize
        normalized = tag.strip().lower()
        if normalized and normalized not in seen:
            cleaned.append(normalized)
            seen.add(normalized)

    return sorted(cleaned)


def estimate_completeness(
    metadata: dict[str, Any], required_fields: list[str], recommended_fields: list[str]
) -> float:
    """
    Calculate completeness score based on required and recommended fields.

    Args:
        metadata: Dictionary of metadata fields
        required_fields: List of required field names
        recommended_fields: List of recommended field names

    Returns:
        Completeness score between 0.0 and 1.0
    """
    total_possible = len(required_fields) + len(recommended_fields)
    if total_possible == 0:
        return 1.0

    score = 0

    # Required fields worth more
    for field in required_fields:
        if non_empty(metadata.get(field)):
            score += 2  # Required fields worth 2 points

    # Recommended fields worth less
    for field in recommended_fields:
        if non_empty(metadata.get(field)):
            score += 1  # Recommended fields worth 1 point

    max_score = len(required_fields) * 2 + len(recommended_fields) * 1
    return min(1.0, score / max_score) if max_score > 0 else 1.0
