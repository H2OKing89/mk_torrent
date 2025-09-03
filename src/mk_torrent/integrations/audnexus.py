"""
Audnexus API integration module
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import nh3

    NH3_AVAILABLE = True
except ImportError:
    NH3_AVAILABLE = False

logger = logging.getLogger(__name__)


class AudnexusAPI:
    """Audnexus API client for audiobook metadata"""

    def __init__(self, base_url: str = "https://api.audnex.us"):
        self.base_url = base_url
        self.user_agent = "mk_torrent/1.0 (RED metadata processor)"

    async def fetch_book_metadata(self, asin: str) -> Optional[Dict[str, Any]]:
        """Fetch book metadata from Audnexus API using async httpx"""
        if not HTTPX_AVAILABLE:
            logger.warning("HTTPX not available, cannot fetch API data")
            return None

        url = f"{self.base_url}/books/{asin}?update=1"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.info(f"Fetching metadata from Audnexus API: {asin}")
                response = await client.get(
                    url, headers={"User-Agent": self.user_agent}
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Successfully fetched metadata for ASIN: {asin}")
                    return self.normalize_api_response(data)
                elif response.status_code == 404:
                    logger.warning(f"ASIN not found in Audnexus: {asin}")
                    return None
                elif response.status_code == 400:
                    error_data = response.json()
                    logger.warning(
                        f"Audnexus API error: {error_data.get('message', 'Unknown error')}"
                    )
                    return None
                else:
                    logger.warning(
                        f"Audnexus API returned status {response.status_code}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching from Audnexus API for ASIN: {asin}")
            return None
        except Exception as e:
            logger.warning(f"Error fetching from Audnexus API: {e}")
            return None

    def fetch_book_metadata_sync(self, asin: str) -> Optional[Dict[str, Any]]:
        """Synchronous version for backwards compatibility"""
        if not HTTPX_AVAILABLE:
            logger.warning("HTTPX not available, cannot fetch API data")
            return None

        url = f"{self.base_url}/books/{asin}?update=1"

        try:
            with httpx.Client(timeout=10.0) as client:
                logger.info(f"Fetching metadata from Audnexus API: {asin}")
                response = client.get(url, headers={"User-Agent": self.user_agent})

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Successfully fetched metadata for ASIN: {asin}")
                    return self.normalize_api_response(data)
                elif response.status_code == 404:
                    logger.warning(f"ASIN not found in Audnexus: {asin}")
                    return None
                elif response.status_code == 400:
                    error_data = response.json()
                    logger.warning(
                        f"Audnexus API error: {error_data.get('message', 'Unknown error')}"
                    )
                    return None
                else:
                    logger.warning(
                        f"Audnexus API returned status {response.status_code}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching from Audnexus API for ASIN: {asin}")
            return None
        except Exception as e:
            logger.warning(f"Error fetching from Audnexus API: {e}")
            return None

    def normalize_api_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Audnexus API response to metadata format"""
        # Start with ALL raw API data to preserve everything
        metadata = dict(data)

        # Clean HTML content
        if data.get("summary"):
            metadata["summary_cleaned"] = self._clean_html_content(data["summary"])
            metadata["description"] = metadata["summary_cleaned"]

        if data.get("description"):
            metadata["description_cleaned"] = self._clean_html_content(
                data["description"]
            )

        # Extract authors with enhanced information
        authors = data.get("authors", [])
        if authors:
            metadata["authors"] = [
                author.get("name") for author in authors if author.get("name")
            ]
            metadata["authors_detailed"] = authors
            metadata["artist"] = metadata["authors"][0] if metadata["authors"] else None
            metadata["artists"] = metadata["authors"]

        # Extract narrators with enhanced information
        narrators = data.get("narrators", [])
        if narrators:
            metadata["narrators"] = [
                narrator.get("name") for narrator in narrators if narrator.get("name")
            ]
            metadata["narrators_detailed"] = narrators
            metadata["narrator"] = ", ".join(metadata["narrators"])

        # Extract series information
        if data.get("seriesPrimary"):
            series = data["seriesPrimary"]
            metadata["series"] = (
                f"{series.get('name', '')} #{series.get('position', '')}"
            )
            metadata["series_detailed"] = series

        # Extract and format genres
        genres = data.get("genres", [])
        if genres:
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
                metadata["genre"] = genre_names[0]  # Primary genre for RED
                metadata["genres"] = genre_names

            if tags:
                metadata["tags"] = tags

            metadata["genres_detailed"] = genres

        # Format album/title
        if data.get("title") and data.get("subtitle"):
            metadata["album"] = f"{data['title']}: {data['subtitle']}"
        elif data.get("title"):
            metadata["album"] = data["title"]

        # Extract year from release date
        if data.get("releaseDate"):
            try:
                release_date = datetime.fromisoformat(
                    data["releaseDate"].replace("Z", "+00:00")
                )
                metadata["year"] = str(release_date.year)
                metadata["date"] = metadata["year"]
                metadata["release_date_formatted"] = release_date.strftime("%B %d, %Y")
            except Exception as e:
                logger.warning(f"Failed to parse release date: {e}")

        # Format runtime
        if data.get("runtimeLengthMin"):
            runtime_min = data["runtimeLengthMin"]
            hours = runtime_min // 60
            minutes = runtime_min % 60
            metadata["runtime_formatted"] = f"{hours}h {minutes}m"
            metadata["duration"] = f"{hours}.{minutes//6} hours"
            metadata["duration_hours"] = runtime_min / 60

        # Add source tracking
        metadata["audnexus_source"] = True
        metadata["audnexus_fetched_at"] = datetime.now().isoformat()

        return metadata

    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content using modern nh3 library"""
        if not html_content:
            return ""

        if NH3_AVAILABLE:
            # Use modern nh3 for secure HTML sanitization
            cleaned = nh3.clean(html_content, tags=set(), attributes={})
            return cleaned.strip()
        else:
            # Fallback to basic regex cleaning
            import re

            clean_text = re.sub(r"<[^>]+>", "", html_content)
            # Clean common HTML entities
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
            }
            for entity, replacement in entities.items():
                clean_text = clean_text.replace(entity, replacement)
            return re.sub(r"\s+", " ", clean_text.strip())


# Convenience functions
def get_audnexus_metadata(asin: str) -> Optional[Dict[str, Any]]:
    """Convenience function to get metadata synchronously"""
    api = AudnexusAPI()
    return api.fetch_book_metadata_sync(asin)


async def get_audnexus_metadata_async(asin: str) -> Optional[Dict[str, Any]]:
    """Convenience function to get metadata asynchronously"""
    api = AudnexusAPI()
    return await api.fetch_book_metadata(asin)
