#!/usr/bin/env python3
"""
Upload workflow integration using the new tracker-agnostic architecture
"""

from pathlib import Path
from typing import Any
from rich.console import Console

from ..core.metadata.engine import MetadataEngine

console = Console()


def get_tracker_api(tracker: str, api_key: str):
    """Get tracker API instance for the specified tracker"""
    if tracker.lower() == "red":
        from ..trackers.red_adapter import REDAdapter, REDConfig

        return REDAdapter(REDConfig(api_key=api_key))
    else:
        raise ValueError(f"Unsupported tracker: {tracker}")


def _validate_with_red_api(enhanced_metadata: dict, api_key: str) -> bool:
    """Validate metadata using RED API directly (same pattern as CLI script)"""
    from ..trackers.red_adapter import REDAdapter, REDConfig

    try:
        # Initialize RED API
        red_api = REDAdapter(REDConfig(api_key=api_key))

        # Prepare metadata in the format expected by CLI validation
        metadata_for_validation = {
            **enhanced_metadata["raw"],
            "path": enhanced_metadata.get("source_path", ""),
            "folder_name": enhanced_metadata.get("folder_name", ""),
            "format": "M4B",
            "encoding": enhanced_metadata["raw"].get("bitrate", "Unknown"),
            "media": "WEB",
            "type": "audiobook",
        }

        # Map author to artists if needed
        if (
            not metadata_for_validation.get("artists")
            or metadata_for_validation.get("artists") == "Unknown"
        ):
            if metadata_for_validation.get("author"):
                metadata_for_validation["artists"] = metadata_for_validation["author"]

        # Debug: Show what we're validating
        console.print("\n[bold cyan]🔍 DEBUG: Validation Input Data[/bold cyan]")
        console.print("[yellow]═══════════════════════════════════════[/yellow]")

        from rich.table import Table

        validation_table = Table(title="Metadata Being Validated")
        validation_table.add_column("Field", style="cyan")
        validation_table.add_column("Value", style="white")

        for key, value in metadata_for_validation.items():
            if key != "path":  # Skip path for brevity
                validation_table.add_row(key, str(value))

        console.print(validation_table)
        console.print("[yellow]═══════════════════════════════════════[/yellow]\n")

        # Validate metadata
        validation = red_api.validate_metadata(metadata_for_validation)

        if validation["valid"]:
            console.print("[green]✅ Metadata validation PASSED[/green]")
            return True
        else:
            console.print("[red]❌ Metadata validation FAILED[/red]")
            for error in validation["errors"]:
                console.print(f"  • [red]{error}[/red]")
            return False

    except Exception as e:
        console.print(f"[red]❌ RED validation failed: {e}[/red]")
        return False


