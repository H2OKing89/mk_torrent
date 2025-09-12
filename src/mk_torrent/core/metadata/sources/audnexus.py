"""
Audnexus API source - Core Modular Metadata System.

Part of the new modular metadata architecture providing authoritative descriptive
metadata from api.audnex.us as the primary source for book information in the
three-source extraction strategy.

Implements the MetadataSource protocol to fetch data from api.audnex.us
following the official API documentation (v1.8.0).

⚠️  AUDNEXUS API FIELD USAGE WARNINGS ⚠️

FIELDS TO PREFER FROM AUDNEXUS:
✅ description, summary, title, author, narrator, publisher, genres
✅ year, asin, isbn, artwork_url, series information
✅ chapter_count, has_chapters (structured data)

CRITICAL WARNING - DESCRIPTION vs SUMMARY:
🚨 API provides BOTH fields with different content:
   - 'description': Often truncated (~200 chars) ending with "..."
   - 'summary': Complete full text content (may be 500+ chars)
   → ALWAYS prefer 'summary' for complete content
   → Use post-processing to select the longer/better field

FIELDS TO AVOID FROM AUDNEXUS:
❌ Technical audio specs (bitrate, sample_rate, channels, duration_sec)
❌ File properties (file_size_bytes, codec, format)
❌ Encoding details - API doesn't have access to actual files

RELIABILITY NOTES:
✅ Very reliable for: Book metadata, descriptions, identifiers
⚠️  Sometimes missing: Narrator info, exact technical specs
❌ Never has: File-specific technical details

Architecture Documentation:
- Source Specification: docs/core/metadata/07.3 — Audnexus Source.md
- Three-Source Strategy: docs/core/metadata/06 — Engine Pipeline.md
- Services Overview: docs/core/metadata/07 — Services Details.md (Section 7.3)

Features:
- Direct dict-based data handling for optimal performance
- Exponential backoff retry logic with tenacity
- TTL caching with cachetools
- Rate limiting with aiolimiter
- HTML sanitization with nh3
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, TypedDict
import re
from datetime import datetime

from ..exceptions import SourceUnavailable
from ..services.html_cleaner import HTMLCleaner

logger = logging.getLogger(__name__)


# Audnexus API Type Definitions (consolidated from integrations/audnexus_types.py)
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
    position: str | int


class AudnexusBookResponse(TypedDict, total=False):
    """Complete Audnexus API book response structure"""

    asin: str
    authors: list[AuthorData]
    copyright: int
    description: str
    formatType: str  # "unabridged" or "abridged"
    genres: list[GenreData]
    image: str  # URL to cover image
    isAdult: bool
    isbn: str
    language: str
    literatureType: str  # "fiction" or "non-fiction"
    narrators: list[NarratorData]
    publisherName: str
    rating: str  # "4.9" format
    region: str  # "us", "uk", etc.
    releaseDate: str  # ISO format "2021-05-04T00:00:00.000Z"
    runtimeLengthMin: int
    summary: str
    title: str
    subtitle: str | None
    seriesPrimary: SeriesData | None


# JSON handling with orjson (preferred) or standard json (fallback)
try:
    import orjson

    json_loads: Callable[[str | bytes], Any] = orjson.loads

    def json_dumps(data: Any) -> str:
        """Dump data to JSON string using orjson."""
        return orjson.dumps(data).decode("utf-8")

    logger.debug("Using orjson for JSON operations")
except ImportError:
    import json

    json_loads = json.loads
    json_dumps = json.dumps  # type: ignore[assignment]
    logger.debug("Using standard json for JSON operations (orjson unavailable)")


class AudnexusSource:
    """
    Enhanced Audnexus API source implementation.

    Features:
    - Fetches audiobook metadata from api.audnex.us following v1.8.0 API spec
    - Direct dict-based data handling for optimal performance
    - Exponential backoff retry logic
    - TTL caching for API responses
    - Rate limiting for polite API usage
    - HTML sanitization for descriptions
    """

    def __init__(
        self,
        base_url: str = "https://api.audnex.us",
        region: str = "us",
        cache_ttl: int = 3600,
        max_cache_size: int = 2048,
        rate_limit_per_second: int = 5,
        timeout: int = 30,
    ):
        """
        Initialize enhanced Audnexus source.

        Args:
            base_url: Base API URL (default: https://api.audnex.us)
            region: Default region code (default: us)
            cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour)
            max_cache_size: Maximum cache entries (default: 2048)
            rate_limit_per_second: API requests per second (default: 5)
            timeout: HTTP timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip("/")
        self.region = region
        self.timeout = timeout
        self._client: Any | None = None
        self._client_type: str = ""

        # Initialize caching
        try:
            from cachetools import TTLCache

            self._cache: TTLCache[str, Any] | dict[str, Any] = TTLCache(
                maxsize=max_cache_size, ttl=cache_ttl
            )
        except ImportError:
            logger.warning("cachetools not available, running without cache")
            self._cache: TTLCache[str, Any] | dict[str, Any] = {}

        # Initialize rate limiter (for async usage)
        self._rate_limit_per_second = rate_limit_per_second
        self._rate_limiter = None
        try:
            from aiolimiter import AsyncLimiter

            self._rate_limiter = AsyncLimiter(
                rate_limit_per_second, 1
            )  # X requests per 1 second
        except ImportError:
            logger.warning("aiolimiter not available, running without rate limiting")

        # Initialize HTML cleaner with paragraph preservation
        self._html_cleaner = HTMLCleaner(preserve_formatting=True)

        # Initialize HTTP client
        self._init_client()

    def __del__(self):
        """Clean up resources when object is destroyed."""
        try:
            self.close()
        except Exception:
            # Ignore exceptions during cleanup
            pass

    def _init_client(self):
        """Initialize HTTP client (httpx preferred, requests fallback)."""
        try:
            import httpx

            self._client = httpx.Client(
                timeout=self.timeout,
                headers={
                    "User-Agent": "mk_torrent/2.0 (Metadata Core)",
                    "Accept": "application/json",
                },
            )
            self._client_type = "httpx"
            logger.debug("Initialized httpx client")
        except ImportError:
            try:
                import requests

                self._client = requests.Session()
                if self._client:
                    self._client.headers.update(
                        {
                            "User-Agent": "mk_torrent/2.0 (Metadata Core)",
                            "Accept": "application/json",
                        }
                    )
                self._client_type = "requests"
                logger.debug("Initialized requests client (httpx unavailable)")
            except ImportError:
                raise SourceUnavailable(
                    "audnexus",
                    "Neither httpx nor requests available",
                    temporary=False,  # Missing dependency - not transient
                )

    def _get_retry_decorator(self) -> Any:
        """Get retry decorator with exponential backoff."""
        try:
            from tenacity import (
                retry,
                stop_after_attempt,
                wait_exponential,
                retry_if_exception_type,
            )

            return retry(
                stop=stop_after_attempt(5),
                wait=wait_exponential(multiplier=0.3, max=5),
                retry=retry_if_exception_type((ConnectionError, TimeoutError)),
                reraise=True,
            )
        except ImportError:
            logger.warning("tenacity not available, running without retry logic")
            return lambda func: func  # type: ignore

    def _make_request(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """Make HTTP request with retry logic and caching."""
        # Check cache first
        cache_key = f"{url}?{hash(str(sorted(params.items())))}"
        if hasattr(self._cache, "get") and cache_key in self._cache:
            logger.debug(f"Cache hit for {url}")
            return self._cache[cache_key]

        # Apply retry logic
        retry_decorator = self._get_retry_decorator()

        @retry_decorator
        def _do_request():
            if not self._client:
                raise SourceUnavailable(
                    "audnexus",
                    "HTTP client not initialized",
                    temporary=False,  # Configuration issue
                )

            if self._client_type == "httpx":
                response = self._client.get(url, params=params)
                response.raise_for_status()
                return json_loads(response.text)
            else:  # requests
                response = self._client.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return json_loads(response.text)

        try:
            result = _do_request()

            # Cache the result
            if hasattr(self._cache, "__setitem__"):
                self._cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")

            # Extract HTTP status code if available
            http_status: int | None = None
            temporary = True  # Default to temporary for network errors

            # Handle different HTTP client error types safely
            if hasattr(e, "response"):
                response = getattr(e, "response", None)
                if response and hasattr(response, "status_code"):
                    http_status = getattr(response, "status_code", None)
            elif hasattr(e, "status_code"):
                http_status = getattr(e, "status_code", None)
            else:
                # Parse status from error message as fallback
                error_str = str(e)
                if "429" in error_str:
                    http_status = 429
                elif "503" in error_str:
                    http_status = 503
                elif "404" in error_str:
                    http_status = 404
                    temporary = False  # Not found is usually permanent

            # Set permanent failure for certain status codes
            if http_status == 404:
                temporary = False

            raise SourceUnavailable(
                "audnexus",
                f"API request failed: {e}",
                temporary=temporary,
                http_status=http_status,
            ) from e

    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content to plain text using HTMLCleaner service."""
        return self._html_cleaner.clean_html(html_content)

    def extract(self, source: str | Path) -> dict[str, Any]:
        """
        Extract metadata from source (ASIN or path containing ASIN).

        Args:
            source: ASIN string or file path containing ASIN pattern

        Returns:
            Dict containing normalized metadata

        Raises:
            SourceUnavailable: If API is unavailable or ASIN not found
        """
        # Extract ASIN from source
        asin = self._extract_asin(str(source))
        if not asin:
            # Try to use source directly as ASIN if it looks like one
            source_str = str(source)
            if self._is_valid_asin(source_str):
                asin = source_str
            else:
                raise SourceUnavailable(
                    "audnexus",
                    f"No ASIN found in source: {source}",
                    temporary=False,  # Invalid input format
                )

        # Fetch book metadata
        try:
            book_data = self._get_book(asin, region=self.region, update=1)
            if not book_data:
                raise SourceUnavailable(
                    "audnexus", f"No metadata found for ASIN: {asin}"
                )

            # Normalize the response
            normalized = self._normalize_book_data(book_data)

            # Try to fetch chapter data (best effort - don't fail if unavailable)
            try:
                chapter_data = self.get_chapters(asin)
                if chapter_data:
                    # Add chapter information to normalized data
                    chapters = chapter_data.get("chapters", [])
                    if chapters:
                        normalized["chapters"] = chapters
                        normalized["chapter_count"] = len(chapters)
                        normalized["has_chapters"] = True

                        # If chapter runtime is more accurate, use it
                        if chapter_data.get("runtimeLengthSec"):
                            normalized["duration_sec"] = chapter_data[
                                "runtimeLengthSec"
                            ]

                        # Add chapter accuracy flag
                        normalized["chapter_accuracy"] = chapter_data.get(
                            "isAccurate", True
                        )
                    else:
                        normalized["has_chapters"] = False
                        normalized["chapter_count"] = 0
                else:
                    normalized["has_chapters"] = False
                    normalized["chapter_count"] = 0
            except Exception as e:
                logger.debug(f"Chapter data unavailable for {asin}: {e}")
                normalized["has_chapters"] = False
                normalized["chapter_count"] = 0

            # Add source information
            normalized.update(
                {
                    "source": "audnexus",
                    "source_asin": asin,
                    "source_url": f"{self.base_url}/books/{asin}",
                    "fetched_at": datetime.now().isoformat(),
                }
            )

            return normalized

        except Exception as e:
            logger.error(f"Failed to extract metadata from Audnexus for {asin}: {e}")
            raise SourceUnavailable("audnexus", f"Extraction failed: {e}") from e

    def _extract_asin(self, text: str) -> str | None:
        """Extract ASIN from text using pattern {ASIN.B0C8ZW5N6Y}."""
        asin_pattern = r"\{ASIN\.([A-Z0-9]{10,12})\}"
        match = re.search(asin_pattern, text)
        return match.group(1) if match else None

    def _is_valid_asin(self, asin: str) -> bool:
        """Check if string looks like a valid ASIN."""
        return bool(re.match(r"^[A-Z0-9]{10,12}$", asin))

    def _get_book(
        self, asin: str, region: str = "us", update: int = 0, seed_authors: int = 0
    ) -> dict[str, Any] | None:
        """
        Get book metadata from Audnexus API.

        Args:
            asin: Audible ASIN
            region: Region code (us, uk, etc.)
            update: Force upstream refresh (0 or 1)
            seed_authors: Seed authors server-side (0 or 1)

        Returns:
            Book data dict or None if not found
        """
        url = f"{self.base_url}/books/{asin}"
        params = {"region": region}

        # Add optional parameters following API spec
        if update:
            params["update"] = str(
                update
            )  # API expects number for book endpoint but params are strings
        if seed_authors:
            params["seedAuthors"] = str(seed_authors)

        try:
            logger.info(f"Fetching book metadata: {asin} (region: {region})")
            return self._make_request(url, params)
        except Exception as e:
            logger.error(f"Failed to fetch book {asin}: {e}")
            return None

    def get_chapters(
        self, asin: str, region: str = "us", update: int = 0
    ) -> dict[str, Any] | None:
        """
        Get chapter information for a book.

        Args:
            asin: Audible ASIN
            region: Region code
            update: Force upstream refresh (0 or 1)

        Returns:
            Chapter data dict or None if not found
        """
        url = f"{self.base_url}/books/{asin}/chapters"
        params = {"region": region}

        if update:
            params["update"] = str(update)

        try:
            logger.info(f"Fetching chapters: {asin}")
            return self._make_request(url, params)
        except Exception as e:
            logger.error(f"Failed to fetch chapters for {asin}: {e}")
            return None

    def search_authors(self, name: str, region: str = "us") -> list[dict[str, Any]]:
        """
        Search for authors by name.

        Args:
            name: Author name to search for
            region: Region code

        Returns:
            List of author data dicts
        """
        url = f"{self.base_url}/authors"
        params = {"name": name, "region": region}

        try:
            logger.info(f"Searching authors: {name}")
            result = self._make_request(url, params)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Author search failed for {name}: {e}")
            return []

    def get_author(
        self, asin: str, region: str = "us", update: str = "0"
    ) -> dict[str, Any] | None:
        """
        Get author details by ASIN.

        Args:
            asin: Author ASIN
            region: Region code
            update: Force refresh ("0" or "1" - note string type for this endpoint)

        Returns:
            Author data dict or None if not found
        """
        url = f"{self.base_url}/authors/{asin}"
        params = {"region": region}

        # Note: Author endpoint expects string "0"/"1" per API spec
        if update and update != "0":
            params["update"] = str(update)

        try:
            logger.info(f"Fetching author: {asin}")
            return self._make_request(url, params)
        except Exception as e:
            logger.error(f"Failed to fetch author {asin}: {e}")
            return None

    def _normalize_book_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize Audnexus book data to our metadata schema.

        Args:
            data: Raw API response data

        Returns:
            Normalized metadata dict
        """
        normalized = {"_src": "audnexus"}

        # Basic fields
        normalized["title"] = data.get("title", "")
        normalized["author"] = self._extract_primary_author(data.get("authors", []))
        authors_list = [
            a.get("name", "") for a in data.get("authors", []) if a.get("name")
        ]
        normalized["authors"] = ", ".join(authors_list) if authors_list else ""

        # Subtitle handling
        subtitle = data.get("subtitle", "")
        if subtitle:
            normalized["subtitle"] = subtitle
            # Create full title with subtitle
            normalized["album"] = f"{normalized['title']}: {subtitle}"
        else:
            normalized["album"] = normalized["title"]

        # Series information
        series_primary = data.get("seriesPrimary")
        if series_primary:
            normalized["series"] = series_primary.get("name", "")
            normalized["volume"] = series_primary.get("position", "")
            if series_primary.get("asin"):
                normalized["series_asin"] = series_primary["asin"]

        # Secondary series
        series_secondary = data.get("seriesSecondary")
        if series_secondary:
            normalized["series_secondary"] = series_secondary.get("name", "")
            normalized["volume_secondary"] = series_secondary.get("position", "")

        # Publication info
        normalized["publisher"] = data.get("publisherName", "")
        normalized["asin"] = data.get("asin", "")
        normalized["isbn"] = data.get("isbn", "")

        # Year from release date or copyright
        if data.get("releaseDate"):
            try:
                release_date = datetime.fromisoformat(
                    data["releaseDate"].replace("Z", "+00:00")
                )
                normalized["year"] = str(release_date.year)
                normalized["release_date"] = release_date.strftime("%Y-%m-%d")
            except Exception:
                normalized["year"] = str(data.get("copyright", ""))
        elif data.get("copyright"):
            normalized["year"] = str(data["copyright"])

        # Narrators
        narrators = data.get("narrators", [])
        if narrators:
            narrator_names = [n.get("name", "") for n in narrators if n.get("name")]
            normalized["narrator"] = ", ".join(narrator_names)
            normalized["narrators"] = ", ".join(narrator_names)

        # Runtime
        runtime_min = data.get("runtimeLengthMin")
        if runtime_min:
            normalized["duration_seconds"] = runtime_min * 60
            hours = runtime_min // 60
            minutes = runtime_min % 60
            normalized["duration"] = f"{hours}h {minutes}m"

        # Genres and tags
        genres = data.get("genres", [])
        if genres:
            genre_names = [
                g.get("name")
                for g in genres
                if g.get("type") == "genre" and g.get("name")
            ]
            tag_names = [
                g.get("name")
                for g in genres
                if g.get("type") == "tag" and g.get("name")
            ]

            if genre_names:
                normalized["genres"] = ", ".join(genre_names)
                normalized["genre"] = genre_names[0]  # Primary genre

            if tag_names:
                normalized["tags"] = ", ".join(tag_names)

        # Format and content info
        normalized["format"] = data.get("formatType", "")  # unabridged/abridged
        normalized["language"] = data.get("language", "")
        normalized["literature_type"] = data.get(
            "literatureType", ""
        )  # fiction/nonfiction

        # Rating and artwork
        if data.get("rating"):
            try:
                normalized["rating"] = str(float(data["rating"]))
            except (ValueError, TypeError):
                normalized["rating"] = str(data["rating"])

        normalized["artwork_url"] = data.get("image", "")

        # Description and summary
        normalized["description"] = self._clean_html(data.get("description", ""))
        normalized["summary"] = self._clean_html(data.get("summary", ""))

        # Adult content flag
        normalized["is_adult"] = data.get("isAdult", False)

        return normalized

    def _extract_primary_author(self, authors: list[dict[str, Any]]) -> str:
        """Extract primary author name from authors list."""
        if not authors:
            return ""

        first_author = authors[0]
        return first_author.get("name", "") if first_author else ""

    def close(self):
        """Close HTTP client connection."""
        if self._client and hasattr(self._client, "close"):
            try:
                self._client.close()
            except Exception as e:
                logger.warning(f"Error closing HTTP client: {e}")
            finally:
                self._client = None

    # Async methods for rate-limited usage
    async def _make_request_async(
        self, url: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Make async HTTP request with rate limiting and caching."""
        # Apply rate limiting if available
        if self._rate_limiter:
            await self._rate_limiter.acquire()

        # Check cache first
        cache_key = f"{url}?{hash(str(sorted(params.items())))}"
        if hasattr(self._cache, "get") and cache_key in self._cache:
            logger.debug(f"Cache hit for {url}")
            return self._cache[cache_key]

        # Make async request
        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = json_loads(response.text)

                # Cache the result
                if hasattr(self._cache, "__setitem__"):
                    self._cache[cache_key] = result

                return result

        except ImportError:
            # Fallback to sync method if httpx not available
            return self._make_request(url, params)
        except Exception as e:
            logger.error(f"Async request failed for {url}: {e}")
            raise SourceUnavailable("audnexus", f"API request failed: {e}")

    async def get_book_async(
        self, asin: str, region: str = "us", update: int = 0, seed_authors: int = 0
    ) -> dict[str, Any] | None:
        """Async version of get_book with rate limiting."""
        url = f"{self.base_url}/books/{asin}"
        params = {"region": region}

        if update:
            params["update"] = str(update)
        if seed_authors:
            params["seedAuthors"] = str(seed_authors)

        try:
            logger.info(f"Fetching book metadata (async): {asin} (region: {region})")
            return await self._make_request_async(url, params)
        except Exception as e:
            logger.error(f"Failed to fetch book {asin} (async): {e}")
            return None

    async def get_chapters_async(
        self, asin: str, region: str = "us", update: int = 0
    ) -> dict[str, Any] | None:
        """Async version of get_chapters with rate limiting."""
        url = f"{self.base_url}/books/{asin}/chapters"
        params = {"region": region}

        if update:
            params["update"] = str(update)

        try:
            logger.info(f"Fetching chapters (async): {asin}")
            return await self._make_request_async(url, params)
        except Exception as e:
            logger.error(f"Failed to fetch chapters for {asin} (async): {e}")
            return None

    async def search_authors_async(
        self, name: str, region: str = "us"
    ) -> list[dict[str, Any]]:
        """Async version of search_authors with rate limiting."""
        url = f"{self.base_url}/authors"
        params = {"name": name, "region": region}

        try:
            logger.info(f"Searching authors (async): {name}")
            result = await self._make_request_async(url, params)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Author search failed for {name} (async): {e}")
            return []

    async def extract_async(self, source: str | Path) -> dict[str, Any]:
        """Async version of extract with rate limiting."""
        # Convert Path to string
        source_str = str(source) if isinstance(source, Path) else source

        # Try to extract ASIN from string
        asin = None
        if self._is_valid_asin(source_str):
            asin = source_str
        else:
            # Look for ASIN pattern in filename/path
            asin = self._extract_asin(source_str)

        if not asin:
            raise SourceUnavailable(
                "audnexus", f"Could not extract valid ASIN from: {source_str}"
            )

        # Fetch book metadata
        try:
            book_data = await self.get_book_async(asin, region=self.region, update=1)
            if not book_data:
                raise SourceUnavailable(
                    "audnexus", f"No metadata found for ASIN: {asin}"
                )

            # Normalize the response
            normalized = self._normalize_book_data(book_data)

            # Add source information
            normalized.update(
                {
                    "source": "audnexus",
                    "source_asin": asin,
                    "source_url": f"{self.base_url}/books/{asin}",
                    "fetched_at": datetime.now().isoformat(),
                }
            )

            return normalized

        except Exception as e:
            logger.error(
                f"Failed to extract metadata from Audnexus for {asin} (async): {e}"
            )
            raise SourceUnavailable("audnexus", f"Extraction failed: {e}") from e


# Convenience functions for backward compatibility and ease of use
def get_audnexus_metadata(asin: str) -> dict[str, Any] | None:
    """
    Convenience function to get metadata synchronously.

    Args:
        asin: Amazon Standard Identification Number

    Returns:
        Normalized metadata dictionary or None if failed
    """
    source = AudnexusSource()
    try:
        # Use extract method with ASIN directly
        return source.extract(asin)
    except Exception:
        return None
    finally:
        source.close()


async def get_audnexus_metadata_async(asin: str) -> dict[str, Any] | None:
    """
    Convenience function to get metadata asynchronously.

    Args:
        asin: Amazon Standard Identification Number

    Returns:
        Normalized metadata dictionary or None if failed
    """
    source = AudnexusSource()
    try:
        return await source.extract_async(asin)
    except Exception:
        return None
    finally:
        source.close()


def extract_asin_from_path(path: str | Path) -> str | None:
    """
    Convenience function to extract ASIN from path.

    Args:
        path: File path that may contain ASIN pattern {ASIN.B0C8ZW5N6Y}

    Returns:
        ASIN string if found, None otherwise
    """
    # Use regex directly since it's a simple pattern
    asin_pattern = r"\{ASIN\.([A-Z0-9]{10,12})\}"
    match = re.search(asin_pattern, str(path))
    return match.group(1) if match else None


# Export consolidated API
__all__ = [
    # Main class
    "AudnexusSource",
    # Type definitions
    "AuthorData",
    "NarratorData",
    "GenreData",
    "SeriesData",
    "AudnexusBookResponse",
    # Convenience functions
    "get_audnexus_metadata",
    "get_audnexus_metadata_async",
    "extract_asin_from_path",
]
