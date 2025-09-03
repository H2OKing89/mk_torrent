#!/usr/bin/env python3
"""
Upload workflow integration using the new tracker-agnostic architecture
"""

from pathlib import Path
from typing import Dict, Any
from rich.console import Console

from ..api.trackers import get_tracker_api
from ..core.metadata.engine import MetadataEngine

console = Console()


def upload_workflow(
    source_path: Path,
    tracker: str,
    config: Dict[str, Any],
    dry_run: bool = True,
    check_existing: bool = True,
) -> bool:
    """
    Main upload workflow using new refactored architecture

    Args:
        source_path: Path to source content
        tracker: Tracker name ('red', 'mam', etc.)
        config: Configuration dictionary
        dry_run: Whether to perform actual upload
        check_existing: Whether to check for existing torrents

    Returns:
        bool: Success status
    """
    console.print(
        f"\n[bold cyan]═══ Upload Workflow - {tracker.upper()} ═══[/bold cyan]\n"
    )

    try:
        # Get API key for tracker
        api_key_field = f"{tracker}_api_key"
        api_key = config.get(api_key_field)

        if not api_key:
            console.print(f"[red]✗ {tracker.upper()} API key not configured[/red]")
            console.print(
                "[dim]Use 'python run.py config' to set up API credentials[/dim]"
            )
            return False

        # Initialize tracker API
        console.print(f"[cyan]Initializing {tracker.upper()} API...[/cyan]")
        tracker_api = get_tracker_api(tracker, api_key=api_key)

        # Test connection
        console.print(f"[cyan]Testing {tracker.upper()} API connection...[/cyan]")
        if not tracker_api.test_connection():
            console.print(f"[red]✗ Failed to connect to {tracker.upper()} API[/red]")
            console.print("[dim]Check your API key and network connection[/dim]")
            return False

        console.print(f"[green]✓ Connected to {tracker.upper()}[/green]")

        # Extract metadata
        console.print(f"[cyan]Processing metadata for: {source_path.name}[/cyan]")
        metadata_engine = MetadataEngine()
        metadata = metadata_engine.process(source_path)

        console.print(
            f"[green]✓ Metadata extracted ({metadata.get('content_type', 'unknown')} detected)[/green]"
        )

        # Check for existing torrents if requested
        if check_existing:
            console.print(
                f"[cyan]Checking for existing torrents on {tracker.upper()}...[/cyan]"
            )

            # Extract search parameters from metadata
            search_params = {}
            if metadata.get("artist"):
                search_params["artist"] = metadata["artist"]
            if metadata.get("album"):
                search_params["album"] = metadata["album"]
            if metadata.get("title"):
                search_params["title"] = metadata["title"]

            if search_params:
                existing = tracker_api.search_existing(**search_params)
                if existing:
                    console.print(
                        f"[yellow]⚠ Found {len(existing)} potentially matching torrents[/yellow]"
                    )
                    for i, torrent in enumerate(existing[:3], 1):  # Show first 3
                        title = torrent.get(
                            "groupName", torrent.get("title", "Unknown")
                        )
                        console.print(f"[dim]  {i}. {title}[/dim]")

                    if not dry_run:
                        import typer

                        if not typer.confirm(
                            "Continue with upload despite existing torrents?"
                        ):
                            console.print("[yellow]Upload cancelled by user[/yellow]")
                            return False
                else:
                    console.print("[green]✓ No existing torrents found[/green]")

        # Validate metadata for this tracker
        console.print(f"[cyan]Validating metadata for {tracker.upper()}...[/cyan]")
        validation = tracker_api.validate_metadata(metadata)

        if not validation["valid"]:
            console.print("[red]✗ Metadata validation failed:[/red]")
            for error in validation["errors"]:
                console.print(f"[red]  • {error}[/red]")
            return False

        if validation.get("warnings"):
            for warning in validation["warnings"]:
                console.print(f"[yellow]⚠ {warning}[/yellow]")

        console.print(f"[green]✓ Metadata validated for {tracker.upper()}[/green]")

        # TODO: Create torrent file (integrate with torrent_creator.py)
        # For now, assume we have a torrent file
        torrent_path = source_path.parent / f"{source_path.name}.torrent"

        if dry_run:
            console.print(
                f"[yellow]DRY RUN: Would upload to {tracker.upper()}[/yellow]"
            )
            console.print(f"[dim]  Source: {source_path}[/dim]")
            console.print(f"[dim]  Torrent: {torrent_path}[/dim]")
            console.print(
                f"[dim]  Content: {metadata.get('content_type', 'unknown')}[/dim]"
            )
            return True
        else:
            # Actual upload
            console.print(f"[cyan]Uploading to {tracker.upper()}...[/cyan]")
            result = tracker_api.upload_torrent(torrent_path, metadata, dry_run=False)

            if result.get("success"):
                console.print(
                    f"[green]✓ Successfully uploaded to {tracker.upper()}![/green]"
                )
                if result.get("url"):
                    console.print(f"[dim]  URL: {result['url']}[/dim]")
                return True
            else:
                console.print(f"[red]✗ Upload to {tracker.upper()} failed[/red]")
                if result.get("error"):
                    console.print(f"[red]  Error: {result['error']}[/red]")
                return False

    except ImportError as e:
        console.print(f"[red]✗ Module import error: {e}[/red]")
        console.print("[dim]Make sure all required modules are available[/dim]")
        return False
    except Exception as e:
        console.print(f"[red]✗ Unexpected error: {e}[/red]")
        return False


def check_existing_torrents(
    tracker: str, metadata: Dict[str, Any], config: Dict[str, Any]
) -> list:
    """
    Check for existing torrents on a tracker

    Args:
        tracker: Tracker name
        metadata: Extracted metadata
        config: Configuration dictionary

    Returns:
        list: List of existing torrents
    """
    try:
        api_key = config.get(f"{tracker}_api_key")
        if not api_key:
            return []

        tracker_api = get_tracker_api(tracker, api_key=api_key)

        search_params = {}
        if metadata.get("artist"):
            search_params["artist"] = metadata["artist"]
        if metadata.get("album"):
            search_params["album"] = metadata["album"]
        if metadata.get("title"):
            search_params["title"] = metadata["title"]

        return tracker_api.search_existing(**search_params)
    except Exception:
        return []
