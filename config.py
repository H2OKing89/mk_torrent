#!/usr/bin/env python3
"""Configuration management for torrent creator"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import os
import getpass

from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

# Import secure credential management
try:
    from secure_credentials import (
        secure_manager,
        get_secure_qbittorrent_password,
        get_secure_tracker_url
    )
    SECURE_STORAGE_AVAILABLE = True
except ImportError:
    console = Console()
    console.print("[yellow]⚠️ Secure credential storage not available[/yellow]")
    console.print("[dim]Install with: pip install cryptography keyring bcrypt[/dim]")
    SECURE_STORAGE_AVAILABLE = False

console = Console()

CONFIG_DIR = Path.home() / ".config" / "torrent_creator"
CONFIG_FILE = CONFIG_DIR / "config.json"
TRACKERS_FILE = CONFIG_DIR / "trackers.txt"

def load_config() -> Dict[str, Any]:
    """Load configuration from file"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return get_default_config()

def save_config(config: Dict[str, Any]):
    """Save configuration to file"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    # Ensure config file has proper permissions
    CONFIG_FILE.chmod(0o600)

def load_trackers() -> List[str]:
    """Load trackers from file with secure passkeys"""
    if not TRACKERS_FILE.exists():
        return []

    trackers = []
    try:
        with open(TRACKERS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if SECURE_STORAGE_AVAILABLE:
                        # Replace secure passkey placeholders with actual passkeys
                        line = get_secure_tracker_url(line)
                    trackers.append(line)
    except Exception as e:
        console.print(f"[red]Error loading trackers: {e}[/red]")

    return trackers

def save_trackers(trackers: List[str]):
    """Save trackers to file"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(TRACKERS_FILE, 'w') as f:
        for tracker in trackers:
            f.write(f"{tracker}\n")
    TRACKERS_FILE.chmod(0o600)

def get_qbittorrent_password(config: Dict[str, Any]) -> Optional[str]:
    """Get qBittorrent password from secure storage"""
    if not SECURE_STORAGE_AVAILABLE:
        # Fallback to plain text if secure storage not available
        return config.get("qbit_password")

    host = config.get("qbit_host", "localhost")
    port = config.get("qbit_port", 8080)
    username = config.get("qbit_username", "admin")

    return get_secure_qbittorrent_password(host, port, username)

def store_qbittorrent_password(config: Dict[str, Any], password: str):
    """Store qBittorrent password securely"""
    if not SECURE_STORAGE_AVAILABLE:
        # Fallback to plain text storage
        config["qbit_password"] = password
        console.print("[yellow]⚠️ Storing password in plain text (secure storage not available)[/yellow]")
        return

    host = config.get("qbit_host", "localhost")
    port = config.get("qbit_port", 8080)
    username = config.get("qbit_username", "admin")

    secure_manager.store_qbittorrent_credentials(host, port, username, password)

def get_default_config() -> Dict[str, Any]:
    """Get default configuration"""
    return {
        "qbit_host": "localhost",
        "qbit_port": 8080,
        "qbit_username": "admin",
        # Password stored securely, not in config
        "qbit_https": False,
        "docker_mode": False,
        "docker_container": "qbittorrent",
        "docker_mappings": {
            "/mnt/cache": "/data",
            "/mnt/user": "/media"
        },
        "default_piece_size": "Auto",
        "default_private": True,
        "output_directory": str(Path.home() / "torrents"),
        "auto_start_seeding": True,
        "auto_torrent_management": True,
        "default_torrent_format": "v1",  # Default to v1 for compatibility
        "default_source": "",  # Source field for cross-seeding
        "common_sources": ["RED", "OPS", "GGn", "PTP", "BTN", "MAM", "FL", "AR", "ANT"],  # Common tracker sources
        "optimize_alignment": True,  # File alignment optimization
        "padded_file_size_limit": -1,  # -1 = auto, 0 = no padding, >0 = size limit
        "backup_directory": str(Path.home() / "torrent_backups"),  # Backup location for cross-seeding
        "comment_templates": [  # Pre-defined comment templates
            "Created with qBittorrent Torrent Creator",
            "Official Release",
            "Scene Release",
            "Internal Release"
        ],
        "default_category": "",
        "default_tags": [],
        "categories": [],
        "common_tags": []
    }