def upload_workflow(
    source_path: Path,
    tracker: str,
    config: dict[str, Any],
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

        # Find the actual audiobook file if source_path is a directory
        audiobook_file = source_path
        if source_path.is_dir():
            # Look for M4B or MP3 files in the directory
            audiobook_files = list(source_path.glob("*.m4b")) + list(
                source_path.glob("*.mp3")
            )
            if not audiobook_files:
                console.print(
                    "[red]✗ No audiobook files (.m4b or .mp3) found in directory[/red]"
                )
                return False
            audiobook_file = audiobook_files[0]  # Use first found file
            console.print(f"[dim]Found audiobook file: {audiobook_file.name}[/dim]")

        # Initialize metadata engine (same pattern as test_red_upload.py)
        metadata_engine = MetadataEngine()
        from ..core.metadata.processors.audiobook import AudiobookProcessor

        audiobook_processor = AudiobookProcessor()
        metadata_engine.register_processor("audiobook", audiobook_processor)
        metadata_engine.set_default_processor("audiobook")

        # Extract raw metadata from the actual file
        metadata_dict = metadata_engine.extract_metadata(audiobook_file)

        # Convert to AudiobookMeta (same pattern as test_red_upload.py)
        from ..core.metadata.base import AudiobookMeta

        audiobookmeta_fields = {
            field.name for field in AudiobookMeta.__dataclass_fields__.values()
        }
        filtered_metadata = {
            k: v for k, v in metadata_dict.items() if k in audiobookmeta_fields
        }

        # Convert year to int if it's a string
        if "year" in filtered_metadata and isinstance(filtered_metadata["year"], str):
            try:
                filtered_metadata["year"] = int(filtered_metadata["year"])
            except (ValueError, TypeError):
                filtered_metadata["year"] = None

        audiobook_meta = AudiobookMeta(**filtered_metadata)

        # Map to tracker format using RED mapper
        from ..core.metadata.mappers.red import REDMapper

        red_mapper = REDMapper()
        tracker_data = red_mapper.map_to_red_upload(
            audiobook_meta, include_description=True
        )

        # Store both raw metadata and tracker data
        metadata = {
            "raw": metadata_dict,
            "audiobook_meta": audiobook_meta,
            "tracker_data": tracker_data,
            "content_type": "audiobook",
            "source_file": audiobook_file,
        }

        console.print(
            f"[green]✓ Metadata extracted: {audiobook_meta.title} by {audiobook_meta.author}[/green]"
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

        # Skip validation for now - will fix this separately
        console.print("[cyan]Validating with RED requirements...[/cyan]")

        # Prepare enhanced metadata for validation
        enhanced_metadata = {
            "raw": metadata["raw"],
            "source_path": source_path,
            "folder_name": source_path.name,
        }

        validation_result = _validate_with_red_api(enhanced_metadata, api_key)
        if not validation_result:
            console.print("[red]❌ Metadata validation failed[/red]")
            return False

        console.print("[green]✓ Proceeding with upload preparation[/green]")

        # Check path compliance before creating torrent
        console.print(f"[cyan]Checking path compliance for {tracker.upper()}...[/cyan]")
        compliance_result = check_path_compliance(source_path, tracker)

        if not compliance_result["compliant"]:
            console.print("[red]✗ Path compliance check failed:[/red]")
            for issue in compliance_result["issues"]:
                console.print(f"[red]  • {issue}[/red]")

            if compliance_result.get("fixable", False):
                console.print("[yellow]⚠ Path can be auto-fixed[/yellow]")
                if not dry_run:
                    from rich.prompt import Confirm

                    if Confirm.ask("Auto-fix path compliance issues?", default=True):
                        fixed_path = fix_path_compliance(
                            source_path, tracker, dry_run=False
                        )
                        if fixed_path:
                            source_path = fixed_path
                            console.print(
                                f"[green]✓ Path compliance fixed: {source_path.name}[/green]"
                            )
                        else:
                            console.print("[red]✗ Failed to fix path compliance[/red]")
                            return False
                    else:
                        console.print(
                            "[yellow]Upload cancelled - path compliance required[/yellow]"
                        )
                        return False
            else:
                console.print("[red]✗ Path issues cannot be auto-fixed[/red]")
                return False
        else:
            console.print(
                f"[green]✓ Path compliant with {tracker.upper()} requirements[/green]"
            )

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

            # Show what would be uploaded to RED (for debugging)
            if tracker.lower() == "red":
                console.print(
                    "\n[bold cyan]🔍 DEBUG: Preparing RED Upload Payload[/bold cyan]"
                )
                # Use the raw metadata for upload data preparation
                tracker_api.prepare_upload_data(metadata["raw"], torrent_path)

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
    tracker: str, metadata: dict[str, Any], config: dict[str, Any]
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


def check_path_compliance(source_path: Path, tracker: str) -> dict[str, Any]:
    """
    Check if path complies with tracker requirements

    Args:
        source_path: Path to check
        tracker: Tracker name (red, mam, etc.)

    Returns:
        dict: Compliance status and details
    """
    try:
        # Import path compliance functions from your script
        import sys
        from pathlib import Path as PathObj

        # Add the scripts directory to path to import from your compliance script
        scripts_dir = PathObj(__file__).parent.parent.parent.parent / "scripts" / "cli"
        sys.path.insert(0, str(scripts_dir))

        from path_compliance import (
            has_audio_files,
            find_all_files,
            analyze_path_compliance,
            detect_tracker_intent,
        )

        # Check if it's an audiobook directory
        if not has_audio_files(source_path):
            return {
                "compliant": False,
                "issues": ["Directory does not contain audio files"],
                "fixable": False,
            }

        # Get files for analysis
        files = find_all_files(source_path)
        if not files:
            return {
                "compliant": False,
                "issues": ["No files found in directory"],
                "fixable": False,
            }

        # Set limits based on tracker
        max_length = 180 if tracker.lower() == "red" else 255

        # Analyze compliance
        analysis = analyze_path_compliance(source_path, files, max_length)

        if analysis["compliant"]:
            return {"compliant": True, "issues": [], "fixable": True}

        # Check tracker intent for safety
        tracker_intent = detect_tracker_intent(source_path)
        safe_for_target = (
            not tracker_intent["detected_trackers"]
            or tracker.lower() in tracker_intent["detected_trackers"]
            or tracker_intent["safe_for_red"]
        )

        issues = []
        for violation in analysis["violations"]:
            issues.append(
                f"Path too long: {violation['filename']} "
                f"({violation['length']} > {max_length} chars, +{violation['overage']})"
            )

        return {
            "compliant": False,
            "issues": issues,
            "fixable": True,
            "safe_for_target": safe_for_target,
            "max_overage": analysis["max_overage"],
            "violation_count": analysis["violation_count"],
        }

    except Exception as e:
        console.print(f"[yellow]⚠ Compliance check error: {e}[/yellow]")
        return {
            "compliant": True,  # Assume compliant if check fails
            "issues": [],
            "fixable": False,
        }


def fix_path_compliance(
    source_path: Path, tracker: str, dry_run: bool = True
) -> Path | None:
    """
    Fix path compliance issues using your PathFixer

    Args:
        source_path: Path to fix
        tracker: Tracker name
        dry_run: Whether to actually apply changes

    Returns:
        Path: New path if successful, None if failed
    """
    try:
        # Import path compliance functions
        import sys
        from pathlib import Path as PathObj

        scripts_dir = PathObj(__file__).parent.parent.parent.parent / "scripts" / "cli"
        sys.path.insert(0, str(scripts_dir))

        from path_compliance import find_all_files
        from mk_torrent.core.compliance.path_fixer import PathFixer, ComplianceConfig

        # Get files
        files = find_all_files(source_path)
        if not files:
            return None

        # Set up configuration
        max_length = 180 if tracker.lower() == "red" else 255
        config = ComplianceConfig(
            max_full_path=max_length, dry_run=dry_run, apply=not dry_run
        )

        # Create fixer and apply changes
        fixer = PathFixer(tracker=tracker.lower(), config=config)

        new_folder, new_files, log_entries = fixer.fix_path(
            str(source_path), files, apply_changes=not dry_run
        )

        # Return new path
        new_path = source_path.parent / new_folder
        return new_path if new_path != source_path else source_path

    except Exception as e:
        console.print(f"[red]✗ Path fix error: {e}[/red]")
        return None
