"""
Metadata validation modules.

Validators check metadata completeness and correctness:
- common: Basic validation primitives
- audiobook_validator: Audiobook-specific validation with RED compliance
"""

from .audiobook_validator import validate_audiobook
from .common import (
    is_year,
    is_language_iso,
    duration_sanity,
    non_empty,
    is_valid_asin,
    is_valid_isbn,
    normalize_volume,
    validate_year_drift,
    clean_genre_tags,
    estimate_completeness,
)

__all__ = [
    "validate_audiobook",
    "is_year",
    "is_language_iso",
    "duration_sanity",
    "non_empty",
    "is_valid_asin",
    "is_valid_isbn",
    "normalize_volume",
    "validate_year_drift",
    "clean_genre_tags",
    "estimate_completeness",
]