def setup_wizard():
    """Interactive setup wizard with health checks"""
    console.print(Panel.fit("[bold cyan]🔧 Torrent Creator Setup Wizard[/bold cyan]", border_style="cyan"))
    
    config = get_default_config()
    
    # qBittorrent Connection Setup
    console.print("\n[bold cyan]📡 qBittorrent Connection Settings[/bold cyan]")
    
    # Ask for connection type
    use_docker = Confirm.ask("Is qBittorrent running in Docker?", default=False)
    config["docker_mode"] = use_docker
    
    if use_docker:
        # Docker setup
        config["docker_container"] = Prompt.ask(
            "Docker container name",
            default=config.get("docker_container", "qbittorrent")
        )
        
        # Test Docker connectivity
        from qbit_api import test_docker_connectivity
        if not test_docker_connectivity(config["docker_container"]):
            if not Confirm.ask("[yellow]Continue anyway?[/yellow]", default=False):
                console.print("[red]Setup cancelled[/red]")
                return
        
        # Path mappings
        console.print("\n[cyan]Configure Docker path mappings[/cyan]")
        console.print("[dim]Map host paths to container paths[/dim]")
        
        mappings = {}
        # Suggest common mappings
        suggested_mappings = [
            ("/mnt/cache", "/data"),
            ("/mnt/user", "/media"),
            ("/mnt/cache/downloads", "/downloads")
        ]
        
        for host_path, container_path in suggested_mappings:
            if Confirm.ask(f"Add mapping {host_path} → {container_path}?", default=True):
                mappings[host_path] = container_path
        
        # Custom mappings
        while Confirm.ask("Add custom path mapping?", default=False):
            host = Prompt.ask("Host path")
            container = Prompt.ask(f"Container path for {host}")
            mappings[host] = container
        
        config["docker_mappings"] = mappings
    
    # qBittorrent Web UI settings
    console.print("\n[cyan]qBittorrent Web UI Settings[/cyan]")
    
    config["qbit_host"] = Prompt.ask(
        "qBittorrent host/IP",
        default=config.get("qbit_host", "localhost")
    )
    
    config["qbit_port"] = IntPrompt.ask(
        "qBittorrent port",
        default=config.get("qbit_port", 8080)
    )
    
    config["qbit_https"] = Confirm.ask(
        "Use HTTPS?",
        default=config.get("qbit_https", False)
    )
    
    config["qbit_username"] = Prompt.ask(
        "Username",
        default=config.get("qbit_username", "admin")
    )

    # Password (secure storage)
    if SECURE_STORAGE_AVAILABLE:
        console.print("\n[cyan]qBittorrent Password[/cyan]")
        console.print("[dim]Password will be stored securely using system keyring[/dim]")
        password = getpass.getpass("Password (hidden): ")
        if password:
            store_qbittorrent_password(config, password)
            console.print("[green]✅ Password stored securely[/green]")
    else:
        console.print("\n[yellow]⚠️ Secure storage not available[/yellow]")
        password = getpass.getpass("Password (will be stored in plain text): ")
        if password:
            config["qbit_password"] = password
            console.print("[yellow]⚠️ Password stored in plain text[/yellow]")

    # Test connection
    console.print("\n[cyan]Testing qBittorrent connection...[/cyan]")
    from qbit_api import run_health_check

    if run_health_check(config):
        console.print("[green]✅ Connection successful![/green]")
    else:
        console.print("[yellow]⚠️ Connection failed. Please check your settings.[/yellow]")
        if not Confirm.ask("Save configuration anyway?", default=True):
            console.print("[red]Setup cancelled[/red]")
            return
    
    # Default output directory
    console.print("\n[cyan]Default Settings[/cyan]")
    config["output_directory"] = Prompt.ask(
        "Default output directory for .torrent files",
        default=config.get("output_directory", str(Path.home() / "torrents"))
    )
    
    Path(config["output_directory"]).mkdir(parents=True, exist_ok=True)
    
    # Auto-seeding preference
    config["auto_start_seeding"] = Confirm.ask(
        "Start seeding automatically after creating torrent?",
        default=config.get("auto_start_seeding", True)
    )
    
    config["auto_torrent_management"] = Confirm.ask(
        "Enable automatic torrent management by default?",
        default=config.get("auto_torrent_management", True)
    )
    
    config["default_private"] = Confirm.ask(
        "Make torrents private by default (for private trackers)?",
        default=config.get("default_private", True)
    )
    
    # Torrent format
    console.print("\n[cyan]Default Torrent Format[/cyan]")
    console.print("[dim]Most private trackers only support v1 format[/dim]")
    
    format_options = {
        "1": "v1",
        "2": "v2",
        "3": "hybrid"
    }
    
    console.print("  1. v1 (Compatible with all trackers) [recommended]")
    console.print("  2. v2 (Modern format, limited tracker support)")
    console.print("  3. hybrid (Both formats, larger file)")
    
    format_choice = Prompt.ask("Select default format", choices=["1", "2", "3"], default="1")
    config["default_torrent_format"] = format_options[format_choice]
    
    # Cross-Seeding Support
    console.print("\n[cyan]Cross-Seeding Support[/cyan]")
    console.print("[dim]Setting a source tag helps identify torrents for safe cross-seeding[/dim]")
    
    config["default_source"] = Prompt.ask(
        "Default source tag (e.g., RED, OPS, MAM)",
        default=config.get("default_source", "")
    )
    
    if config["default_source"]:
        console.print(f"[green]✓ Source tag '{config['default_source']}' will be added to torrents[/green]")
        console.print("[yellow]ℹ️ Remember to download .torrent files for cross-seeding on other trackers[/yellow]")
    
    # Categories setup
    console.print("\n[cyan]Categories Setup[/cyan]")
    console.print("[dim]Categories help organize your torrents in qBittorrent[/dim]")
    
    categories = []
    suggested_categories = ["Movies", "TV Shows", "Music", "Audiobooks", "Software", "Games", "Books"]
    
    if Confirm.ask("Add suggested categories?", default=True):
        for cat in suggested_categories:
            if Confirm.ask(f"  Add '{cat}'?", default=True):
                categories.append(cat)
    
    while Confirm.ask("Add custom category?", default=False):
        category = Prompt.ask("Category name")
        if category and category not in categories:
            categories.append(category)
    
    config["categories"] = categories
    
    if categories:
        config["default_category"] = Prompt.ask(
            "Default category",
            choices=categories + [""],
            default=""
        )
    
    # Tags setup
    console.print("\n[cyan]Tags Setup[/cyan]")
    console.print("[dim]Tags allow flexible labeling of torrents[/dim]")
    
    tags = []
    suggested_tags = ["new", "seeding", "private", "public", "verified", "own-rip", "web-dl", "bluray"]
    
    if Confirm.ask("Add suggested tags?", default=False):
        for tag in suggested_tags:
            if Confirm.ask(f"  Add '{tag}'?", default=True):
                tags.append(tag)
    
    while Confirm.ask("Add custom tag?", default=False):
        tag = Prompt.ask("Tag name")
        if tag and tag not in tags:
            tags.append(tag)
    
    config["common_tags"] = tags
    
    if tags:
        default_tags = []
        if Confirm.ask("Select default tags to apply to all torrents?", default=False):
            console.print("Available tags: " + ", ".join(tags))
            tags_input = Prompt.ask("Default tags (comma-separated)", default="")
            default_tags = [t.strip() for t in tags_input.split(',') if t.strip() in tags]
        config["default_tags"] = default_tags
    
    # Default trackers
    console.print("\n[cyan]Default Tracker URLs[/cyan]")
    console.print("[dim]Add tracker URLs that will be used by default[/dim]")
    
    trackers = []
    # Suggest some public trackers
    public_trackers = [
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://open.stealth.si:80/announce",
        "udp://tracker.torrent.eu.org:451/announce"
    ]
    
    if Confirm.ask("Add suggested public trackers?", default=False):
        trackers.extend(public_trackers)
    
    while Confirm.ask("Add custom tracker?", default=False):
        tracker = Prompt.ask("Tracker URL")
        if tracker:
            trackers.append(tracker)
    
    # Save configuration
    save_config(config)
    console.print(f"\n[green]✅ Configuration saved to {CONFIG_FILE}[/green]")
    
    # Save trackers
    if trackers:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(TRACKERS_FILE, 'w') as f:
            f.write('\n'.join(trackers))
        console.print(f"[green]✅ Trackers saved to {TRACKERS_FILE}[/green]")
    
    console.print("\n[bold green]Setup complete! You can now create torrents.[/bold green]")
    console.print("Run [cyan]python run.py create[/cyan] to start creating torrents.")

