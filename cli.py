#!/usr/bin/env python3
"""Main CLI interface for Torrent Creator"""
from pathlib import Path
from typing import Optional, List, Dict, Any
import typer
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress
from rich.table import Table

from config import (
    load_config, 
    save_config, 
    setup_wizard,
    show_config,
    edit_config
)
from torrent_creator import TorrentCreator, QBitMode
from core_health_checks import (
    run_comprehensive_health_check, 
    run_quick_health_check, 
    ContinuousMonitor
)
from wizard import run_wizard
from feature_templates import (
    load_templates,
    save_template,
    list_templates
)
from feature_validator import validate_path
from api_qbittorrent import validate_qbittorrent_config, sync_qbittorrent_metadata

console = Console()
app = typer.Typer(
    help="Interactive Torrent Creator for qBittorrent",
    add_completion=False
)

@app.command()
def setup():
    """Run initial setup wizard"""
    setup_wizard()

@app.command()
def create(
    path: Optional[str] = typer.Argument(None, help="Path to create torrent for"),
    batch: bool = typer.Option(False, "--batch", "-b", help="Batch mode for multiple torrents"),
    docker: Optional[str] = typer.Option(None, "--docker", "-d", help="Docker container name"),
    quick: bool = typer.Option(False, "--quick", "-q", help="Quick mode with minimal prompts")
):
    """Create torrent(s) interactively"""
    config = load_config()
    
    # Check health before creating
    if batch and not run_quick_health_check(config):
        if not Confirm.ask("[yellow]System health check warnings detected. Continue anyway?[/yellow]", default=False):
            raise typer.Exit(1)
    
    if docker:
        mode = QBitMode.DOCKER
        container_name = docker
    else:
        mode = QBitMode.LOCAL
        container_name = None
    
    creator = TorrentCreator(mode=mode, container_name=container_name, config=config)
    
    if batch:
        creator.batch_create_interactive()
    elif quick:
        if not path:
            path = Prompt.ask("Path to create torrent for")
        # Quick creation using API directly
        output_dir = Path(config.get("output_directory", Path.home() / "torrents"))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{Path(path).name}.torrent"
        creator.load_default_trackers()
        success = creator.create_torrent_via_api(Path(path), output_path)
        if success:
            console.print(f"[green]✅ Torrent created: {output_path}[/green]")
        else:
            console.print("[red]❌ Failed to create torrent[/red]")
    else:
        if path:
            # Set up creator for single file and run interactive
            console.print(f"[cyan]Creating torrent for: {path}[/cyan]")
            creator.create_single()
        else:
            creator.create_single()

@app.command()
def wizard():
    """Run guided wizard for common tasks"""
    run_wizard()

@app.command()
def quick(path: Optional[str] = typer.Argument(None)):
    """Quick torrent creation with defaults"""
    config = load_config()
    creator = TorrentCreator(config=config)
    
    if not path:
        path = Prompt.ask("Path to create torrent for")
    
    # Quick creation using API directly
    output_dir = Path(config.get("output_directory", Path.home() / "torrents"))
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{Path(path).name}.torrent"
    creator.load_default_trackers()
    success = creator.create_torrent_via_api(Path(path), output_path)
    if success:
        console.print(f"[green]✅ Torrent created: {output_path}[/green]")
    else:
        console.print("[red]❌ Failed to create torrent[/red]")

@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
    edit: bool = typer.Option(False, "--edit", "-e", help="Edit configuration interactively"),
    reset: bool = typer.Option(False, "--reset", "-r", help="Reset to defaults")
):
    """Manage configuration"""
    if reset:
        if Confirm.ask("Reset configuration to defaults?", default=False):
            setup_wizard()
    elif show:
        config = load_config()
        show_config()
    elif edit:
        # Import here to avoid circular dependency
        config = load_config()
        edit_config()
    else:
        # Default to interactive editor
        config = load_config()
        edit_config()

@app.command()
def health(
    comprehensive: bool = typer.Option(False, "--comprehensive", "-c", help="Run comprehensive health checks"),
    monitor: bool = typer.Option(False, "--monitor", "-m", help="Monitor continuously"),
    duration: int = typer.Option(300, "--duration", "-d", help="Monitor duration in seconds")
):
    """Run system health checks"""
    config = load_config()
    
    if monitor:
        monitor_obj = ContinuousMonitor(config)
        try:
            monitor_obj.monitor(duration)
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    elif comprehensive:
        success = run_comprehensive_health_check(config)
        raise typer.Exit(0 if success else 1)
    else:
        success = run_quick_health_check(config)
        raise typer.Exit(0 if success else 1)

