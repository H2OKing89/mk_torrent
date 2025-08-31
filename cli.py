#!/usr/bin/env python3
"""Main CLI interface for Torrent Creator"""

import typer
from pathlib import Path
from typing import Optional, List, Dict, Any
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress
from rich.table import Table

from config import (
    load_config, 
    save_config, 
    setup_wizard
)
from torrent_creator import TorrentCreator, QBitMode
from qbit_api import (
    run_health_check, 
    QBittorrentAPI,
    validate_qbittorrent_config,  # Move these imports here
    sync_qbittorrent_metadata      # Move these imports here
)
from validator import validate_torrent
from templates import list_templates, apply_template_cli

# Handle both module and direct execution - simplified approach
try:
    from torrent_creator import TorrentCreator, QBitMode
    from database import get_recent_torrents, save_torrent_history
    from config import load_config, save_config, setup_wizard, verify_config
    from qbit_api import run_health_check, QBittorrentAPI
except ImportError as e:
    console = Console()
    console.print(f"[red]Import error: {e}[/red]")
    console.print("[yellow]Make sure all dependencies are installed:[/yellow]")
    console.print("pip install -r requirements.txt")
    sys.exit(1)

app = typer.Typer(
    help="🎯 Interactive Torrent Creator - Easy & Powerful",
    add_completion=False
)
console = Console()

def ensure_setup():
    """Ensure the application is properly configured"""
    config_file = Path.home() / ".config" / "torrent_creator" / "config.json"
    if not config_file.exists():
        console.print("[yellow]⚠️ First time setup required![/yellow]")
        setup_wizard()
        return True
    return verify_config()

@app.command()
def create(
    batch: bool = typer.Option(False, "--batch", "-b", help="Create multiple torrents"),
    docker: Optional[str] = typer.Option(None, "--docker", "-d", help="Docker container name"),
    interactive: bool = typer.Option(True, "--interactive", "-i", help="Interactive mode"),
    skip_checks: bool = typer.Option(False, "--skip-checks", help="Skip health checks")
):
    """Create torrent(s) interactively"""
    
    # Show welcome banner
    console.print(Panel.fit(
        "[bold cyan]🎯 Torrent Creator[/bold cyan]\n"
        "[dim]Easy interactive torrent creation for qBittorrent[/dim]",
        border_style="cyan"
    ))
    
    # Ensure setup and run health checks
    if not skip_checks:
        if not ensure_setup():
            if not Confirm.ask("[yellow]Health checks failed. Continue anyway?[/yellow]", default=False):
                console.print("[red]Aborted.[/red]")
                return
    
    # Load config
    config = load_config()
    
    # Determine mode
    if docker:
        mode = QBitMode.DOCKER
        container_name = docker
    elif config.get("docker_mode"):
        mode = QBitMode.DOCKER
        container_name = config.get("docker_container", "qbittorrent")
    else:
        mode = QBitMode.LOCAL
        container_name = None
    
    creator = TorrentCreator(
        mode=mode, 
        container_name=container_name,  # Now properly Optional[str]
        config=config
    )
    
    if mode == QBitMode.DOCKER:
        console.print(f"[cyan]Using Docker container: {container_name}[/cyan]")
    
    # Create torrents
    if batch:
        creator.create_batch()
    else:
        creator.create_single()
        
        # Ask if user wants to create another
        while Confirm.ask("\nCreate another torrent?", default=False):
            creator.create_single()

@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of entries to show")
):
    """Show torrent creation history"""
    
    torrents = get_recent_torrents(limit)
    
    if not torrents:
        console.print("[yellow]No torrent history found[/yellow]")
        return
    
    # Create table
    table = Table(title="Recent Torrent Creations", show_lines=True)
    table.add_column("Created", style="cyan", no_wrap=True)
    table.add_column("Source", style="green")
    table.add_column("Size", style="yellow")
    table.add_column("Private", style="magenta")
    
    for t in torrents:
        table.add_row(
            t.created_at.strftime("%Y-%m-%d %H:%M"),
            Path(t.source_path).name,
            t.file_size,
            "✓" if t.private else "✗"
        )
    
    console.print(table)

@app.command()
def health():
    """Run health checks for qBittorrent connectivity"""
    config = load_config()
    
    if not Path.home().joinpath(".config/torrent_creator/config.json").exists():
        console.print("[yellow]No configuration found. Run setup first.[/yellow]")
        if Confirm.ask("Run setup now?", default=True):
            setup_wizard()
    else:
        run_health_check(config)
        
        # Offer to reconfigure if needed
        if Confirm.ask("\n[cyan]Reconfigure settings?[/cyan]", default=False):
            setup_wizard()

