"""
qBittorrent API integration using the new base infrastructure

This module provides a standardized qBittorrent client with:
- Unified error handling and retry logic
- Standardized configuration management
- Health checks and connection validation
- Category and tag synchronization

Part of Phase 3B.2: Upload Workflow Unification
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from datetime import timedelta

from qbittorrentapi import Client as QBittorrentAPIClient
from qbittorrentapi.exceptions import APIConnectionError, LoginFailed
from rich.console import Console

from .base import (
    BaseIntegrationClient,
    IntegrationConfig,
    IntegrationResponse,
    IntegrationStatus,
)
from .auth import (
    AuthenticationConfig,
    AuthenticationType,
    CredentialStorage,
    AuthenticationFactory,
)

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class QBittorrentConfig(IntegrationConfig):
    """Configuration specific to qBittorrent"""

    base_url: str = ""  # Will be set in __post_init__
    host: str = "localhost"
    port: int = 8080
    username: str = "admin"
    password: str = ""
    use_https: bool = False

    # qBittorrent-specific settings
    sync_categories: bool = True
    sync_tags: bool = True
    default_category: str | None = None
    default_tags: list[str] | None = None

    def __post_init__(self):
        # Build base_url from host/port
        protocol = "https" if self.use_https else "http"
        self.base_url = f"{protocol}://{self.host}:{self.port}"

        # Initialize default tags if None
        if self.default_tags is None:
            self.default_tags = []

        super().__post_init__()


class QBittorrentClient(BaseIntegrationClient):
    """Modern qBittorrent client using base integration infrastructure"""

    def __init__(self, config: QBittorrentConfig):
        self.qb_config = config  # Set this BEFORE calling super().__init__
        super().__init__(config)
        self._qb_client: QBittorrentAPIClient | None = None
        self._authenticated = False

        # Initialize standardized authentication
        auth_config = AuthenticationConfig(
            auth_type=AuthenticationType.USERNAME_PASSWORD,
            storage_method=CredentialStorage.MEMORY_ONLY,  # For now, use memory
            service_name="qBittorrent",
            username=config.username,
            password=config.password,
            session_timeout=timedelta(
                hours=24
            ),  # qBittorrent sessions typically last long
            auto_refresh=True,
        )

        self._auth_handler = AuthenticationFactory.create_handler(
            auth_config,
            login_endpoint=f"{config.base_url}/api/v2/auth/login",
            client_session=None,  # Will be set when qb_client is created
        )

    def _configure_session(self, **kwargs: Any) -> None:
        """Configure requests session for qBittorrent specifics"""
        # Disable SSL warnings for self-signed certs
        if self.qb_config.use_https and not self.config.verify_ssl:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @property
    def qb_client(self) -> QBittorrentAPIClient:
        """Get or create qBittorrent API client"""
        if self._qb_client is None:
            self._qb_client = QBittorrentAPIClient(
                host=self.qb_config.host,
                port=self.qb_config.port,
                username=self.qb_config.username,
                password=self.qb_config.password,
                VERIFY_WEBUI_CERTIFICATE=self.config.verify_ssl,
                REQUESTS_ARGS={
                    "timeout": self.config.timeout,
                },
            )
        return self._qb_client

    def authenticate(self) -> IntegrationResponse:
        """Authenticate with qBittorrent using standardized authentication"""
        try:
            # Use the standardized authentication handler
            response = self._auth_handler.authenticate()

            if response.success:
                # Also authenticate the underlying qb_client
                self.qb_client.auth_log_in()
                self._authenticated = True

                return IntegrationResponse(
                    status=IntegrationStatus.SUCCESS,
                    message="Authentication successful",
                    data={
                        "authenticated": True,
                        "expires_at": response.data.get("expires_at")
                        if response.data
                        else None,
                    },
                )
            else:
                self._authenticated = False
                return response

        except LoginFailed as e:
            self._authenticated = False
            return IntegrationResponse(
                status=IntegrationStatus.AUTHENTICATION_REQUIRED,
                message="Invalid credentials",
                error_details={"exception": str(e)},
            )
        except APIConnectionError as e:
            return IntegrationResponse(
                status=IntegrationStatus.FAILED,
                message=f"Connection failed: {e}",
                error_details={"exception": str(e)},
            )
        except Exception as e:
            return IntegrationResponse(
                status=IntegrationStatus.FAILED,
                message=f"Authentication error: {e}",
                error_details={"exception": str(e)},
            )

    def is_authenticated(self) -> bool:
        """Check authentication status using standardized handler"""
        return self._auth_handler.is_authenticated() and self._authenticated

    def health_check(self) -> IntegrationResponse:
        """Perform comprehensive health check"""
        try:
            # Test basic connectivity
            version_response = self._make_request("GET", "api/v2/app/webapiVersion")

            if not version_response.success:
                return IntegrationResponse(
                    status=IntegrationStatus.FAILED,
                    message="Failed to connect to qBittorrent Web UI",
                    error_details=version_response.error_details,
                )

            api_version = (
                version_response.data.get("raw", "unknown")
                if version_response.data
                else "unknown"
            )

            # Test authentication
            if not self.is_authenticated():
                auth_response = self.authenticate()
                if not auth_response.success:
                    return auth_response

            # Get application info
            try:
                app_version = self.qb_client.app.version
                preferences = self.qb_client.app.preferences

                return IntegrationResponse(
                    status=IntegrationStatus.SUCCESS,
                    message="qBittorrent is healthy",
                    data={
                        "api_version": api_version,
                        "app_version": app_version,
                        "preferences": {
                            "save_path": preferences.get("save_path"),
                            "dht_enabled": preferences.get("dht"),
                            "upnp_enabled": preferences.get("upnp"),
                        },
                    },
                )

            except Exception as e:
                return IntegrationResponse(
                    status=IntegrationStatus.FAILED,
                    message=f"Failed to get application info: {e}",
                    error_details={"exception": str(e)},
                )

        except Exception as e:
            logger.exception("Health check failed")
            return IntegrationResponse(
                status=IntegrationStatus.FAILED,
                message=f"Health check failed: {e}",
                error_details={"exception": str(e)},
            )

    def get_categories(self) -> IntegrationResponse:
        """Get all categories from qBittorrent"""
        try:
            if not self.is_authenticated():
                auth_response = self.authenticate()
                if not auth_response.success:
                    return auth_response

            categories = self.qb_client.torrents_categories()

            return IntegrationResponse(
                status=IntegrationStatus.SUCCESS,
                message="Categories retrieved",
                data={"categories": dict(categories)},
            )

        except Exception as e:
            return IntegrationResponse(
                status=IntegrationStatus.FAILED,
                message=f"Failed to get categories: {e}",
                error_details={"exception": str(e)},
            )

    def create_category(self, name: str, save_path: str = "") -> IntegrationResponse:
        """Create a new category"""
        try:
            if not self.is_authenticated():
                auth_response = self.authenticate()
                if not auth_response.success:
                    return auth_response

            self.qb_client.torrents_create_category(name=name, save_path=save_path)

            return IntegrationResponse(
                status=IntegrationStatus.SUCCESS,
                message=f"Category '{name}' created",
                data={"category": name, "save_path": save_path},
            )

        except Exception as e:
            return IntegrationResponse(
                status=IntegrationStatus.FAILED,
                message=f"Failed to create category '{name}': {e}",
                error_details={"exception": str(e)},
            )

    def get_tags(self) -> IntegrationResponse:
        """Get all tags from qBittorrent"""
        try:
            if not self.is_authenticated():
                auth_response = self.authenticate()
                if not auth_response.success:
                    return auth_response

            tags = self.qb_client.torrents_tags()

            return IntegrationResponse(
                status=IntegrationStatus.SUCCESS,
                message="Tags retrieved",
                data={"tags": list(tags)},
            )

        except Exception as e:
            return IntegrationResponse(
                status=IntegrationStatus.FAILED,
                message=f"Failed to get tags: {e}",
                error_details={"exception": str(e)},
            )

    def create_tags(self, tags: list[str]) -> IntegrationResponse:
        """Create new tags"""
        try:
            if not self.is_authenticated():
                auth_response = self.authenticate()
                if not auth_response.success:
                    return auth_response

            self.qb_client.torrents_create_tags(tags=tags)

            return IntegrationResponse(
                status=IntegrationStatus.SUCCESS,
                message=f"Created {len(tags)} tags",
                data={"tags": tags},
            )

        except Exception as e:
            return IntegrationResponse(
                status=IntegrationStatus.FAILED,
                message=f"Failed to create tags: {e}",
                error_details={"exception": str(e)},
            )

    def sync_categories_and_tags(self) -> IntegrationResponse:
        """Sync categories and tags from configuration"""
        results: list[str] = []

        try:
            # Sync categories
            if self.qb_config.sync_categories and self.qb_config.default_category:
                categories_response = self.get_categories()
                if categories_response.success:
                    existing_categories = (
                        categories_response.data.get("categories", {})
                        if categories_response.data
                        else {}
                    )

                    if self.qb_config.default_category not in existing_categories:
                        create_response = self.create_category(
                            self.qb_config.default_category
                        )
                        if create_response.success:
                            results.append(
                                f"✓ Created category: {self.qb_config.default_category}"
                            )
                        else:
                            results.append(
                                f"✗ Failed to create category: {create_response.message}"
                            )
                    else:
                        results.append(
                            f"✓ Category already exists: {self.qb_config.default_category}"
                        )

            # Sync tags
            if self.qb_config.sync_tags and self.qb_config.default_tags:
                tags_response = self.get_tags()
                if tags_response.success:
                    existing_tags = (
                        tags_response.data.get("tags", []) if tags_response.data else []
                    )

                    new_tags = [
                        tag
                        for tag in self.qb_config.default_tags
                        if tag not in existing_tags
                    ]
                    if new_tags:
                        create_response = self.create_tags(new_tags)
                        if create_response.success:
                            results.append(f"✓ Created tags: {', '.join(new_tags)}")
                        else:
                            results.append(
                                f"✗ Failed to create tags: {create_response.message}"
                            )
                    else:
                        results.append("✓ All tags already exist")

            return IntegrationResponse(
                status=IntegrationStatus.SUCCESS,
                message="Sync completed",
                data={"results": results},
            )

        except Exception as e:
            return IntegrationResponse(
                status=IntegrationStatus.FAILED,
                message=f"Sync failed: {e}",
                error_details={"exception": str(e), "partial_results": results},
            )

    def add_torrent(
        self,
        torrent_path: Path,
        category: str | None = None,
        tags: list[str] | None = None,
        save_path: str | None = None,
    ) -> IntegrationResponse:
        """Add torrent to qBittorrent"""
        try:
            if not self.is_authenticated():
                auth_response = self.authenticate()
                if not auth_response.success:
                    return auth_response

            # Read torrent file
            if not torrent_path.exists():
                return IntegrationResponse(
                    status=IntegrationStatus.VALIDATION_FAILED,
                    message=f"Torrent file not found: {torrent_path}",
                )

            with open(torrent_path, "rb") as f:
                torrent_data = f.read()

            # Prepare options
            options = {}
            if category:
                options["category"] = category
            if tags:
                options["tags"] = ",".join(tags)
            if save_path:
                options["savepath"] = save_path

            # Add torrent
            self.qb_client.torrents_add(torrent_files=torrent_data, **options)

            return IntegrationResponse(
                status=IntegrationStatus.SUCCESS,
                message=f"Torrent added: {torrent_path.name}",
                data={
                    "torrent_file": str(torrent_path),
                    "category": category,
                    "tags": tags,
                    "save_path": save_path,
                },
            )

        except Exception as e:
            return IntegrationResponse(
                status=IntegrationStatus.FAILED,
                message=f"Failed to add torrent: {e}",
                error_details={"exception": str(e)},
            )


# Convenience function for backward compatibility
def sync_qbittorrent_metadata(config: dict[str, Any]) -> None:
    """Legacy function for syncing qBittorrent metadata (deprecated)"""
    import warnings

    warnings.warn(
        "sync_qbittorrent_metadata is deprecated. Use QBittorrentClient.sync_categories_and_tags() instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    try:
        qb_config = QBittorrentConfig(
            host=config.get("qbit_host", "localhost"),
            port=config.get("qbit_port", 8080),
            username=config.get("qbit_username", "admin"),
            password=config.get("qbit_password", ""),
            use_https=config.get("qbit_use_https", False),
            default_category=config.get("default_category"),
            default_tags=config.get("default_tags", []),
        )

        with QBittorrentClient(qb_config) as client:
            result = client.sync_categories_and_tags()

            if result.success:
                for line in result.data.get("results", []) if result.data else []:
                    console.print(f"[green]{line}[/green]")
            else:
                console.print(f"[red]Sync failed: {result.message}[/red]")

    except Exception as e:
        console.print(f"[red]Error syncing qBittorrent metadata: {e}[/red]")


__all__ = [
    "QBittorrentConfig",
    "QBittorrentClient",
    "sync_qbittorrent_metadata",  # Deprecated
]
