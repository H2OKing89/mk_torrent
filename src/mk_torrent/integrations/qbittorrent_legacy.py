#!/usr/bin/env python3
"""
DEPRECATED: Legacy qBittorrent API integration (Phase 3B.3.3 Migration)

This module provides a simplified backward compatibility shim for the legacy
QBittorrentAPI class. It uses the modern BaseIntegrationClient infrastructure
internally but provides the original interface for existing code.

DEPRECATION NOTICE:
==================
This legacy interface is deprecated as of Phase 3B.3.3.
Use mk_torrent.integrations.QBittorrentClient (modern) instead.

The QBittorrentAPI class is maintained for backward compatibility but will be
removed in a future release. New code should use:
- IntegrationFactory.create('qbittorrent', config)
- QBittorrentClient directly

Migration Guide:
================

OLD (legacy):
    api = QBittorrentAPI(
        host='localhost',
        port=8080,
        username='admin',
        password='secret'
    )
    api.login()

NEW (modern):
    from mk_torrent.integrations import IntegrationFactory

    client = IntegrationFactory.create('qbittorrent', {
        'url': 'http://localhost:8080',
        'username': 'admin',
        'password': 'secret'
    })
"""

import logging
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from rich.console import Console

from .qbittorrent_modern import QBittorrentClient, QBittorrentConfig

console = Console()
logger = logging.getLogger(__name__)