@app.command()
def setup():
    """Run the setup wizard"""
    setup_wizard()  # Update the function call

@app.command()
def quick(path: Optional[str] = typer.Argument(None, help="Path to file or folder")):
    """Quick torrent creation with minimal prompts"""
    from torrent_creator import TorrentCreator, QBitMode
    
    config = load_config()
    
    # Quick validation
    if not validate_qbittorrent_config(config):
        console.print("[red]✗ qBittorrent connection failed. Run 'setup' first.[/red]")
        raise typer.Exit(1)
    
    # Get path
    if not path:
        path = Prompt.ask("Path to create torrent for", default=".")
    
    source_path = Path(path).expanduser().resolve()
    if not source_path.exists():
        console.print(f"[red]Path does not exist: {source_path}[/red]")
        raise typer.Exit(1)
    
    # Determine mode
    mode = QBitMode.DOCKER if config.get("docker_mode") else QBitMode.LOCAL
    container_name = config.get("docker_container") if mode == QBitMode.DOCKER else None
    
    # Create torrent creator with defaults
    creator = TorrentCreator(mode=mode, container_name=container_name, config=config)
    
    if not creator.client:
        console.print("[red]❌ qBittorrent API not connected[/red]")
        raise typer.Exit(1)
    
    # Use all defaults from config
    creator.load_default_trackers()
    creator.private = config.get("default_private", True)
    creator.torrent_format = config.get("default_torrent_format", "v1")
    creator.source = config.get("default_source", "")
    creator.category = config.get("default_category", "")
    creator.tags = config.get("default_tags", [])
    creator.start_seeding = config.get("auto_start_seeding", True)
    creator.auto_management = config.get("auto_torrent_management", True)
    
    # Output location
    output_dir = Path(config.get("output_directory", Path.home() / "torrents"))
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{source_path.name}.torrent"
    
    # Create torrent
    console.print(f"[cyan]Creating torrent for: {source_path.name}[/cyan]")
    console.print(f"[dim]Format: {creator.torrent_format}[/dim]")
    console.print(f"[dim]Private: {'Yes' if creator.private else 'No'}[/dim]")
    if creator.source:
        console.print(f"[dim]Source: {creator.source}[/dim]")
    
    if creator.create_torrent_via_api(source_path, output_path):
        console.print(f"[green]✅ Torrent created successfully![/green]")
        console.print(f"[green]   Location: {output_path}[/green]")
        if creator.start_seeding:
            console.print(f"[green]   Status: Seeding in qBittorrent[/green]")
    else:
        console.print("[red]✗ Failed to create torrent[/red]")
        raise typer.Exit(1)

@app.command()
def config(
    edit: bool = typer.Option(False, "--edit", "-e", help="Edit specific setting"),
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
    reset: bool = typer.Option(False, "--reset", "-r", help="Reset to defaults")
):
    """Manage configuration settings"""
    from config import edit_config, show_config, reset_config
    
    if reset:
        if Confirm.ask("[yellow]⚠️ Reset all settings to defaults?[/yellow]", default=False):
            reset_config()
            console.print("[green]✅ Configuration reset to defaults[/green]")
    elif show:
        show_config()
    else:
        # Default to edit mode
        edit_config()

@app.command()
def wizard():
    """Interactive wizard for common tasks"""
    from wizard import run_wizard
    run_wizard()

@app.command()
def validate(
    path: str = typer.Argument(..., help="Path to validate for torrent creation")
):
    """Validate a path before creating torrent"""
    from validator import validate_path
    validate_path(path)

@app.command()
def templates():
    """Manage torrent templates for quick reuse"""
    from templates import manage_templates
    manage_templates()

