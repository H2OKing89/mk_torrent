#!/usr/bin/env python3
"""qBittorrent API integration using qbittorrent-api library"""

from typing import Any
import logging
import requests
import urllib3  # Add this import
import subprocess  # Add this import

from qbittorrentapi import Client

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import secure credential management
try:
    from ..core.secure_credentials import (
        get_secure_qbittorrent_password as get_qbittorrent_password,
    )

    SECURE_STORAGE_AVAILABLE = True
except ImportError:
    SECURE_STORAGE_AVAILABLE = False

console = Console()
logger = logging.getLogger(__name__)


class QBittorrentAPI:
    """Handle qBittorrent Web API connections"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        username: str = "admin",
        password: str = "adminadmin",
        use_https: bool = False,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_https = use_https
        self.session = requests.Session()
        self.logged_in = False
        self.api_version = None
        self.sid_cookie = None

        # Disable SSL warnings if needed (for self-signed certs)
        if use_https:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @property
    def base_url(self) -> str:
        """Get base URL for API"""
        protocol = "https" if self.use_https else "http"
        return f"{protocol}://{self.host}:{self.port}"

    def login(self) -> bool:
        """Login to qBittorrent Web API"""
        try:
            # First, try to get the login page to establish session
            login_url = f"{self.base_url}/api/v2/auth/login"

            # Prepare login data
            login_data = {"username": self.username, "password": self.password}

            # Make login request with proper headers
            headers = {
                "Referer": self.base_url,
                "Origin": self.base_url,
                "Content-Type": "application/x-www-form-urlencoded",
            }

            response = self.session.post(
                login_url,
                data=login_data,
                headers=headers,
                timeout=10,
                verify=False if self.use_https else True,
                allow_redirects=False,
            )

            # Check if login was successful
            if response.status_code == 200:
                response_text = response.text.strip()
                if response_text == "Ok.":
                    self.logged_in = True
                    # Store the SID cookie if present
                    if "SID" in self.session.cookies:
                        self.sid_cookie = self.session.cookies["SID"]
                    return True
                elif response_text == "Fails.":
                    console.print("[red]❌ Login failed: Invalid credentials[/red]")
                    return False
                else:
                    # Sometimes qBittorrent returns different responses
                    console.print(
                        f"[yellow]Unexpected login response: {response_text}[/yellow]"
                    )
                    # Try to verify if we're actually logged in
                    if self._verify_login():
                        self.logged_in = True
                        return True
                    return False  # Add explicit return
            elif response.status_code == 403:
                console.print(
                    "[red]❌ Login failed: Access forbidden (check IP whitelist in qBittorrent settings)[/red]"
                )
                return False
            else:
                console.print(
                    f"[red]❌ Login failed: HTTP {response.status_code}[/red]"
                )
                return False

        except requests.exceptions.ConnectionError:
            console.print(f"[red]❌ Cannot connect to {self.base_url}[/red]")
            console.print(
                "[yellow]Make sure qBittorrent Web UI is enabled and accessible[/yellow]"
            )
            return False
        except requests.exceptions.Timeout:
            console.print(f"[red]❌ Connection timeout to {self.base_url}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Login error: {e}[/red]")
            return False

    def _verify_login(self) -> bool:
        """Verify if we're logged in by trying to access a protected endpoint"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v2/app/version",
                timeout=5,
                verify=False if self.use_https else True,
            )
            return response.status_code == 200
        except Exception:
            return False

    def test_connection(self) -> tuple[bool, str]:
        """Test connection to qBittorrent"""
        try:
            # First try to get API version (sometimes doesn't require auth)
            response = self.session.get(
                f"{self.base_url}/api/v2/app/webapiVersion",
                timeout=5,
                verify=False if self.use_https else True,
            )

            if response.status_code == 200:
                self.api_version = response.text.strip()
                return True, f"Connected (API v{self.api_version})"
            elif response.status_code == 403:
                # Try to login first
                if self.login():
                    # Retry getting version
                    response = self.session.get(
                        f"{self.base_url}/api/v2/app/webapiVersion",
                        timeout=5,
                        verify=False if self.use_https else True,
                    )
                    if response.status_code == 200:
                        self.api_version = response.text.strip()
                        return True, f"Connected (API v{self.api_version})"
                return False, "Authentication required"
            else:
                return False, f"HTTP {response.status_code}"

        except requests.exceptions.ConnectionError:
            return False, "Connection refused - is qBittorrent running?"
        except requests.exceptions.Timeout:
            return False, "Connection timeout"
        except Exception as e:
            return False, str(e)

    def get_preferences(self) -> dict[str, Any] | None:
        """Get qBittorrent preferences"""
        if not self.logged_in:
            if not self.login():
                return None

        try:
            response = self.session.get(
                f"{self.base_url}/api/v2/app/preferences",
                timeout=5,
                verify=False if self.use_https else True,
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                console.print("[yellow]Session expired, re-authenticating...[/yellow]")
                if self.login():
                    response = self.session.get(
                        f"{self.base_url}/api/v2/app/preferences",
                        timeout=5,
                        verify=False if self.use_https else True,
                    )
                    if response.status_code == 200:
                        return response.json()
            return None
        except Exception as e:
            console.print(f"[red]Error getting preferences: {e}[/red]")
            return None

    def get_default_save_path(self) -> str | None:
        """Get default save path from qBittorrent"""
        prefs = self.get_preferences()
        if prefs:
            return prefs.get("save_path", None)
        return None

    def create_torrent(
        self,
        source_path: str,
        trackers: list | None = None,
        comment: str = "",
        is_private: bool = False,
        piece_size: int = 0,
    ) -> tuple[bool, bytes]:
        """Create torrent via API (if supported)"""
        if not self.logged_in:
            if not self.login():
                return False, b""

        # Note: qBittorrent Web API doesn't directly support torrent creation
        # This would need to be done via CLI or other means
        console.print(
            "[yellow]⚠️ Torrent creation via Web API not directly supported[/yellow]"
        )
        console.print("[yellow]Using alternative method...[/yellow]")
        return False, b""

    def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check"""
        results: dict[str, Any] = {  # Fix: explicitly type the dict
            "connection": False,
            "api_version": None,
            "authenticated": False,
            "preferences_accessible": False,
            "default_save_path": None,
            "errors": [],
            "warnings": [],
        }

        # Test basic connection
        console.print("[cyan]Testing connection...[/cyan]")
        connected, msg = self.test_connection()
        results["connection"] = connected
        results["api_version"] = self.api_version

        if not connected:
            # Fix: Ensure we're appending to lists, not treating them as bool/None
            errors_list = results["errors"]
            if isinstance(errors_list, list):
                errors_list.append(f"Connection failed: {msg}")

            # Provide helpful suggestions
            warnings_list = results["warnings"]
            if isinstance(warnings_list, list):
                if "refused" in msg.lower():
                    warnings_list.append(
                        "Make sure qBittorrent is running and Web UI is enabled"
                    )
                    warnings_list.append(f"Check if port {self.port} is correct")
                elif "403" in str(msg):
                    warnings_list.append("Check qBittorrent Web UI settings:")
                    warnings_list.append(
                        "  - Ensure IP address is whitelisted or authentication bypass is configured"
                    )
                    warnings_list.append(
                        "  - Try disabling 'Bypass authentication for clients on localhost' if accessing remotely"
                    )

            return results

        # Test authentication
        console.print("[cyan]Testing authentication...[/cyan]")
        if self.login():
            results["authenticated"] = True

            # Test preferences access
            console.print("[cyan]Testing API access...[/cyan]")
            prefs = self.get_preferences()
            if prefs:
                results["preferences_accessible"] = True
                results["default_save_path"] = prefs.get("save_path")

                # Check some important settings
                warnings_list = results["warnings"]
                if isinstance(warnings_list, list):
                    if prefs.get("web_ui_domain_list") and self.host not in prefs.get(
                        "web_ui_domain_list", ""
                    ):
                        warnings_list.append(
                            f"Host {self.host} may not be in qBittorrent's domain whitelist"
                        )
        else:
            errors_list = results["errors"]
            warnings_list = results["warnings"]
            if isinstance(errors_list, list):
                errors_list.append(
                    "Authentication failed - check username and password"
                )
            if isinstance(warnings_list, list):
                warnings_list.append("Also check IP whitelist settings in qBittorrent")

        return results

    def get_categories(self) -> dict[str, Any]:
        """Get all categories from qBittorrent"""
        if not self.logged_in:
            if not self.login():
                return {}

        try:
            response = self.session.get(
                f"{self.base_url}/api/v2/torrents/categories",
                timeout=5,
                verify=False if self.use_https else True,
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            console.print(f"[red]Error getting categories: {e}[/red]")
        return {}

    def create_category(self, name: str, save_path: str = "") -> bool:
        """Create a new category in qBittorrent"""
        if not self.logged_in:
            if not self.login():
                return False

        try:
            response = self.session.post(
                f"{self.base_url}/api/v2/torrents/createCategory",
                data={"category": name, "savePath": save_path},
                timeout=5,
                verify=False if self.use_https else True,
            )
            return response.status_code == 200
        except Exception as e:
            console.print(f"[red]Error creating category: {e}[/red]")
            return False

    def get_tags(self) -> list[str]:
        """Get all tags from qBittorrent"""
        if not self.logged_in:
            if not self.login():
                return []

        try:
            response = self.session.get(
                f"{self.base_url}/api/v2/torrents/tags",
                timeout=5,
                verify=False if self.use_https else True,
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            console.print(f"[red]Error getting tags: {e}[/red]")
        return []

    def create_tags(self, tags: list[str]) -> bool:
        """Create new tags in qBittorrent"""
        if not self.logged_in:
            if not self.login():
                return False

        try:
            # Fix: Handle empty list properly
            if not tags:
                return True  # Nothing to create

            response = self.session.post(
                f"{self.base_url}/api/v2/torrents/createTags",
                data={"tags": ",".join(tags)},
                timeout=5,
                verify=False if self.use_https else True,
            )
            return response.status_code == 200
        except Exception as e:
            console.print(f"[red]Error creating tags: {e}[/red]")
            return False

    def sync_categories_and_tags(self, config: dict[str, Any]) -> None:
        """Sync categories and tags from config to qBittorrent"""
        console.print("[cyan]Syncing categories and tags with qBittorrent...[/cyan]")

        # Sync categories
        existing_categories = self.get_categories()
        for category in config.get("categories", []):
            if category not in existing_categories:
                if self.create_category(category):
                    console.print(f"  [green]✓ Created category: {category}[/green]")

        # Sync tags
        existing_tags = self.get_tags()
        new_tags = [
            tag for tag in config.get("common_tags", []) if tag not in existing_tags
        ]
        if new_tags:
            if self.create_tags(new_tags):
                console.print(f"  [green]✓ Created tags: {', '.join(new_tags)}[/green]")


def run_health_check(config: dict[str, Any]) -> bool:
    """Run health check with config"""
    console.print(
        Panel.fit(
            "[bold cyan]🏥 qBittorrent Health Check[/bold cyan]", border_style="cyan"
        )
    )

    # Get connection settings from config
    host = config.get("qbit_host", "localhost")
    port = config.get("qbit_port", 8080)
    username = config.get("qbit_username", "admin")

    # Get password securely
    if SECURE_STORAGE_AVAILABLE:
        password = get_qbittorrent_password(host, port, username)
        if not password:
            console.print("[red]❌ No password found in secure storage[/red]")
            console.print("[dim]Run setup again to store password securely[/dim]")
            return False
    else:
        password = config.get("qbit_password", "adminadmin")

    use_https = config.get("qbit_https", False)

    # Create API instance
    api = QBittorrentAPI(host, port, username, password, use_https)

    # Run health check
    results = api.health_check()

    # Display results
    table = Table(title="Health Check Results", show_lines=True)
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")

    # Connection
    table.add_row(
        "Connection",
        "✅" if results["connection"] else "❌",
        f"{api.base_url}"
        + (f" (API v{results['api_version']})" if results["api_version"] else ""),
    )

    # Authentication
    table.add_row(
        "Authentication",
        "✅" if results["authenticated"] else "❌",
        f"User: {username}",
    )

    # Preferences
    table.add_row(
        "Preferences Access",
        "✅" if results["preferences_accessible"] else "❌",
        "Can read settings" if results["preferences_accessible"] else "No access",
    )

    # Save Path
    if results["default_save_path"]:
        table.add_row("Default Save Path", "✅", results["default_save_path"])

    console.print(table)

    # Show warnings if any
    if results["warnings"]:
        console.print("\n[yellow]⚠️ Warnings:[/yellow]")
        for warning in results["warnings"]:
            console.print(f"  • {warning}")

    # Show errors if any
    if results["errors"]:
        console.print("\n[red]Errors:[/red]")
        for error in results["errors"]:
            console.print(f"  • {error}")

        # Provide troubleshooting steps
        console.print("\n[cyan]Troubleshooting Steps:[/cyan]")
        console.print("1. Check qBittorrent Web UI settings (Tools → Options → Web UI)")
        console.print("2. Ensure 'Enable Web User Interface' is checked")
        console.print(f"3. Verify IP address {host} is accessible")
        console.print(
            "4. Check 'Bypass authentication for clients on localhost' if accessing locally"
        )
        console.print(
            "5. Or add your IP to 'Bypass authentication for clients in whitelisted IP subnets'"
        )
        console.print("6. Verify username and password are correct")

        return False

    if all([results["connection"], results["authenticated"]]):
        console.print(
            "\n[green]✅ All checks passed! qBittorrent is accessible.[/green]"
        )

        # Sync categories and tags
        api.sync_categories_and_tags(config)

        return True
    else:
        console.print(
            "\n[yellow]⚠️ Some checks failed. Please review settings.[/yellow]"
        )
        return False


def check_docker_connectivity(container_name: str) -> bool:
    """Test if Docker container is running and accessible"""

    try:
        # Check if container is running
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={container_name}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if container_name in result.stdout:
            console.print(
                f"[green]✅ Docker container '{container_name}' is running[/green]"
            )

            # Try to exec into container
            test_cmd = ["docker", "exec", container_name, "echo", "test"]
            test_result = subprocess.run(
                test_cmd, capture_output=True, text=True, timeout=5
            )

            if test_result.returncode == 0:
                console.print("[green]✅ Can execute commands in container[/green]")
                return True
            else:
                console.print("[red]❌ Cannot execute commands in container[/red]")
                return False
        else:
            console.print(f"[red]❌ Container '{container_name}' is not running[/red]")
            console.print("[yellow]Available containers:[/yellow]")

            # Show available containers
            list_result = subprocess.run(
                ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True,
            )
            console.print(list_result.stdout)
            return False

    except subprocess.TimeoutExpired:
        console.print("[red]❌ Docker command timeout[/red]")
        return False
    except FileNotFoundError:
        console.print("[red]❌ Docker not found. Is Docker installed?[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Docker error: {e}[/red]")
        return False


def validate_qbittorrent_config(config: dict[str, Any]) -> bool:
    """Validate qBittorrent connection configuration"""
    if not config.get("qbit_host"):
        return False

    # Get password securely
    if SECURE_STORAGE_AVAILABLE:
        password = get_qbittorrent_password(
            config["qbit_host"],
            config.get("qbit_port", 8080),
            config.get("qbit_username", "admin"),
        )
        if not password:
            console.print("[red]❌ No password found in secure storage[/red]")
            return False
    else:
        password = config.get("qbit_password")

    try:
        client = Client(
            host=f"{config['qbit_host']}:{config.get('qbit_port', 8080)}",
            username=config.get("qbit_username"),
            password=password,
            VERIFY_WEBUI_CERTIFICATE=False,
        )

        # Try to get version to verify connection
        version = client.app_version()
        console.print(f"[green]✓ Connected to qBittorrent {version}[/green]")
        return True

    except Exception as e:
        console.print(f"[red]✗ Connection failed: {e}[/red]")
        return False


def sync_qbittorrent_metadata(config: dict[str, Any]) -> None:
    """Sync categories and tags with qBittorrent"""
    try:
        client = Client(
            host=f"{config['qbit_host']}:{config.get('qbit_port', 8080)}",
            username=config.get("qbit_username"),
            password=config.get("qbit_password"),
            VERIFY_WEBUI_CERTIFICATE=False,
        )

        # Sync categories
        default_category = config.get("default_category")
        if default_category:
            existing_categories = client.torrents_categories()
            if default_category not in existing_categories:
                client.torrents_create_category(default_category)
                console.print(f"[green]✓ Created category: {default_category}[/green]")

        # Sync tags
        default_tags = config.get("default_tags", [])
        if default_tags:
            existing_tags = client.torrents_tags()
            new_tags = [tag for tag in default_tags if tag not in existing_tags]
            if new_tags:
                client.torrents_create_tags(new_tags)
                console.print(f"[green]✓ Created tags: {', '.join(new_tags)}[/green]")

    except Exception as e:
        console.print(f"[yellow]Warning: Could not sync metadata: {e}[/yellow]")
