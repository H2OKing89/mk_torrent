"""
MyAnonamouse (MAM) tracker implementation

NOTE: MAM does not support API uploads. This adapter is for torrent creation
and metadata validation only. Torrents must be uploaded manually through
MAM's web interface.

This module supports:
- Torrent creation with proper MAM source tag
- Metadata validation for MAM requirements
- Configuration for MAM announce URL

This module does NOT support:
- Automatic upload (MAM has no API)
- Upload testing or dry runs
- Authentication or login
"""

from pathlib import Path
from typing import Any
from rich.console import Console

from mk_torrent.trackers.base import TrackerAPI, TrackerConfig

console = Console()


class MyAnonaMouseAPI(TrackerAPI):
    """
    MAM tracker implementation for torrent creation only.

    IMPORTANT: MAM does not support API uploads. This class only provides:
    - Torrent creation with proper MAM announce URL and source tag
    - Metadata validation for MAM requirements
    - Configuration information

    Torrents must be uploaded manually through MAM's web interface.
    """

    def __init__(
        self,
        username: str = "",  # Not used - MAM has no API auth
        password: str = "",  # Not used - MAM has no API auth
        base_url: str = "https://www.myanonamouse.net",
    ):
        """
        Initialize MAM adapter (torrent creation only).

        Note: username/password are not used as MAM has no upload API.
        They're kept for interface compatibility but can be empty strings.
        """
        super().__init__(api_key="")  # No API key needed
        self.base_url = base_url

    def get_tracker_config(self) -> TrackerConfig:
        """Return MAM-specific configuration"""
        return TrackerConfig(
            name="MyAnonamouse",
            announce_url="https://tracker.myanonamouse.net/announce",
            api_endpoint="https://www.myanonamouse.net",
            source_tag="MAM",
            requires_private=True,
            supported_formats=["v1", "v2"],
            max_path_length=255,  # MAM is more lenient
        )

    def test_connection(self) -> bool:
        """
        MAM connection test - always returns False.

        MAM does not provide an API for authentication testing.
        Manual verification through web interface is required.
        """
        console.print("[yellow]⚠️  MAM does not support API connections[/yellow]")
        console.print("[dim]Torrents must be uploaded manually via web interface[/dim]")
        return False

    def search_existing(
        self,
        artist: str | None = None,
        album: str | None = None,
        title: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Search for existing torrents - not supported by MAM API.

        MAM does not provide a public search API.
        Manual search through web interface is required.
        """
        console.print("[yellow]⚠️  MAM does not support API search[/yellow]")
        console.print("[dim]Manual search through web interface required[/dim]")
        return []

    def validate_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Validate metadata for MAM requirements (torrent creation only)."""
        errors: list[str] = []
        warnings: list[str] = []

        # Basic requirements for torrent creation
        if not metadata.get("title"):
            errors.append("Missing title - required for torrent creation")

        # MAM-specific recommendations
        if not metadata.get("description"):
            warnings.append("Missing description - recommended for MAM uploads")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "ready_for_upload": False,  # Always False - no API upload support
            "note": "Manual upload required - MAM has no upload API",
        }

    def prepare_upload_data(
        self, metadata: dict[str, Any], torrent_path: Path
    ) -> dict[str, Any]:
        """
        Upload data preparation - not applicable for MAM.

        MAM does not support API uploads. This method returns empty data
        with a note that manual upload is required.
        """
        console.print("[yellow]⚠️  MAM does not support API uploads[/yellow]")
        console.print(
            "[dim]Torrent created successfully - upload manually via MAM web interface[/dim]"
        )
        return {
            "note": "Manual upload required - MAM has no upload API",
            "torrent_ready": True,
            "upload_url": f"{self.base_url}/tor/upload.php",
        }

    def upload_torrent(
        self, torrent_path: Path, metadata: dict[str, Any], dry_run: bool = True
    ) -> dict[str, Any]:
        """
        Upload torrent - not supported by MAM.

        MAM does not provide an upload API. This method always returns
        a message directing users to manual upload.
        """
        console.print("[red]❌ MAM upload not possible via API[/red]")
        console.print(f"[cyan]📁 Torrent created: {torrent_path}[/cyan]")
        console.print(
            f"[cyan]🌐 Manual upload at: {self.base_url}/tor/upload.php[/cyan]"
        )
        console.print("[dim]Upload the .torrent file through MAM's web interface[/dim]")

        return {
            "success": False,
            "message": "MAM does not support API uploads - manual upload required",
            "torrent_path": str(torrent_path),
            "upload_url": f"{self.base_url}/tor/upload.php",
            "note": "Torrent file created successfully - use web interface to upload",
        }