@app.command()
def verify(
    hash: Optional[str] = typer.Argument(None, help="Torrent hash to verify"),
    recent: int = typer.Option(0, "--recent", "-r", help="Verify N most recent torrents")
):
    """Verify torrent settings and status"""
    config = load_config()
    
    try:
        import qbittorrentapi
        client = qbittorrentapi.Client(
            host=f"{config.get('qbit_host', 'localhost')}:{config.get('qbit_port', 8080)}",
            username=config.get("qbit_username", "admin"),
            password=config.get("qbit_password", "adminadmin"),
            VERIFY_WEBUI_CERTIFICATE=False if config.get("qbit_https", False) else True
        )
        client.auth_log_in()
    except Exception as e:
        console.print(f"[red]Could not connect to qBittorrent: {e}[/red]")
        return
    
    if hash:
        # Verify specific torrent
        torrents = client.torrents_info(torrent_hashes=hash)
        if not torrents:
            console.print(f"[red]Torrent not found: {hash}[/red]")
            return
    elif recent > 0:
        # Verify recent torrents
        torrents = client.torrents_info(sort="added_on", reverse=True, limit=recent)
    else:
        # Show help
        console.print("[yellow]Specify --hash or --recent to verify torrents[/yellow]")
        return
    
    # Create verification table
    table = Table(title="Torrent Verification", show_lines=True)
    table.add_column("Name", style="cyan", max_width=50)
    table.add_column("Category", style="green")
    table.add_column("Tags", style="yellow", max_width=30)
    table.add_column("Private", style="magenta")
    table.add_column("Auto Mgmt", style="blue")
    table.add_column("State", style="white")
    
    for torrent in torrents:
        table.add_row(
            torrent.name[:47] + "..." if len(torrent.name) > 50 else torrent.name,
            torrent.category or "[dim]none[/dim]",
            torrent.tags[:27] + "..." if len(torrent.tags) > 30 else torrent.tags or "[dim]none[/dim]",
            "✓" if getattr(torrent, 'is_private', False) else "✗",
            "✓" if torrent.auto_tmm else "✗",
            torrent.state
        )
    
    console.print(table)
    
    # Show summary
    console.print(f"\n[cyan]Verified {len(torrents)} torrent(s)[/cyan]")

@app.command()
def info():
    """Show current configuration and system info"""
    config = load_config()
    
    console.print(Panel.fit("[bold cyan]📊 System Information[/bold cyan]", border_style="cyan"))
    
    # Try to connect to qBittorrent
    try:
        import qbittorrentapi
        client = qbittorrentapi.Client(
            host=f"{config.get('qbit_host', 'localhost')}:{config.get('qbit_port', 8080)}",
            username=config.get("qbit_username", "admin"),
            password=config.get("qbit_password", "adminadmin"),
            VERIFY_WEBUI_CERTIFICATE=False if config.get("qbit_https", False) else True
        )
        client.auth_log_in()
        
        console.print("\n[cyan]qBittorrent Info:[/cyan]")
        console.print(f"  Version: {client.app.version}")
        console.print(f"  Web API: {client.app.web_api_version}")
        console.print(f"  Connection: [green]✓ Connected[/green]")
    except:
        console.print("\n[cyan]qBittorrent Info:[/cyan]")
        console.print(f"  Connection: [red]✗ Not connected[/red]")
    
    # Show configuration
    console.print("\n[cyan]Current Settings:[/cyan]")
    console.print(f"  Default Format: {config.get('default_torrent_format', 'v1')}")
    console.print(f"  Private by Default: {config.get('default_private', True)}")
    console.print(f"  Auto-seeding: {config.get('auto_start_seeding', True)}")
    console.print(f"  Auto Management: {config.get('auto_torrent_management', True)}")
    console.print(f"  Output Directory: {config.get('output_directory', 'Not set')}")
    
    if config.get("default_category"):
        console.print(f"  Default Category: {config.get('default_category')}")
    
    if config.get("default_tags"):
        console.print(f"  Default Tags: {', '.join(config.get('default_tags'))}")
    
    # Show tracker count
    trackers_file = Path.home() / ".config" / "torrent_creator" / "trackers.txt"
    if trackers_file.exists():
        with open(trackers_file) as f:
            tracker_count = len([line for line in f if line.strip()])
        console.print(f"  Configured Trackers: {tracker_count}")
    
    # Format recommendation
    console.print("\n[cyan]Format Recommendations:[/cyan]")
    console.print("  • v1: Best compatibility, works with all trackers ✓")
    console.print("  • v2: Modern format, limited tracker support ⚠️")
    console.print("  • hybrid: Largest file size, maximum compatibility")
    
    if config.get('default_torrent_format') == 'v2':
        console.print("\n[yellow]⚠️ Warning: You're using v2 format by default.[/yellow]")
        console.print("[yellow]Many private trackers don't support v2 torrents yet.[/yellow]")
        console.print("[yellow]Consider switching to v1 for better compatibility.[/yellow]")

@app.command()
def crossseed():
    """Manage torrents for cross-seeding"""
    from cross_seed import cross_seed_wizard
    cross_seed_wizard()