def verify_config() -> bool:
    """Verify current configuration"""
    config = load_config()
    
    if not CONFIG_FILE.exists():
        console.print("[yellow]⚠️ No configuration found. Running setup...[/yellow]")
        setup_wizard()
        return True
    
    # Quick health check
    from qbit_api import run_health_check
    return run_health_check(config)

def edit_config():
    """Interactive configuration editor"""
    config = load_config()
    
    console.print(Panel.fit("[bold cyan]⚙️ Configuration Editor[/bold cyan]", border_style="cyan"))
    
    while True:
        # Show menu
        console.print("\n[cyan]What would you like to configure?[/cyan]")
        options = [
            "1. qBittorrent Connection",
            "2. Docker Settings",
            "3. Path Mappings",
            "4. Default Directories",
            "5. Categories & Tags",
            "6. Tracker URLs",
            "7. Default Behavior",
            "8. View All Settings",
            "9. Test Connection",
            "0. Exit"
        ]
        
        for opt in options:
            console.print(f"  {opt}")
        
        choice = Prompt.ask("\nSelect option", choices=["0","1","2","3","4","5","6","7","8","9"], default="0")
        
        if choice == "0":
            break
        elif choice == "1":
            edit_qbit_connection(config)
        elif choice == "2":
            edit_docker_settings(config)
        elif choice == "3":
            edit_path_mappings(config)
        elif choice == "4":
            edit_directories(config)
        elif choice == "5":
            edit_categories_tags(config)
        elif choice == "6":
            edit_trackers()
        elif choice == "7":
            edit_behavior(config)
        elif choice == "8":
            show_config()
        elif choice == "9":
            from qbit_api import run_health_check
            run_health_check(config)
        
        # Save after each change
        save_config(config)
        console.print("[green]✅ Settings saved[/green]")