class QBittorrentAPI:
    """
    DEPRECATED: Legacy qBittorrent API wrapper (Phase 3B.3.3 Migration)

    This class provides backward compatibility for the legacy interface while
    using the modern BaseIntegrationClient infrastructure internally.

    DEPRECATION WARNING: Use QBittorrentClient or IntegrationFactory instead.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        username: str = "admin",
        password: str = "adminadmin",
        use_https: bool = False,
    ):
        """
        Initialize legacy qBittorrent API wrapper.

        Args:
            host: qBittorrent server host
            port: qBittorrent server port
            username: Login username
            password: Login password
            use_https: Whether to use HTTPS
        """
        # Issue deprecation warning
        warnings.warn(
            "QBittorrentAPI is deprecated. Use QBittorrentClient or "
            "IntegrationFactory.create('qbittorrent') instead. "
            "Legacy interface will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Store legacy parameters
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_https = use_https

        # Create modern client with legacy parameters
        config = QBittorrentConfig(
            host=host,
            port=port,
            username=username,
            password=password,
            use_https=use_https,
            verify_ssl=False if use_https else True,  # Legacy behavior
            timeout=30,
            max_retries=3,
            user_agent="mk_torrent/1.0 (Legacy qBittorrent API)",
        )

        self._modern_client = QBittorrentClient(config=config)

        # Legacy state tracking
        self.logged_in = False
        self.api_version = None
        self.sid_cookie = None
        self.session = None  # Legacy compatibility

    @property
    def base_url(self) -> str:
        """Get base URL for API (legacy compatibility)"""
        protocol = "https" if self.use_https else "http"
        return f"{protocol}://{self.host}:{self.port}"

    def login(self) -> bool:
        """
        Login to qBittorrent Web API (legacy interface)

        Returns:
            True if login successful, False otherwise
        """
        try:
            response = self._modern_client.authenticate()

            if response.success:
                self.logged_in = True
                # Extract legacy state from modern response if available
                if hasattr(response, "data") and response.data:
                    self.api_version = response.data.get("api_version")
                    self.sid_cookie = response.data.get("sid_cookie")
                return True
            else:
                self.logged_in = False
                # Use legacy console output for compatibility
                console.print(f"[red]❌ Login failed: {response.message}[/red]")
                return False

        except Exception as e:
            self.logged_in = False
            console.print(f"[red]❌ Login error: {e}[/red]")
            return False

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to qBittorrent (legacy interface)

        Returns:
            Tuple of (success, message)
        """
        try:
            response = self._modern_client.health_check()

            if response.success:
                version_info = (
                    response.data.get("version", "Unknown")
                    if response.data
                    else "Unknown"
                )
                return True, f"Connected to qBittorrent {version_info}"
            else:
                return False, response.message or "Connection failed"

        except Exception as e:
            return False, f"Connection error: {e}"

    def get_torrents(self) -> List[Dict[str, Any]]:
        """
        Get list of torrents (legacy interface)

        Uses the underlying qbittorrent-api client directly since the modern
        wrapper focuses on configuration management rather than operations.
        """
        try:
            # Ensure we're authenticated first
            if not self.logged_in:
                if not self.login():
                    return []

            # Use the underlying qb_client for direct API access
            qb_client = self._modern_client.qb_client
            torrents = qb_client.torrents_info()
            return [dict(torrent) for torrent in torrents]

        except Exception as e:
            console.print(f"[red]❌ Error getting torrents: {e}[/red]")
            return []

    def upload_torrent(
        self,
        torrent_path: Union[str, Path],
        save_path: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> bool:
        """
        Upload torrent file (legacy interface)

        Args:
            torrent_path: Path to torrent file
            save_path: Download save path
            category: Torrent category
            tags: List of tags
            **kwargs: Additional parameters

        Returns:
            True if upload successful, False otherwise
        """
        try:
            # Ensure we're authenticated first
            if not self.logged_in:
                if not self.login():
                    return False

            # Use the underlying qb_client for direct torrent upload
            qb_client = self._modern_client.qb_client

            # Prepare upload kwargs in the format expected by qbittorrent-api
            upload_kwargs = {}
            if save_path:
                upload_kwargs["save_path"] = save_path
            if category:
                upload_kwargs["category"] = category
            if tags:
                # Convert list to comma-separated string as expected by qBittorrent
                upload_kwargs["tags"] = (
                    ",".join(tags) if isinstance(tags, list) else str(tags)
                )

            # Add any additional options (being careful about parameter names)
            for key, value in kwargs.items():
                upload_kwargs[key] = value

            # Upload using the underlying client
            with open(torrent_path, "rb") as torrent_file:
                qb_client.torrents_add(torrent_files=torrent_file, **upload_kwargs)

            console.print("[green]✅ Torrent uploaded successfully[/green]")
            return True

        except Exception as e:
            console.print(f"[red]❌ Upload error: {e}[/red]")
            return False

    def get_categories(self) -> Dict[str, Any]:
        """
        Get categories (legacy interface)

        Returns:
            Dictionary of categories
        """
        try:
            # Ensure we're authenticated first
            if not self.logged_in:
                if not self.login():
                    return {}

            response = self._modern_client.get_categories()

            if response.success and response.data:
                return response.data
            else:
                console.print(
                    f"[red]❌ Failed to get categories: {response.message}[/red]"
                )
                return {}

        except Exception as e:
            console.print(f"[red]❌ Error getting categories: {e}[/red]")
            return {}

    def add_category(self, name: str, save_path: str = "") -> bool:
        """
        Add category (legacy interface)

        Args:
            name: Category name
            save_path: Default save path for category

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure we're authenticated first
            if not self.logged_in:
                if not self.login():
                    return False

            response = self._modern_client.create_category(name, save_path)

            if response.success:
                console.print(f"[green]✅ Category '{name}' added[/green]")
                return True
            else:
                console.print(
                    f"[red]❌ Failed to add category: {response.message}[/red]"
                )
                return False

        except Exception as e:
            console.print(f"[red]❌ Category add error: {e}[/red]")
            return False

    # Simplified implementations for other common legacy methods
    def get_torrent_info(self, torrent_hash: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific torrent (legacy interface)"""
        try:
            if not self.logged_in:
                if not self.login():
                    return None

            qb_client = self._modern_client.qb_client
            torrents = qb_client.torrents_info(torrent_hashes=torrent_hash)

            if torrents:
                return dict(torrents[0])
            return None

        except Exception as e:
            console.print(f"[red]❌ Error getting torrent info: {e}[/red]")
            return None

    def delete_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        """Delete torrent (legacy interface)"""
        try:
            if not self.logged_in:
                if not self.login():
                    return False

            qb_client = self._modern_client.qb_client
            qb_client.torrents_delete(
                torrent_hashes=torrent_hash, delete_files=delete_files
            )

            console.print("[green]✅ Torrent deleted successfully[/green]")
            return True

        except Exception as e:
            console.print(f"[red]❌ Delete error: {e}[/red]")
            return False

    def pause_torrent(self, torrent_hash: str) -> bool:
        """Pause torrent (legacy interface)"""
        try:
            if not self.logged_in:
                if not self.login():
                    return False

            qb_client = self._modern_client.qb_client
            qb_client.torrents_pause(torrent_hashes=torrent_hash)

            console.print("[green]✅ Torrent paused[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ Pause error: {e}[/red]")
            return False

    def resume_torrent(self, torrent_hash: str) -> bool:
        """Resume torrent (legacy interface)"""
        try:
            if not self.logged_in:
                if not self.login():
                    return False

            qb_client = self._modern_client.qb_client
            qb_client.torrents_resume(torrent_hashes=torrent_hash)

            console.print("[green]✅ Torrent resumed[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ Resume error: {e}[/red]")
            return False

    # Legacy compatibility methods
    def _verify_login(self) -> bool:
        """Legacy compatibility method"""
        return self.logged_in

    def logout(self) -> bool:
        """Legacy logout method (modern client handles this automatically)"""
        self.logged_in = False
        return True


# Additional legacy functions for compatibility
def get_qbittorrent_password() -> str:
    """
    DEPRECATED: Legacy password function

    Use secure credential management or configuration files instead.
    """
    warnings.warn(
        "get_qbittorrent_password is deprecated. Use secure credential management.",
        DeprecationWarning,
        stacklevel=2,
    )
    return "adminadmin"  # Default fallback


# Legacy imports and compatibility
try:
    from ..core.secure_credentials import (
        get_secure_qbittorrent_password as get_qbittorrent_password,
    )

    SECURE_STORAGE_AVAILABLE = True
except ImportError:
    SECURE_STORAGE_AVAILABLE = False


# Maintain legacy module interface
__all__ = [
    "QBittorrentAPI",
    "get_qbittorrent_password",
    "SECURE_STORAGE_AVAILABLE",
]