@app.command()
def batch(
    path: Optional[str] = typer.Argument(None, help="Base directory containing items"),
    max_items: int = typer.Option(0, "--max", "-m", help="Maximum number of items to select"),
    pattern: str = typer.Option("", "--pattern", "-p", help="Filter items by pattern (e.g., '*.mkv')"),
    recent: bool = typer.Option(False, "--recent", "-r", help="Sort by most recent first"),
    skip_checks: bool = typer.Option(False, "--skip-checks", help="Skip connectivity checks")
):
    """Batch create torrents with smart selection"""
    from pathlib import Path
    import fnmatch
    
    config = load_config()
    
    # Validate qBittorrent connection
    if not skip_checks:
        if not validate_qbittorrent_config(config):
            console.print("[red]✗ qBittorrent connection failed. Run 'setup' first.[/red]")
            raise typer.Exit(1)
    
    # Determine mode
    mode = QBitMode.DOCKER if config.get("docker_mode") else QBitMode.LOCAL
    container_name = config.get("docker_container") if mode == QBitMode.DOCKER else None
    
    # Sync categories and tags
    console.print("Syncing categories and tags with qBittorrent...")
    sync_qbittorrent_metadata(config)
    
    # Create torrent creator
    from torrent_creator import TorrentCreator
    creator = TorrentCreator(mode=mode, container_name=container_name, config=config)
    
    # Get base path
    if path:
        base_path = Path(path).expanduser().resolve()
    else:
        base_path = Path(Prompt.ask("Base directory", default=".")).expanduser().resolve()
    
    if not base_path.exists() or not base_path.is_dir():
        console.print(f"[red]Invalid directory: {base_path}[/red]")
        raise typer.Exit(1)
    
    # Get all items
    all_items = []
    for item in base_path.iterdir():
        if item.name.startswith('.'):
            continue
        if pattern and not fnmatch.fnmatch(item.name, pattern):
            continue
        all_items.append(item)
    
    if not all_items:
        console.print("[yellow]No items found matching criteria[/yellow]")
        return
    
    # Sort if requested
    if recent:
        all_items.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    else:
        all_items.sort(key=lambda p: p.name)
    
    console.print(f"[cyan]Found {len(all_items)} items[/cyan]")
    
    # Limit if requested
    if max_items > 0 and len(all_items) > max_items:
        console.print(f"[yellow]Limiting to first {max_items} items[/yellow]")
        all_items = all_items[:max_items]
    
    # Show items and confirm
    console.print("\n[cyan]Items to process:[/cyan]")
    for item in all_items[:20]:  # Show first 20
        size = calculate_item_size(item)
        console.print(f"  • {item.name} [{format_size(size)}]")
    if len(all_items) > 20:
        console.print(f"  [dim]... and {len(all_items) - 20} more[/dim]")
    
    if not Confirm.ask(f"\nCreate {len(all_items)} torrents?", default=True):
        return
    
    # Create torrents
    create_batch_torrents(creator, all_items, config)

def create_batch_torrents(creator, items: List[Path], config: Dict[str, Any]):
    """Create torrents for selected items"""
    from tqdm import tqdm
    
    output_dir = Path(config.get("output_directory", Path.home() / "torrents"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure creator with defaults
    creator.load_default_trackers()
    creator.private = config.get("default_private", True)
    creator.torrent_format = config.get("default_torrent_format", "v1")
    creator.source = config.get("default_source", "")
    creator.category = config.get("default_category", "")
    creator.tags = config.get("default_tags", [])
    creator.start_seeding = config.get("auto_start_seeding", True)
    creator.auto_management = config.get("auto_torrent_management", True)
    
    successful = 0
    failed = 0
    
    console.print(f"\n[cyan]Creating {len(items)} torrents...[/cyan]")
    
    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Creating torrents...", total=len(items))
        
        for item in items:
            torrent_name = f"{item.name}.torrent"
            output_path = output_dir / torrent_name
            
            try:
                if creator.create_torrent_via_api(item, output_path):
                    successful += 1
                    progress.console.print(f"[green]✓[/green] {item.name}")
                else:
                    failed += 1
                    progress.console.print(f"[red]✗[/red] {item.name}")
            except Exception as e:
                failed += 1
                progress.console.print(f"[red]✗[/red] {item.name}: {e}")
            
            progress.update(task, advance=1)
    
    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  [green]Successful: {successful}[/green]")
    if failed > 0:
        console.print(f"  [red]Failed: {failed}[/red]")

def calculate_item_size(path: Path) -> int:
    """Calculate size of file or directory"""
    if path.is_file():
        return path.stat().st_size
    else:
        total = 0
        for file in path.rglob("*"):
            if file.is_file():
                total += file.stat().st_size
        return total

def format_size(bytes: int) -> str:
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} PB"

def main():
    """Main entry point"""
    app()

if __name__ == "__main__":
    main()
    main()
    """Main entry point"""
    app()

if __name__ == "__main__":
    main()
    main()