def edit_qbit_connection(config: Dict[str, Any]):
    """Edit qBittorrent connection settings"""
    console.print("\n[cyan]qBittorrent Connection Settings[/cyan]")
    
    config["qbit_host"] = Prompt.ask("Host/IP", default=config.get("qbit_host", "localhost"))
    config["qbit_port"] = IntPrompt.ask("Port", default=config.get("qbit_port", 8080))
    config["qbit_username"] = Prompt.ask("Username", default=config.get("qbit_username", "admin"))
    
    if Confirm.ask("Update password?", default=False):
        password = getpass.getpass("Password (hidden): ")
        if password:
            config["qbit_password"] = password
    
    config["qbit_https"] = Confirm.ask("Use HTTPS?", default=config.get("qbit_https", False))

def edit_docker_settings(config: Dict[str, Any]):
    """Edit Docker settings"""
    console.print("\n[cyan]Docker Settings[/cyan]")
    
    config["docker_mode"] = Confirm.ask("Use Docker mode?", default=config.get("docker_mode", False))
    
    if config["docker_mode"]:
        config["docker_container"] = Prompt.ask(
            "Container name",
            default=config.get("docker_container", "qbittorrent")
        )
        
        # Test Docker connectivity
        from qbit_api import test_docker_connectivity
        test_docker_connectivity(config["docker_container"])

def edit_path_mappings(config: Dict[str, Any]):
    """Edit Docker path mappings"""
    if not config.get("docker_mode"):
        console.print("[yellow]Docker mode is disabled[/yellow]")
        return
    
    console.print("\n[cyan]Path Mappings (Host → Container)[/cyan]")
    
    mappings = config.get("docker_mappings", {})
    
    # Show current mappings
    if mappings:
        table = Table(title="Current Mappings")
        table.add_column("Host Path", style="cyan")
        table.add_column("Container Path", style="green")
        
        for host, container in mappings.items():
            table.add_row(host, container)
        
        console.print(table)
    
    # Edit mappings
    while True:
        action = Prompt.ask(
            "\nAction",
            choices=["add", "remove", "clear", "done"],
            default="done"
        )
        
        if action == "done":
            break
        elif action == "add":
            host = Prompt.ask("Host path")
            container = Prompt.ask(f"Container path for {host}")
            mappings[host] = container
        elif action == "remove":
            if mappings:
                host = Prompt.ask("Host path to remove", choices=list(mappings.keys()))
                del mappings[host]
        elif action == "clear":
            if Confirm.ask("Clear all mappings?", default=False):
                mappings.clear()
    
    config["docker_mappings"] = mappings

