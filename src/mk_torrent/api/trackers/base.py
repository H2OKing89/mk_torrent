"""
Base tracker API interface that all trackers must implement
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from dataclasses import dataclass


@dataclass
class TrackerConfig:
    """Configuration for a tracker"""

    name: str
    announce_url: str
    api_endpoint: str
    source_tag: str
    requires_private: bool = True
    supported_formats: list[str] | None = None
    max_path_length: int = 255  # Default, RED uses 150

    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ["v1", "v2", "hybrid"]


class TrackerAPI(ABC):
    """Abstract base class for tracker APIs"""

    def __init__(
        self,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        self.api_key = api_key
        self.username = username
        self.password = password
        self.config = self.get_tracker_config()

    @abstractmethod
    def get_tracker_config(self) -> TrackerConfig:
        """Return tracker-specific configuration"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        pass

    @abstractmethod
    def search_existing(
        self,
        artist: str | None = None,
        album: str | None = None,
        title: str | None = None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """Search for existing torrents on tracker"""
        pass

    @abstractmethod
    def validate_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Validate metadata for this tracker's requirements"""
        pass

    @abstractmethod
    def prepare_upload_data(
        self, metadata: dict[str, Any], torrent_path: Path
    ) -> dict[str, Any]:
        """Prepare data for upload to tracker"""
        pass

    @abstractmethod
    def upload_torrent(
        self, torrent_path: Path, metadata: dict[str, Any], dry_run: bool = True
    ) -> dict[str, Any]:
        """Upload torrent to tracker"""
        pass

    def check_path_compliance(self, path: str) -> bool:
        """Check if path meets tracker requirements"""
        return len(path) <= self.config.max_path_length

    def get_compliance_report(self, paths: list[str]) -> dict[str, Any]:
        """Get detailed compliance report for multiple paths"""
        compliant_paths = []
        non_compliant_paths = []

        for path in paths:
            if self.check_path_compliance(path):
                compliant_paths.append({"path": path, "length": len(path)})
            else:
                non_compliant_paths.append(
                    {
                        "path": path,
                        "length": len(path),
                        "overage": len(path) - self.config.max_path_length,
                    }
                )

        results = {
            "compliant": compliant_paths,
            "non_compliant": non_compliant_paths,
            "max_length": self.config.max_path_length,
            "total_paths": len(paths),
            "compliance_rate": len(compliant_paths) / len(paths) if paths else 0.0,
        }

        return results
