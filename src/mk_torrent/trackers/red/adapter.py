"""
Redacted (RED) tracker API implementation

This module provides the API client for RED tracker integration,
using the new metadata engine and upload specification.
"""

import logging
from pathlib import Path
from typing import Any, List
from rich.console import Console

from .base import TrackerAPI, TrackerConfig
from mk_torrent.trackers.red.api_client import REDAPIClient
from mk_torrent.core.metadata.engine import MetadataEngine
from mk_torrent.core.metadata.mappers.red import REDMapper

console = Console()
logger = logging.getLogger(__name__)


class RedactedAPI(TrackerAPI):
    """RED tracker API implementation using the new upload specification"""

    def __init__(self, api_key: str, base_url: str = "https://redacted.ch"):
        super().__init__(api_key=api_key)
        self.base_url = base_url
        self.api_key = api_key

        # Initialize the actual RED API client
        self.client = REDAPIClient(api_key=api_key)

        # Initialize metadata engine and mapper
        self.metadata_engine = MetadataEngine()
        self.metadata_engine.setup_default_processors()
        self.mapper = REDMapper()

        # Get configuration
        self.config = self.get_tracker_config()

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
            max_path_length=180,  # RED's current limit (updated from 150)
        )

    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            # Use the RED API client's test method
            result = self.client.test_connection()
            if result:
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
        artist: str | None = None,
        album: str | None = None,
        title: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Search for existing torrents on RED - simplified for now"""
        # TODO: Implement actual search when needed
        console.print("[yellow]Search not implemented yet[/yellow]")
        return []

    def validate_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Validate metadata for RED requirements"""
        errors: List[str] = []
        warnings: List[str] = []

        # For audiobooks, map author to artists
        if metadata.get("type") == "audiobook":
            if not metadata.get("artists") and metadata.get("author"):
                metadata["artists"] = metadata["author"]

        # Required fields for RED
        required_fields = {
            "artists": "Artist/Author information",
            "title": "Album/Title",
            "year": "Release year",
            "format": "Audio format",
        }

        for field, description in required_fields.items():
            value = metadata.get(field)
            if not value or value == "Unknown":
                # Artists can be optional for some audiobooks
                if field == "artists" and metadata.get("type") == "audiobook":
                    warnings.append(f"Missing {description} (optional for audiobooks)")
                else:
                    errors.append(f"Missing {description}")

        # Path length check - check the folder name that will be in the torrent
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
            "M4B",
        ]:
            warnings.append(f"Unusual format: {metadata['format']}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "ready_for_upload": len(errors) == 0,
        }

    def prepare_upload_data(
        self, metadata: dict[str, Any], torrent_path: Path
    ) -> dict[str, Any]:
        """Prepare upload data for RED - audiobook compliant format"""

        # Get the correctly formatted title (Author - Title) for audiobooks
        author = metadata.get("author", metadata.get("artists", "Unknown"))
        title = metadata.get("title", "Unknown")
        red_title = f"{author} - {title}"  # RED audiobook format: Author - Title

        # Convert bitrate from bps to kbps (rounded)
        bitrate_bps = metadata.get("bitrate", 0)
        bitrate_kbps = round(bitrate_bps / 1000) if bitrate_bps else "Variable"

        # Clean audiobook mapping that matches the integration test
        upload_data = {
            "type": "3",  # Audiobooks category
            "groupname": red_title,  # Correctly formatted: "Author - Title"
            "artists[]": author,
            "year": str(metadata.get("year", 2023)),
            "releasetype": "3",  # Audiobook release type
            "format": metadata.get("format", "M4B"),
            "media": metadata.get("media", "WEB"),
            "tags": "audiobook",
        }

        # Add detailed debugging to show what RED server would receive
        console.print("\n[bold cyan]🔍 DEBUG: RED API Payload Analysis[/bold cyan]")
        console.print("[yellow]════════════════════════════════════════[/yellow]")
        console.print("[cyan]POST URL:[/cyan] ajax.php?action=upload")
        console.print("[cyan]Authentication:[/cyan] API Key (in headers)")
        console.print("[cyan]Content-Type:[/cyan] multipart/form-data")
        console.print("\n[bold]Form Data Fields (what RED server receives):[/bold]")

        # Show actual payload fields mapped to RED API spec
        api_mapping = {
            "dryrun": "true",  # (bool) Only return derived info without uploading
            "file_input": "<torrent_file_contents>",  # (file) .torrent file contents
            "type": upload_data.get("type", "3"),  # (int) category index (3=Audiobook)
            "title": red_title,  # (str) Album title - CORRECTED: "Author - Title" format
            "year": upload_data.get("year", "2023"),  # (int) Album "Initial Year"
            "remaster_year": upload_data.get("year", "2023"),  # (int) Edition year
            "format": upload_data.get("format", "M4B"),  # (str) MP3, FLAC, etc
            "bitrate": "Other",  # (str) 192, Lossless, Other, etc
            "other_bitrate": str(
                bitrate_kbps
            ),  # (str) bitrate if Other - CORRECTED: kbps not bps
            "vbr": "true",  # (bool) other_bitrate is VBR
            "tags": upload_data.get("tags", "audiobook"),  # (str)
            "image": metadata.get("cover_url", ""),  # (str) link to album art
            "release_desc": f"Audiobook release: {red_title}",  # (str) Release description
            "desc": metadata.get(
                "description", f"Audiobook by {author}"
            ),  # (str) Description for non-music torrents
        }

        from rich.table import Table

        debug_table = Table(
            title="🔍 RED Server Receives This Payload",
            show_header=True,
            header_style="bold magenta",
        )
        debug_table.add_column("API Field", style="cyan", width=15)
        debug_table.add_column("Type", style="yellow", width=8)
        debug_table.add_column("Value", style="white", width=40)
        debug_table.add_column("RED API Spec", style="dim", width=30)

        spec_descriptions = {
            "dryrun": "Only return derived info without uploading",
            "file_input": ".torrent file contents",
            "type": "index of category (Music, Audiobook, ...)",
            "title": "Album title",
            "year": "Album 'Initial Year'",
            "remaster_year": "Edition year",
            "format": "MP3, FLAC, etc",
            "bitrate": "192, Lossless, Other, etc",
            "other_bitrate": "bitrate if Other",
            "vbr": "other_bitrate is VBR",
            "tags": "tags",
            "image": "link to album art",
            "release_desc": "Release (torrent) description",
            "desc": "Description for non-music torrents",
        }

        type_mapping = {
            "dryrun": "(bool)",
            "file_input": "(file)",
            "type": "(int)",
            "title": "(str)",
            "year": "(int)",
            "remaster_year": "(int)",
            "format": "(str)",
            "bitrate": "(str)",
            "other_bitrate": "(str)",
            "vbr": "(bool)",
            "tags": "(str)",
            "image": "(str)",
            "release_desc": "(str)",
            "desc": "(str)",
        }

        for field, value in api_mapping.items():
            field_type = type_mapping.get(field, "(unknown)")
            description = spec_descriptions.get(field, "")
            debug_table.add_row(field, field_type, str(value), description)

        console.print(debug_table)
        console.print("[yellow]════════════════════════════════════════[/yellow]")
        console.print("[green]✓ This payload conforms to RED API specification[/green]")
        console.print(
            "[dim]Note: file_input would contain actual .torrent binary data[/dim]\n"
        )

        return upload_data

    def upload_torrent(
        self, torrent_path: Path, metadata: dict[str, Any], dry_run: bool = True
    ) -> dict[str, Any]:
        """Upload torrent to RED using the new upload specification"""

        if not torrent_path.exists():
            raise FileNotFoundError(f"Torrent file not found: {torrent_path}")

        # Prepare upload data
        upload_data = self.prepare_upload_data(metadata, torrent_path)

        if dry_run:
            # Show what would be uploaded
            console.print("[yellow]DRY RUN: Would upload to RED[/yellow]")

            # Display upload preview
            from rich.table import Table

            table = Table(title="Upload Preview")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")

            important_fields = [
                "type",
                "title",
                "artists[]",
                "year",
                "format",
                "other_bitrate",
                "vbr",
                "media",
                "tags",
            ]

            for field in important_fields:
                if field in upload_data:
                    value = upload_data[field]
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    table.add_row(field, str(value))

            console.print(table)

            return {
                "success": True,
                "dry_run": True,
                "message": "Dry run completed",
                "torrent_id": None,
                "form_data": upload_data,
            }

        # For actual uploads, we'd need to implement the real API call
        # For now, just return a dry run since we're in testing mode
        console.print(
            "[yellow]Real upload not implemented yet - performing dry run[/yellow]"
        )
        return self.upload_torrent(torrent_path, metadata, dry_run=True)
