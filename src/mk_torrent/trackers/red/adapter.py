"""
DEPRECATED: Redacted (RED) tracker API implementation

This module is deprecated as of 2025-01-09 and will be removed on 2025-02-09.
Use mk_torrent.trackers.red_adapter.REDAdapter instead.

This file now imports and re-exports the consolidated implementation.
"""

import warnings
from pathlib import Path
from typing import Any

from mk_torrent.trackers.red_adapter import REDAdapter, REDConfig
from mk_torrent.trackers.base import TrackerAPI, TrackerConfig

warnings.warn(
    "mk_torrent.trackers.red.adapter is deprecated. "
    "Use mk_torrent.trackers.red_adapter.REDAdapter instead. "
    "This module will be removed on 2025-02-09.",
    DeprecationWarning,
    stacklevel=2,
)


class RedactedAPI(TrackerAPI):
    """DEPRECATED: Use REDAdapter from mk_torrent.trackers.red_adapter instead."""

    def __init__(self, api_key: str, base_url: str = "https://redacted.ch"):
        warnings.warn(
            "RedactedAPI is deprecated. Use REDAdapter instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Create REDConfig and adapter
        config = REDConfig(api_key=api_key, base_url=base_url)
        self._adapter = REDAdapter(config)

        # Initialize parent with the same parameters
        super().__init__(api_key=api_key)

    def get_tracker_config(self) -> TrackerConfig:
        """Return RED-specific configuration."""
        return self._adapter.get_tracker_config()

    def test_connection(self) -> bool:
        """Test API connection and authentication."""
        return self._adapter.test_connection()

    def search_existing(
        self,
        artist: str | None = None,
        album: str | None = None,
        title: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Search for existing torrents on RED."""
        return self._adapter.search_existing(artist, album, title, **kwargs)

    def validate_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Validate metadata for RED requirements."""
        return self._adapter.validate_metadata(metadata)

    def prepare_upload_data(
        self, metadata: dict[str, Any], torrent_path: Path
    ) -> dict[str, Any]:
        """Prepare upload data for RED."""
        return self._adapter.prepare_upload_data(metadata, torrent_path)

    def upload_torrent(
        self, torrent_path: Path, metadata: dict[str, Any], dry_run: bool = True
    ) -> dict[str, Any]:
        """Upload torrent to RED."""
        return self._adapter.upload_torrent(torrent_path, metadata, dry_run)


# Re-export for backward compatibility
__all__ = ["RedactedAPI", "REDAdapter", "REDConfig"]
