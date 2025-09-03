"""
Redacted (RED) tracker API implementation
"""

import time
import requests
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from rich.console import Console

from .base import TrackerAPI, TrackerConfig

console = Console()
logger = logging.getLogger(__name__)


class RedactedAPI(TrackerAPI):
    """RED tracker API implementation"""

    # RED-specific constants
    RELEASE_TYPES = {
        "ALBUM": 1,
        "SOUNDTRACK": 3,
        "EP": 5,
        "ANTHOLOGY": 6,
        "COMPILATION": 7,
        "SINGLE": 9,
        "LIVE_ALBUM": 11,
        "REMIX": 13,
        "BOOTLEG": 14,
        "INTERVIEW": 15,
        "MIXTAPE": 16,
        "DEMO": 17,
        "CONCERT_RECORDING": 18,
        "DJ_MIX": 19,
        "UNKNOWN": 21,
    }

    def __init__(self, api_key: str, base_url: str = "https://redacted.ch"):
        super().__init__(api_key=api_key)
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "MKTorrent/1.0 (RED API Client)",
                "Authorization": f"Bearer {api_key}",
            }
        )

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests

    def get_tracker_config(self) -> TrackerConfig:
        """Return RED-specific configuration"""
        return TrackerConfig(
            name="Redacted",
            announce_url="https://flacsfor.me/announce",
            api_endpoint="https://redacted.ch",
            source_tag="RED",
            requires_private=True,
            supported_formats=["v1"],  # RED doesn't support v2 yet
            max_path_length=150,  # RED's strict limit
        )

    def _rate_limit(self):
        """Enforce rate limiting between API requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Make an authenticated request to RED API"""
        self._rate_limit()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=data, timeout=timeout)
            elif method.upper() == "POST":
                response = self.session.post(
                    url, data=data, files=files, timeout=timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            result = response.json()

            if result.get("status") == "failure":
                error_msg = result.get("error", "Unknown API error")
                raise Exception(f"RED API error: {error_msg}")

            return result

        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")

    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            result = self._make_request("ajax.php?action=index")
            if result.get("status") == "success":
                console.print("[green]✓ RED API connection successful[/green]")
                return True
            else:
                console.print("[red]✗ RED API connection failed[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ RED API connection failed: {e}[/red]")
            return False

    def search_existing(
        self,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        title: Optional[str] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Search for existing torrents on RED"""
        try:
            search_params = {"action": "browse", "searchstr": ""}

            if artist:
                search_params["artistname"] = artist
            if album:
                search_params["groupname"] = album
            if title:
                search_params["searchstr"] = title

            result = self._make_request("ajax.php", "GET", search_params)

            if result.get("status") == "success" and "response" in result:
                return result["response"].get("results", [])

            return []

        except Exception as e:
            console.print(f"[yellow]Warning: Search failed: {e}[/yellow]")
            return []

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata for RED requirements"""
        errors = []
        warnings = []

        # Required fields for RED
        required_fields = {
            "artists": "Artist information",
            "album": "Album title",
            "year": "Release year",
            "format": "Audio format",
            "encoding": "Audio encoding",
        }

        for field, description in required_fields.items():
            if not metadata.get(field):
                errors.append(f"Missing {description}")

        # Path length check - check the folder name that will be in the torrent, not full path
        if metadata.get("path"):
            path_obj = Path(metadata["path"])
            folder_name = path_obj.name  # Just the folder name, not full path
            if len(folder_name) > self.config.max_path_length:
                errors.append(
                    f"Folder name exceeds RED's {self.config.max_path_length} character limit: {len(folder_name)} chars"
                )
            elif len(folder_name) > self.config.max_path_length * 0.9:  # Warning at 90%
                warnings.append(
                    f"Folder name is close to RED's limit: {len(folder_name)}/{self.config.max_path_length} chars"
                )

        # Format validation
        if metadata.get("format") and metadata["format"] not in [
            "FLAC",
            "MP3",
            "AAC",
            "AC3",
            "DTS",
        ]:
            warnings.append(f"Unusual format: {metadata['format']}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "ready_for_upload": len(errors) == 0,
        }

    def prepare_upload_data(
        self, metadata: Dict[str, Any], torrent_path: Path
    ) -> Dict[str, Any]:
        """Prepare data for RED upload"""

        # Detect release type
        release_type = self._detect_release_type(metadata)

        upload_data = {
            "submit": "true",
            "type": "0",  # Music
            "artists[]": metadata.get("artists", []),
            "groupname": metadata.get("album", ""),
            "year": metadata.get("year", ""),
            "releasetype": release_type,
            "format": metadata.get("format", ""),
            "bitrate": metadata.get("encoding", ""),
            "media": metadata.get("media", "WEB"),
            "tags": ",".join(metadata.get("tags", [])),
            "image": metadata.get("artwork_url", ""),
            "album_desc": metadata.get("description", ""),
            "release_desc": metadata.get("release_notes", ""),
        }

        return upload_data

    def _detect_release_type(self, metadata: Dict[str, Any]) -> int:
        """Detect RED release type from metadata"""
        title = metadata.get("album", "").lower()

        # Check for audiobook first
        if metadata.get("type") == "audiobook":
            return self.RELEASE_TYPES[
                "SOUNDTRACK"
            ]  # RED uses soundtrack for audiobooks

        # Check title patterns
        if any(word in title for word in ["soundtrack", "ost", "score"]):
            return self.RELEASE_TYPES["SOUNDTRACK"]
        elif any(word in title for word in ["ep", "e.p."]):
            return self.RELEASE_TYPES["EP"]
        elif "single" in title:
            return self.RELEASE_TYPES["SINGLE"]
        elif any(word in title for word in ["compilation", "best of", "greatest hits"]):
            return self.RELEASE_TYPES["COMPILATION"]
        elif any(word in title for word in ["live", "concert"]):
            return self.RELEASE_TYPES["LIVE_ALBUM"]
        elif any(word in title for word in ["demo"]):
            return self.RELEASE_TYPES["DEMO"]
        elif "remix" in title:
            return self.RELEASE_TYPES["REMIX"]
        else:
            return self.RELEASE_TYPES["ALBUM"]

    def upload_torrent(
        self, torrent_path: Path, metadata: Dict[str, Any], dry_run: bool = True
    ) -> Dict[str, Any]:
        """Upload torrent to RED"""
        if dry_run:
            console.print("[yellow]DRY RUN: Would upload to RED[/yellow]")
            return {
                "success": True,
                "dry_run": True,
                "message": "Dry run completed",
                "torrent_id": None,
            }

        if not torrent_path.exists():
            raise FileNotFoundError(f"Torrent file not found: {torrent_path}")

        upload_data = self.prepare_upload_data(metadata, torrent_path)

        files = {
            "file_input": (
                "torrent.torrent",
                open(torrent_path, "rb"),
                "application/x-bittorrent",
            )
        }

        try:
            console.print("[cyan]Uploading to RED...[/cyan]")
            result = self._make_request(
                "ajax.php?action=upload",
                "POST",
                data=upload_data,
                files=files,
                timeout=60,
            )

            if result.get("status") == "success":
                torrent_id = result.get("response", {}).get("torrentid")
                console.print(f"[green]✓ Upload successful! ID: {torrent_id}[/green]")
                return {
                    "success": True,
                    "dry_run": False,
                    "torrent_id": torrent_id,
                    "url": f"https://redacted.ch/torrents.php?torrentid={torrent_id}",
                }
            else:
                raise Exception(f"Upload failed: {result.get('error', 'Unknown')}")

        finally:
            if "file_input" in files:
                files["file_input"][1].close()
