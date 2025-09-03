"""
Audnexus API response templates and type definitions
"""

from typing import Dict, Any, List, Optional, TypedDict, Union

# Type definitions for Audnexus API responses


class AuthorData(TypedDict):
    """Author information from Audnexus API"""

    asin: str
    name: str


class NarratorData(TypedDict):
    """Narrator information from Audnexus API"""

    name: str


class GenreData(TypedDict):
    """Genre/tag information from Audnexus API"""

    asin: str
    name: str
    type: str  # "genre" or "tag"


class SeriesData(TypedDict):
    """Series information from Audnexus API"""

    asin: str
    name: str
    position: Union[str, int]


class AudnexusBookResponse(TypedDict, total=False):
    """Complete Audnexus API book response structure"""

    asin: str
    authors: List[AuthorData]
    copyright: int
    description: str
    formatType: str  # "unabridged" or "abridged"
    genres: List[GenreData]
    image: str  # URL to cover image
    isAdult: bool
    isbn: str
    language: str
    literatureType: str  # "fiction" or "non-fiction"
    narrators: List[NarratorData]
    publisherName: str
    rating: str  # "4.9" format
    region: str  # "us", "uk", etc.
    releaseDate: str  # ISO format "2021-05-04T00:00:00.000Z"
    runtimeLengthMin: int
    summary: str  # HTML content
    title: str
    # Optional fields
    subtitle: Optional[str]
    seriesPrimary: Optional[SeriesData]


class AudnexusErrorResponse(TypedDict):
    """Error response structure from Audnexus API"""

    statusCode: int
    error: str
    message: str


# Example responses for reference

EXAMPLE_SUCCESS_RESPONSE: AudnexusBookResponse = {
    "asin": "B08G9PRS1K",
    "authors": [{"asin": "B00G0WYW92", "name": "Andy Weir"}],
    "copyright": 2021,
    "description": "Ryland Grace is the sole survivor on a desperate, last-chance mission - and if he fails, humanity and the Earth itself will perish. Except that right now, he doesn't know that. He can't even remember his own name, let alone the nature of his assignment or how to complete it....",
    "formatType": "unabridged",
    "genres": [
        {"asin": "18580606011", "name": "Science Fiction & Fantasy", "type": "genre"},
        {"asin": "18580628011", "name": "Science Fiction", "type": "tag"},
        {"asin": "18580629011", "name": "Adventure", "type": "tag"},
        {"asin": "18580639011", "name": "Hard Science Fiction", "type": "tag"},
        {"asin": "18580645011", "name": "Space Opera", "type": "tag"},
    ],
    "image": "https://m.media-amazon.com/images/I/91vS2L5YfEL.jpg",
    "isAdult": False,
    "isbn": "9781603935470",
    "language": "english",
    "literatureType": "fiction",
    "narrators": [{"name": "Ray Porter"}],
    "publisherName": "Audible Studios",
    "rating": "4.9",
    "region": "us",
    "releaseDate": "2021-05-04T00:00:00.000Z",
    "runtimeLengthMin": 970,
    "summary": "<p><b><i>Winner of the 2022 Audie Awards' Audiobook of the Year</i></b></p> <p><b><i>Number-One Audible and </i></b><b>New York Times</b><b><i> Audio Best Seller</i></b></p> <p><b><i>More than one million audiobooks sold</i></b></p> <p><b>A lone astronaut must save the earth from disaster in this incredible new science-based thriller from the number-one </b><b><i>New York Times</i></b><b> best-selling author of </b><b><i>The Martian</i></b><b>.</b></p> <p>Ryland Grace is the sole survivor on a desperate, last-chance mission - and if he fails, humanity and the Earth itself will perish.</p> <p>Except that right now, he doesn't know that. He can't even remember his own name, let alone the nature of his assignment or how to complete it.</p> <p>All he knows is that he's been asleep for a very, very long time. And he's just been awakened to find himself millions of miles from home, with nothing but two corpses for company.</p> <p>His crewmates dead, his memories fuzzily returning, he realizes that an impossible task now confronts him. Alone on this tiny ship that's been cobbled together by every government and space agency on the planet and hurled into the depths of space, it's up to him to conquer an extinction-level threat to our species.</p> <p>And thanks to an unexpected ally, he just might have a chance.</p> <p>Part scientific mystery, part dazzling interstellar journey, <i>Project Hail Mary</i> is a tale of discovery, speculation, and survival to rival <i>The Martian</i> - while taking us to places it never dreamed of going.</p> <p>PLEASE NOTE: To accommodate this audio edition, some changes to the original text have been made with the approval of author Andy Weir.</p>",
    "title": "Project Hail Mary",
}

EXAMPLE_ERROR_RESPONSE: AudnexusErrorResponse = {
    "statusCode": 404,
    "error": "Not Found",
    "message": "Book not found",
}

# Field mapping for metadata normalization
AUDNEXUS_TO_METADATA_MAPPING = {
    # Direct mappings
    "asin": "asin",
    "title": "title",
    "isbn": "isbn",
    "language": "language",
    "rating": "rating",
    "region": "region",
    "copyright": "copyright",
    "publisherName": "publisher",
    "formatType": "format_type",
    "literatureType": "literature_type",
    "isAdult": "is_adult",
    "image": "cover_image_url",
    "runtimeLengthMin": "runtime_minutes",
    # Complex mappings (handled in normalize function)
    "authors": "authors",
    "narrators": "narrators",
    "genres": "genres",
    "seriesPrimary": "series",
    "releaseDate": "release_date",
    "summary": "summary",
    "description": "description",
}


# Common field transformations
def normalize_language(language: str) -> str:
    """Normalize language codes"""
    language_map = {
        "english": "en",
        "spanish": "es",
        "french": "fr",
        "german": "de",
        "italian": "it",
        "portuguese": "pt",
        "japanese": "ja",
        "chinese": "zh",
    }
    return language_map.get(language.lower(), language.lower())


def format_runtime(minutes: int) -> Dict[str, Any]:
    """Format runtime from minutes to various formats"""
    hours = minutes // 60
    mins = minutes % 60

    return {
        "runtime_minutes": minutes,
        "runtime_hours": round(minutes / 60, 1),
        "runtime_formatted": f"{hours}h {mins}m",
        "duration": f"{hours}.{mins//6} hours",  # Legacy format
    }