def edit_directories(config: Dict[str, Any]):
    """Edit default directories"""
    console.print("\n[cyan]Default Directories[/cyan]")
    
    config["output_directory"] = Prompt.ask(
        "Default .torrent output directory",
        default=config.get("output_directory", str(Path.home() / "torrents"))
    )
    
    Path(config["output_directory"]).mkdir(parents=True, exist_ok=True)

def edit_categories_tags(config: Dict[str, Any]):
    """Edit categories and tags"""
    console.print("\n[cyan]Categories & Tags[/cyan]")
    
    # Categories
    categories = config.get("categories", [])
    console.print(f"\nCurrent categories: {', '.join(categories) if categories else 'None'}")
    
    if Confirm.ask("Edit categories?", default=False):
        while True:
            action = Prompt.ask("Action", choices=["add", "remove", "done"], default="done")
            if action == "done":
                break
            elif action == "add":
                cat = Prompt.ask("Category name")
                if cat and cat not in categories:
                    categories.append(cat)
            elif action == "remove" and categories:
                cat = Prompt.ask("Remove category", choices=categories)
                categories.remove(cat)
        
        config["categories"] = categories
    
    # Tags
    tags = config.get("common_tags", [])
    console.print(f"\nCurrent tags: {', '.join(tags) if tags else 'None'}")
    
    if Confirm.ask("Edit tags?", default=False):
        while True:
            action = Prompt.ask("Action", choices=["add", "remove", "done"], default="done")
            if action == "done":
                break
            elif action == "add":
                tag = Prompt.ask("Tag name")
                if tag and tag not in tags:
                    tags.append(tag)
            elif action == "remove" and tags:
                tag = Prompt.ask("Remove tag", choices=tags)
                tags.remove(tag)
        
        config["common_tags"] = tags

def edit_trackers():
    """Edit default tracker URLs"""
    console.print("\n[cyan]Default Tracker URLs[/cyan]")
    
    trackers_file = CONFIG_DIR / "trackers.txt"
    trackers = []
    
    if trackers_file.exists():
        with open(trackers_file) as f:
            trackers = [line.strip() for line in f if line.strip()]
    
    console.print(f"Current trackers ({len(trackers)}):")
    for t in trackers:
        console.print(f"  • {t}")
    
    while True:
        action = Prompt.ask("\nAction", choices=["add", "remove", "clear", "done"], default="done")
        
        if action == "done":
            break
        elif action == "add":
            tracker = Prompt.ask("Tracker URL")
            if tracker and tracker not in trackers:
                trackers.append(tracker)
        elif action == "remove" and trackers:
            # Show numbered list
            for i, t in enumerate(trackers, 1):
                console.print(f"{i}. {t}")
            idx = IntPrompt.ask("Remove number", default=1)
            if 1 <= idx <= len(trackers):
                trackers.pop(idx - 1)
            else:
                console.print("[red]Invalid number[/red]")
        elif action == "clear":
            if Confirm.ask("Clear all trackers?", default=False):
                trackers.clear()
    
    # Save trackers
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(trackers_file, 'w') as f:
        f.write('\n'.join(trackers))