@app.command()
def validate(path: str = typer.Argument(..., help="Path to validate")):
    """Validate a path for torrent creation"""
    from feature_validator import validate_path
    
    is_valid, errors = validate_path(path)
    
    if is_valid:
        console.print(f"[green]✅ Path is valid for torrent creation: {path}[/green]")
    else:
        console.print(f"[red]❌ Path validation failed:[/red]")
        for error in errors:
            console.print(f"  • {error}")
    
    raise typer.Exit(0 if is_valid else 1)

@app.command()
def templates(
    list_only: bool = typer.Option(False, "--list", "-l", help="List templates only"),
    apply: Optional[str] = typer.Option(None, "--apply", "-a", help="Apply template by name"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Path for template application")
):
    """Manage torrent templates"""
    if list_only:
        templates = list_templates()
        if templates:
            table = Table(title="Available Templates")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Private", style="yellow")
            
            for template in templates:
                table.add_row(
                    template.get('name', 'unnamed'),
                    template.get('type', 'general'),
                    "Yes" if template.get('private', False) else "No"
                )
            console.print(table)
        else:
            console.print("[yellow]No templates found[/yellow]")
    elif apply and path:
        # Import here to avoid issues
        from feature_templates import apply_template_cli
        success = apply_template_cli(apply, Path(path))
        raise typer.Exit(0 if success else 1)
    else:
        # Interactive template management
        from feature_templates import create_template, edit_template, delete_template, view_templates
        
        templates_dict = {t['name']: t for t in list_templates()}
        
        action = Prompt.ask(
            "Template action",
            choices=["view", "create", "edit", "delete", "apply"],
            default="view"
        )
        
        if action == "view":
            view_templates(templates_dict)
        elif action == "create":
            create_template(templates_dict)
            save_template(templates_dict)
        elif action == "edit":
            edit_template(templates_dict)
            save_template(templates_dict)
        elif action == "delete":
            delete_template(templates_dict)
            save_template(templates_dict)
        elif action == "apply":
            from feature_templates import apply_template
            apply_template(templates_dict)

@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of entries to show"),
    clear: bool = typer.Option(False, "--clear", help="Clear history")
):
    """View torrent creation history"""
    # For now, just show a placeholder
    console.print("[yellow]History tracking not yet implemented[/yellow]")
    console.print("[dim]This will show recent torrent creations[/dim]")

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
        tags = config.get("default_tags", [])
        if isinstance(tags, list):
            console.print(f"  Default Tags: {', '.join(tags)}")
        else:
            console.print(f"  Default Tags: {tags}")
    
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
    from feature_cross_seed import cross_seed_wizard
    cross_seed_wizard()

