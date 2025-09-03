"""
Audnexus API integration module
Handles communication with https://api.audnex.us for audiobook metadata
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import logging
import re
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AudnexusAuthor:
    """Audnexus author information"""

    asin: str
    name: str


@dataclass
class AudnexusNarrator:
    """Audnexus narrator information"""

    name: str


@dataclass
class AudnexusGenre:
    """Audnexus genre/tag information"""

    asin: str
    name: str
    type: str  # 'genre' or 'tag'


@dataclass
class AudnexusResponse:
    """Complete Audnexus API response structure"""

    asin: str
    title: str
    authors: List[AudnexusAuthor]
    copyright: int
    description: str
    formatType: str  # 'unabridged' or 'abridged'
    genres: List[AudnexusGenre]
    image: str
    isAdult: bool
    isbn: str
    language: str
    literatureType: str  # 'fiction' or 'non-fiction'
    narrators: List[AudnexusNarrator]
    publisherName: str
    rating: str
    region: str
    releaseDate: str
    runtimeLengthMin: int
    summary: str

    # Optional fields that may not always be present
    subtitle: Optional[str] = None
    seriesPrimary: Optional[Dict[str, Any]] = None


@dataclass
class AudnexusError:
    """Audnexus API error response"""

    statusCode: int
    error: str
    message: str


class AudnexusClient:
    """Client for Audnexus API interactions"""

    def __init__(self, base_url: str = "https://api.audnex.us"):
        self.base_url = base_url
        self.session = None
        self._init_client()

    def _init_client(self):
        """Initialize HTTPX client"""
        try:
            import httpx

            self.session = httpx.Client(
                timeout=10.0,
                headers={
                    "User-Agent": "mk_torrent/1.0 (RED metadata processor)",
                    "Accept": "application/json",
                },
            )
        except ImportError:
            logger.warning("HTTPX not available, falling back to requests")
            try:
                import requests

                self.session = requests.Session()
                self.session.headers.update(
                    {
                        "User-Agent": "mk_torrent/1.0 (RED metadata processor)",
                        "Accept": "application/json",
                    }
                )
            except ImportError:
                logger.error("Neither HTTPX nor requests available for API calls")
                self.session = None

    def extract_asin_from_path(self, path: Union[str, Path]) -> Optional[str]:
        """Extract ASIN from filename or path pattern {ASIN.B0C8ZW5N6Y}"""
        asin_pattern = r"\{ASIN\.([A-Z0-9]{10,12})\}"
        match = re.search(asin_pattern, str(path))
        return match.group(1) if match else None

    async def get_book_metadata_async(self, asin: str) -> Optional[Dict[str, Any]]:
        """Fetch book metadata asynchronously (if httpx is available)"""
        if not self.session:
            return None

        try:
            import httpx

            if isinstance(self.session, httpx.Client):
                # Use async client
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{self.base_url}/books/{asin}?update=1",
                        headers={
                            "User-Agent": "mk_torrent/1.0 (RED metadata processor)",
                            "Accept": "application/json",
                        },
                    )
                    return self._process_response(response)
        except ImportError:
            pass

        # Fallback to sync
        return self.get_book_metadata(asin)

    def get_book_metadata(self, asin: str) -> Optional[Dict[str, Any]]:
        """Fetch book metadata from Audnexus API"""
        if not self.session:
            logger.error("No HTTP client available")
            return None

        try:
            url = f"{self.base_url}/books/{asin}?update=1"
            logger.info(f"Fetching Audnexus metadata: {asin}")

            response = self.session.get(url, timeout=10)
            return self._process_response(response)

        except Exception as e:
            logger.warning(f"Failed to fetch Audnexus metadata for {asin}: {e}")
            return None

    def _process_response(self, response) -> Optional[Dict[str, Any]]:
        """Process HTTP response from Audnexus API"""
        try:
            if response.status_code == 200:
                data = response.json()
                logger.info("Successfully fetched Audnexus metadata")
                return self._normalize_response(data)
            elif response.status_code == 404:
                logger.warning("ASIN not found in Audnexus database")
                return None
            elif response.status_code == 400:
                error_data = response.json()
                logger.warning(
                    f"Audnexus API error: {error_data.get('message', 'Bad request')}"
                )
                return None
            else:
                logger.warning(f"Audnexus API returned status {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Failed to process Audnexus response: {e}")
            return None

    def _normalize_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and enhance Audnexus API response"""
        try:
            # Start with all raw API data
            normalized = dict(data)

            # Extract and normalize authors
            if data.get("authors"):
                authors = data["authors"]
                normalized["authors_detailed"] = authors
                normalized["authors"] = [
                    author.get("name") for author in authors if author.get("name")
                ]
                normalized["artist"] = (
                    normalized["authors"][0] if normalized["authors"] else None
                )

            # Extract and normalize narrators
            if data.get("narrators"):
                narrators = data["narrators"]
                normalized["narrators_detailed"] = narrators
                normalized["narrators"] = [
                    narrator.get("name")
                    for narrator in narrators
                    if narrator.get("name")
                ]
                normalized["narrator"] = (
                    ", ".join(normalized["narrators"])
                    if normalized["narrators"]
                    else None
                )

            # Extract and normalize series information
            if data.get("seriesPrimary"):
                series = data["seriesPrimary"]
                normalized["series_detailed"] = series
                normalized["series"] = {
                    "name": series.get("name"),
                    "position": series.get("position"),
                    "asin": series.get("asin"),
                }

            # Extract and categorize genres
            if data.get("genres"):
                genres = data["genres"]
                normalized["genres_detailed"] = genres

                genre_names = []
                tags = []

                for genre in genres:
                    genre_type = genre.get("type", "").lower()
                    genre_name = genre.get("name")

                    if genre_name:
                        if genre_type == "genre":
                            genre_names.append(genre_name)
                        elif genre_type == "tag":
                            tags.append(genre_name)

                if genre_names:
                    normalized["genre"] = genre_names[0]  # Primary genre for RED
                    normalized["genres"] = genre_names

                if tags:
                    normalized["tags"] = tags

            # Format title/album for RED compliance
            if data.get("title") and data.get("subtitle"):
                normalized["album"] = f"{data['title']}: {data['subtitle']}"
            elif data.get("title"):
                normalized["album"] = data["title"]

            # Extract year from release date
            if data.get("releaseDate"):
                try:
                    release_date = datetime.fromisoformat(
                        data["releaseDate"].replace("Z", "+00:00")
                    )
                    normalized["year"] = str(release_date.year)
                    normalized["date"] = normalized["year"]
                    normalized["release_date_formatted"] = release_date.strftime(
                        "%B %d, %Y"
                    )
                except (ValueError, AttributeError):
                    pass
            elif data.get("copyright"):
                normalized["year"] = str(data["copyright"])
                normalized["date"] = normalized["year"]

            # Format runtime
            if data.get("runtimeLengthMin"):
                runtime_min = data["runtimeLengthMin"]
                hours = runtime_min // 60
                minutes = runtime_min % 60
                normalized["runtime_formatted"] = f"{hours}h {minutes}m"
                normalized["duration"] = f"{hours}.{minutes//6} hours"  # Decimal hours
                normalized["duration_hours"] = hours + (minutes / 60)

            # Clean HTML from summary and description
            if data.get("summary"):
                normalized["summary_cleaned"] = self._clean_html_content(
                    data["summary"]
                )
                normalized["description"] = normalized["summary_cleaned"]

            if data.get("description") and not normalized.get("description"):
                normalized["description"] = self._clean_html_content(
                    data["description"]
                )

            # Add metadata about the API source
            normalized["audnexus_source"] = True
            normalized["audnexus_fetched_at"] = datetime.now().isoformat()

            # Set RED-compatible fields
            if normalized.get("authors") and not normalized.get("artists"):
                normalized["artists"] = normalized["authors"]

            return normalized

        except Exception as e:
            logger.error(f"Failed to normalize Audnexus response: {e}")
            return data  # Return raw data if normalization fails

    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content from API responses"""
        if not html_content:
            return ""

        try:
            # Try modern nh3 library first
            import nh3

            cleaned = nh3.clean(html_content, tags=set(), attributes={})
            return cleaned.strip()
        except ImportError:
            # Fallback to basic HTML tag removal
            clean_text = re.sub(r"<[^>]+>", "", html_content)
            # Clean HTML entities
            entities = {
                "&amp;": "&",
                "&lt;": "<",
                "&gt;": ">",
                "&quot;": '"',
                "&#39;": "'",
                "&apos;": "'",
                "&nbsp;": " ",
                "&mdash;": "—",
                "&ndash;": "–",
                "&hellip;": "…",
                "&copy;": "©",
                "&reg;": "®",
            }
            for entity, replacement in entities.items():
                clean_text = clean_text.replace(entity, replacement)
            return re.sub(r"\s+", " ", clean_text.strip())

    def validate_response(self, data: Dict[str, Any]) -> bool:
        """Validate that API response has required fields"""
        required_fields = ["asin", "title"]
        return all(data.get(field) for field in required_fields)

    def close(self):
        """Close the HTTP session"""
        if self.session:
            if hasattr(self.session, "close"):
                self.session.close()


# Global client instance
_audnexus_client = None


def get_audnexus_client() -> AudnexusClient:
    """Get global Audnexus client instance"""
    global _audnexus_client
    if _audnexus_client is None:
        _audnexus_client = AudnexusClient()
    return _audnexus_client


def fetch_metadata_by_asin(asin: str) -> Optional[Dict[str, Any]]:
    """Convenience function to fetch metadata by ASIN"""
    client = get_audnexus_client()
    return client.get_book_metadata(asin)


def extract_asin_from_path(path: Union[str, Path]) -> Optional[str]:
    """Convenience function to extract ASIN from path"""
    client = get_audnexus_client()
    return client.extract_asin_from_path(path)