def edit_behavior(config: Dict[str, Any]):
    """Edit default behavior settings"""
    console.print("\n[cyan]Default Behavior[/cyan]")
    
    config["auto_start_seeding"] = Confirm.ask(
        "Auto-start seeding after creation?",
        default=config.get("auto_start_seeding", True)
    )
    
    config["auto_torrent_management"] = Confirm.ask(
        "Enable automatic torrent management by default?",
        default=config.get("auto_torrent_management", True)
    )
    
    config["default_private"] = Confirm.ask(
        "Make torrents private by default?",
        default=config.get("default_private", True)
    )
    
    # Torrent format setting
    console.print("\n[cyan]Default Torrent Format:[/cyan]")
    console.print("  v1: Compatible with all clients (recommended)")
    console.print("  v2: Modern format with better hash tree")
    console.print("  hybrid: Both v1 and v2 (larger file)")
    
    current_format = config.get("default_torrent_format", "v1")
    console.print(f"Current format: {current_format}")
    
    if Confirm.ask("Change default format?", default=False):
        format_choice = Prompt.ask(
            "Default format",
            choices=["v1", "v2", "hybrid"],
            default=current_format
        )
        config["default_torrent_format"] = format_choice
        
        if format_choice == "v2":
            console.print("[yellow]⚠️ Note: Many trackers don't support v2 torrents yet[/yellow]")
    
    # Default piece size
    sizes = ["Auto", "16 KiB", "32 KiB", "64 KiB", "128 KiB", "256 KiB", 
            "512 KiB", "1 MiB", "2 MiB", "4 MiB", "8 MiB", "16 MiB"]
    
    current = config.get("default_piece_size", "Auto")
    console.print(f"\nCurrent piece size: {current}")
    
    if Confirm.ask("Change piece size?", default=False):
        for i, size in enumerate(sizes, 1):
            console.print(f"{i}. {size}")
        
        idx = IntPrompt.ask("Select", default=1)
        if 1 <= idx <= len(sizes):
            config["default_piece_size"] = sizes[idx - 1]
        else:
            console.print("[red]Invalid selection[/red]")
            config["default_piece_size"] = "Auto"
    
    # Source field configuration
    console.print("\n[cyan]Cross-Seeding Configuration:[/cyan]")
    
    config["default_source"] = Prompt.ask(
        "Default source tag (empty for none)",
        default=config.get("default_source", "")
    )
    
    if config["default_source"]:
        console.print(f"[yellow]ℹ️ Torrents will be tagged with source '{config['default_source']}' for cross-seeding[/yellow]")
    
    # Edit common sources list
    if Confirm.ask("Edit common source tags?", default=False):
        sources = config.get("common_sources", [])
        console.print(f"Current sources: {', '.join(sources)}")
        
        while True:
            action = Prompt.ask("Action", choices=["add", "remove", "clear", "done"], default="done")
            if action == "done":
                break
            elif action == "add":
                source = Prompt.ask("Source tag to add")
                if source and source not in sources:
                    sources.append(source)
            elif action == "remove" and sources:
                source = Prompt.ask("Remove source", choices=sources)
                sources.remove(source)
            elif action == "clear":
                if Confirm.ask("Clear all sources?", default=False):
                    sources.clear()
        
        config["common_sources"] = sources
    
    # Advanced options
    console.print("\n[cyan]Advanced Creation Options:[/cyan]")
    
    config["optimize_alignment"] = Confirm.ask(
        "Optimize file alignment by default?",
        default=config.get("optimize_alignment", True)
    )
    
    # Backup directory for cross-seeding
    config["backup_directory"] = Prompt.ask(
        "Backup directory for .torrent files",
        default=config.get("backup_directory", str(Path.home() / "torrent_backups"))
    )
    
    Path(config["backup_directory"]).mkdir(parents=True, exist_ok=True)

def show_config():
    """Display current configuration"""
    config = load_config()
    
    console.print(Panel.fit("[bold cyan]📋 Current Configuration[/bold cyan]", border_style="cyan"))
    
    # Format config as JSON for display
    json_str = json.dumps(config, indent=2, sort_keys=True)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
    console.print(syntax)
    
    # Also show trackers
    trackers_file = CONFIG_DIR / "trackers.txt"
    if trackers_file.exists():
        console.print("\n[cyan]Default Trackers:[/cyan]")
        with open(trackers_file) as f:
            for line in f:
                if line.strip():
                    console.print(f"  • {line.strip()}")

def reset_config():
    """Reset configuration to defaults"""
    config = get_default_config()
    save_config(config)
    
    # Clear trackers
    trackers_file = CONFIG_DIR / "trackers.txt"
    if trackers_file.exists():
        trackers_file.unlink()