@app.command()
def metadata(
    path: str = typer.Argument(..., help="Path to extract metadata from"),
    format: str = typer.Option("json", "--format", "-f", help="Output format (json, table)"),
    save: Optional[str] = typer.Option(None, "--save", "-s", help="Save metadata to file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed metadata")
):
    """Extract and display metadata for RED compliance"""
    from feature_metadata_engine import process_album_metadata
    from pathlib import Path
    import json
    
    source_path = Path(path)
    if not source_path.exists():
        console.print(f"[red]✗ Path does not exist: {path}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Extracting metadata from: {source_path.name}[/cyan]")
    
    try:
        metadata = process_album_metadata(source_path)
        
        if format == "table":
            # Display in table format
            table = Table(title="Metadata Summary", show_header=True)
            table.add_column("Field", style="cyan", min_width=15)
            table.add_column("Value", style="white")
            
            # Basic fields
            if metadata.get('artist'):
                table.add_row("Artist", str(metadata['artist']))
            if metadata.get('album'):
                table.add_row("Album", str(metadata['album']))
            if metadata.get('year'):
                table.add_row("Year", str(metadata['year']))
            if metadata.get('format'):
                table.add_row("Format", str(metadata['format']))
            if metadata.get('encoding'):
                table.add_row("Encoding", str(metadata['encoding']))
                
            # Audio quality information
            if metadata.get('bitrate'):
                bitrate_kbps = metadata['bitrate'] // 1000
                vbr_status = "VBR" if metadata.get('vbr') else "CBR"
                table.add_row("Bitrate", f"{bitrate_kbps} kbps ({vbr_status})")
            
            if metadata.get('sample_rate'):
                table.add_row("Sample Rate", f"{metadata['sample_rate']} Hz")
            
            if metadata.get('channels'):
                channel_desc = "Stereo" if metadata['channels'] == 2 else f"{metadata['channels']} channels"
                table.add_row("Channels", channel_desc)
            
            if metadata.get('duration'):
                duration_mins = int(metadata['duration'] // 60)
                duration_secs = int(metadata['duration'] % 60)
                table.add_row("Duration", f"{duration_mins}:{duration_secs:02d}")
            
            # Validation status
            validation = metadata.get('validation', {})
            score = validation.get('score', 0)
            status = "✓ Valid" if validation.get('valid') else "⚠ Issues"
            table.add_row("Validation", f"{status} ({score}/100)")
            
            console.print(table)
            
            if verbose and validation.get('warnings'):
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in validation['warnings']:
                    console.print(f"  • {warning}")
                    
            if validation.get('errors'):
                console.print("\n[red]Errors:[/red]")
                for error in validation['errors']:
                    console.print(f"  • {error}")
                    
        else:
            # JSON format
            if verbose:
                console.print(json.dumps(metadata, indent=2, default=str))
            else:
                # Simplified output
                summary = {
                    'artist': metadata.get('artist'),
                    'album': metadata.get('album'), 
                    'year': metadata.get('year'),
                    'format': metadata.get('format'),
                    'encoding': metadata.get('encoding'),
                    'validation_score': metadata.get('validation', {}).get('score', 0),
                    'ready_for_upload': metadata.get('validation', {}).get('valid', False)
                }
                console.print(json.dumps(summary, indent=2, default=str))
        
        # Save to file if requested
        if save:
            save_path = Path(save)
            with open(save_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            console.print(f"[green]✓ Metadata saved to: {save_path}[/green]")
            
    except Exception as e:
        console.print(f"[red]✗ Error extracting metadata: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def upload(
    path: str = typer.Argument(..., help="Path to upload (directory or torrent file)"),
    tracker: str = typer.Option("red", "--tracker", "-t", help="Tracker to upload to (red, ops)"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Perform dry run only"),
    check_existing: bool = typer.Option(True, "--check-existing/--no-check", help="Check for existing torrents"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompts")
):
    """Upload torrent to private tracker with metadata processing"""
    from pathlib import Path
    from tracker_red_integration import integrate_upload_workflow
    
    source_path = Path(path)
    if not source_path.exists():
        console.print(f"[red]✗ Path does not exist: {path}[/red]")
        raise typer.Exit(1)
    
    # Load configuration
    config = load_config()
    
    # Check if API key is configured
    api_key_field = f"{tracker}_api_key"
    if not config.get(api_key_field):
        console.print(f"[red]✗ {tracker.upper()} API key not configured[/red]")
        console.print(f"[dim]Run 'python run.py config' to set up API credentials[/dim]")
        raise typer.Exit(1)
    
    # Show dry run warning
    if dry_run:
        console.print("[yellow]🔍 DRY RUN MODE - No actual upload will be performed[/yellow]")
    elif not force:
        if not Confirm.ask(f"Perform actual upload to {tracker.upper()}?", default=False):
            console.print("[yellow]Upload cancelled by user[/yellow]")
            raise typer.Exit(0)
    
    # Check for existing torrents if requested
    if check_existing and tracker == "red":
        try:
            from feature_red_uploader import REDUploader
            uploader = REDUploader(config[api_key_field])
            
            # Extract basic metadata for search
            from feature_metadata_engine import process_album_metadata
            metadata = process_album_metadata(source_path)
            
            artist = metadata.get('artist', '')
            album = metadata.get('album', '')
            
            if artist and album:
                console.print(f"[cyan]Checking for existing torrents on {tracker.upper()}...[/cyan]")
                existing = uploader.search_existing_torrent(artist, album)
                
                if existing:
                    console.print(f"[yellow]⚠️ Found {len(existing)} existing torrent(s) for this album[/yellow]")
                    if not force and not Confirm.ask("Continue with upload anyway?", default=False):
                        console.print("[yellow]Upload cancelled - existing torrents found[/yellow]")
                        raise typer.Exit(0)
                else:
                    console.print("[green]✓ No existing torrents found[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not check for existing torrents: {e}[/yellow]")
    
    # Perform the upload workflow
    try:
        success = integrate_upload_workflow(source_path, tracker, config)
        
        if success:
            if dry_run:
                console.print("[green]✓ Dry run completed successfully[/green]")
                console.print("[dim]Add --no-dry-run to perform actual upload[/dim]")
            else:
                console.print("[green]🎉 Upload completed successfully![/green]")
        else:
            console.print("[red]✗ Upload workflow failed[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]✗ Upload error: {e}[/red]")
        if not dry_run:
            console.print("[dim]You may want to try --dry-run first to test the workflow[/dim]")
        raise typer.Exit(1)

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

def format_size(size_bytes: int) -> str:
    """Format bytes to human readable"""
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def main():
    """Main entry point"""
    # Run health check on first run if no config exists
    config_path = Path.home() / ".config" / "torrent_creator" / "config.json"
    if not config_path.exists():
        console.print("[yellow]No configuration found. Running setup...[/yellow]")
        setup_wizard()
        console.print("\n[cyan]Running initial health check...[/cyan]")
        config = load_config()
        run_quick_health_check(config)
    
    app()

if __name__ == "__main__":
    main()
