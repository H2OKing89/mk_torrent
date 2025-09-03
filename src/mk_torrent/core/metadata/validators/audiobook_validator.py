"""
Audiobook-specific validation with tracker-agnostic checks and RED-specific hints.

Provides comprehensive validation for audiobook metadata, including both
general content validation and tracker-specific requirements.
"""

from typing import Dict, List, Any
from .common import (
    non_empty,
    is_year,
    duration_sanity,
    is_valid_asin,
    is_valid_isbn,
    is_language_iso,
    normalize_volume,
    validate_year_drift,
    clean_genre_tags,
    estimate_completeness,
)


def validate_audiobook(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate audiobook metadata with tracker-agnostic and RED-specific checks.

    Args:
        metadata: Dictionary containing audiobook metadata

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str],
            "completeness": float (0.0-1.0)
        }
    """
    errors = []
    warnings = []

    # Required fields (RED compliance)
    required_fields = ["title", "author"]

    # Recommended fields for better completeness
    recommended_fields = [
        "year",
        "narrator",
        "duration_sec",
        "asin",
        "album",
        "publisher",
        "description",
        "format",
        "encoding",
    ]

    # Check required fields
    for field in required_fields:
        if not non_empty(metadata.get(field)):
            errors.append(f"Missing required field: {field}")

    # Validate specific fields
    _validate_title(metadata, errors, warnings)
    _validate_author(metadata, errors, warnings)
    _validate_album(metadata, errors, warnings)
    _validate_year(metadata, errors, warnings)
    _validate_duration(metadata, errors, warnings)
    _validate_format_encoding(metadata, errors, warnings)
    _validate_identifiers(metadata, errors, warnings)
    _validate_volume_series(metadata, errors, warnings)
    _validate_narrator(metadata, errors, warnings)
    _validate_publisher_description(metadata, errors, warnings)
    _validate_language(metadata, errors, warnings)
    _validate_genres_tags(metadata, errors, warnings)

    # RED-specific validation hints
    _validate_red_compliance(metadata, warnings)

    # Calculate completeness score
    completeness = estimate_completeness(metadata, required_fields, recommended_fields)

    # Overall validity (no errors)
    is_valid = len(errors) == 0

    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "completeness": completeness,
    }


def _validate_title(metadata: Dict, errors: List[str], warnings: List[str]) -> None:
    """Validate title field."""
    title = metadata.get("title", "")

    if non_empty(title):
        if len(title) > 200:
            warnings.append("Title is very long (>200 chars), may cause display issues")
        if title.strip() != title:
            warnings.append("Title has leading/trailing whitespace")


def _validate_author(metadata: Dict, errors: List[str], warnings: List[str]) -> None:
    """Validate author field."""
    author = metadata.get("author", "")

    if non_empty(author):
        if len(author) > 100:
            warnings.append("Author name is very long (>100 chars)")
        if author.strip() != author:
            warnings.append("Author has leading/trailing whitespace")


def _validate_album(metadata: Dict, errors: List[str], warnings: List[str]) -> None:
    """Validate album field (RED wants this present)."""
    album = metadata.get("album", "")
    title = metadata.get("title", "")

    # RED expects album field - if empty, should default to title
    if not non_empty(album) and non_empty(title):
        warnings.append(
            "Album field empty - should default to title for RED compliance"
        )


def _validate_year(metadata: Dict, errors: List[str], warnings: List[str]) -> None:
    """Validate year field."""
    year = metadata.get("year")

    if year is not None:
        if not is_year(year):
            errors.append(f"Invalid year: {year}")
        else:
            is_valid, warning_msg = validate_year_drift(year)
            if warning_msg:
                warnings.append(warning_msg)
    else:
        warnings.append("Year not provided - recommended for tracker compliance")


def _validate_duration(metadata: Dict, errors: List[str], warnings: List[str]) -> None:
    """Validate duration field."""
    duration = metadata.get("duration_sec")

    if duration is not None:
        if not duration_sanity(duration):
            errors.append(f"Invalid duration: {duration} seconds")
        elif duration < 300:  # 5 minutes
            warnings.append("Very short duration for an audiobook")
        elif duration > 180000:  # 50 hours
            warnings.append("Very long duration for an audiobook")
    else:
        warnings.append("Duration not provided - recommended for quality assessment")


def _validate_format_encoding(
    metadata: Dict, errors: List[str], warnings: List[str]
) -> None:
    """Validate format and encoding fields."""
    format_val = metadata.get("format", "")
    encoding = metadata.get("encoding", "")

    valid_formats = {"AAC", "MP3", "FLAC", "M4A", "M4B", "OGG"}

    if non_empty(format_val):
        if format_val.upper() not in valid_formats:
            warnings.append(f"Uncommon audio format: {format_val}")
    else:
        warnings.append("Audio format not specified")

    if non_empty(encoding):
        # Check for reasonable encoding values
        if (
            "kbps" not in encoding.lower()
            and "lossless" not in encoding.lower()
            and "v" not in encoding.lower()
        ):
            warnings.append(f"Encoding format unclear: {encoding}")


def _validate_identifiers(
    metadata: Dict, errors: List[str], warnings: List[str]
) -> None:
    """Validate ASIN and ISBN identifiers."""
    asin = metadata.get("asin", "")
    isbn = metadata.get("isbn", "")

    if non_empty(asin):
        if not is_valid_asin(asin):
            warnings.append(f"ASIN format looks invalid: {asin}")
    else:
        warnings.append("ASIN not provided - helpful for metadata enrichment")

    if non_empty(isbn):
        if not is_valid_isbn(isbn):
            warnings.append(f"ISBN format looks invalid: {isbn}")


def _validate_volume_series(
    metadata: Dict, errors: List[str], warnings: List[str]
) -> None:
    """Validate volume and series fields."""
    volume = metadata.get("volume", "")
    series = metadata.get("series", "")

    if non_empty(volume):
        normalized = normalize_volume(volume)
        if normalized is None:
            warnings.append(f"Volume format unclear: {volume}")
        elif normalized != volume:
            warnings.append(f"Volume should be zero-padded: {volume} → {normalized}")

    if non_empty(series) and non_empty(volume):
        # Good - series with volume
        pass
    elif non_empty(volume) and not non_empty(series):
        warnings.append("Volume specified but no series name")


def _validate_narrator(metadata: Dict, errors: List[str], warnings: List[str]) -> None:
    """Validate narrator field."""
    narrator = metadata.get("narrator", "")

    if non_empty(narrator):
        if len(narrator) > 200:
            warnings.append("Narrator field very long (>200 chars)")

        # Check for multiple narrators (common pattern)
        if "," in narrator or " and " in narrator or "&" in narrator:
            warnings.append("Multiple narrators detected - consider list format")
    else:
        warnings.append("Narrator not specified - important for audiobook metadata")


def _validate_publisher_description(
    metadata: Dict, errors: List[str], warnings: List[str]
) -> None:
    """Validate publisher and description fields."""
    publisher = metadata.get("publisher", "")
    description = metadata.get("description", "")

    if non_empty(publisher):
        if len(publisher) > 100:
            warnings.append("Publisher name very long (>100 chars)")

    if non_empty(description):
        if len(description) < 50:
            warnings.append("Description quite short - consider enriching")
        elif len(description) > 5000:
            warnings.append("Description very long - may need trimming")

        # Check for HTML tags (should be cleaned)
        if "<" in description and ">" in description:
            warnings.append("Description contains HTML tags - should be cleaned")


def _validate_language(metadata: Dict, errors: List[str], warnings: List[str]) -> None:
    """Validate language field."""
    language = metadata.get("language", "")

    if non_empty(language):
        if not is_language_iso(language):
            warnings.append(f"Language code may be invalid: {language}")
    else:
        # Default to English is acceptable
        pass


def _validate_genres_tags(
    metadata: Dict, errors: List[str], warnings: List[str]
) -> None:
    """Validate genres and tags fields."""
    genres = metadata.get("genres", [])
    tags = metadata.get("tags", [])

    if isinstance(genres, list):
        if len(genres) == 0:
            warnings.append("No genres specified - helpful for categorization")
        elif len(genres) > 10:
            warnings.append("Many genres specified - consider consolidating")

        cleaned_genres = clean_genre_tags(genres)
        if cleaned_genres != genres:
            warnings.append("Genres could be normalized (case, duplicates)")

    if isinstance(tags, list) and len(tags) > 20:
        warnings.append("Many tags specified - may be excessive")


def _validate_red_compliance(metadata: Dict, warnings: List[str]) -> None:
    """Add RED-specific validation hints."""
    title = metadata.get("title", "")
    album = metadata.get("album", "")

    # RED prefers album field to be present
    if non_empty(title) and not non_empty(album):
        warnings.append("RED tracker expects 'album' field - should default to title")

    # RED likes specific metadata fields
    red_recommended = ["year", "narrator", "publisher", "description"]
    missing_red = [
        field for field in red_recommended if not non_empty(metadata.get(field))
    ]

    if missing_red:
        warnings.append(f"RED recommends these fields: {', '.join(missing_red)}")

    # Format preferences for RED
    format_val = metadata.get("format", "").upper()
    encoding = metadata.get("encoding", "")

    if format_val == "M4B":
        # M4B is good for audiobooks
        pass
    elif format_val in ["MP3", "AAC"]:
        if not non_empty(encoding):
            warnings.append("MP3/AAC uploads to RED should specify encoding quality")
    elif format_val == "FLAC":
        warnings.append("FLAC audiobooks are rare - verify this is correct")


# Export main validation function
__all__ = ["validate_audiobook"]
