#!/usr/bin/env python3
"""
RED Upload CLI - Command line interface for uploading to RED
Uses the new metadata engine and upload specification system.

Usage: python red_upload_cli.py [audiobook_path] --api-key [key] [--dry-run]
"""

import sys
import os
import re
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

console = Console()


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Upload audiobooks to RED tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python red_upload_cli.py /path/to/audiobook --api-key YOUR_API_KEY --dry-run
  python red_upload_cli.py /path/to/audiobook --api-key YOUR_API_KEY --upload
        """,
    )

    parser.add_argument(
        "audiobook_path", type=Path, help="Path to the audiobook folder or M4B file"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        help="RED API key (can also be set via RED_API_KEY environment variable)",
    )

    # Use mutually exclusive group for upload mode
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Do not upload (default)")
    mode.add_argument("--upload", action="store_true", help="Actually upload to RED")

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    return parser.parse_args()


def get_api_key(args) -> Optional[str]:
    """Get API key from arguments or environment or prompt user"""
    api_key = args.api_key or os.environ.get("RED_API_KEY")

    if not api_key:
        console.print("[yellow]No API key provided.[/yellow]")
        console.print("You can:")
        console.print("1. Use --api-key parameter")
        console.print("2. Set RED_API_KEY environment variable")
        console.print("3. Enter it now (will not be stored)")

        if Confirm.ask("Enter API key now?"):
            api_key = Prompt.ask("RED API Key", password=True)
        else:
            console.print("[red]API key required for upload.[/red]")
            return None

    return api_key


def find_audiobook_files(audiobook_path: Path) -> Dict[str, Any]:
    """Find and validate audiobook files"""
    result = {}

    # Determine if path is file or directory
    if audiobook_path.is_file() and audiobook_path.suffix.lower() == ".m4b":
        m4b_file = audiobook_path
        folder_path = audiobook_path.parent
    elif audiobook_path.is_dir():
        m4b_files = list(audiobook_path.glob("*.m4b"))
        if not m4b_files:
            console.print("[red]❌ No M4B file found in directory[/red]")
            return None
        elif len(m4b_files) == 1:
            m4b_file = m4b_files[0]
        else:
            # Multiple M4B files - choose the largest one
            m4b_file = max(m4b_files, key=lambda f: f.stat().st_size)
            console.print(
                f"[yellow]⚠️  Multiple M4B files found, using largest: {m4b_file.name}[/yellow]"
            )
        folder_path = audiobook_path
    else:
        console.print("[red]❌ Invalid audiobook path[/red]")
        return None

    # Find additional files
    cover_files = list(folder_path.glob("*.jpg")) + list(folder_path.glob("*.png"))

    result = {
        "folder_path": folder_path,
        "m4b_file": m4b_file,
        "cover_file": cover_files[0] if cover_files else None,
        "folder_name": folder_path.name,
        "folder_length": len(folder_path.name),
    }

    console.print(f"✅ Found M4B: {m4b_file.name}")
    if result["cover_file"]:
        console.print(f"✅ Found cover: {result['cover_file'].name}")

    return result


def extract_audiobook_metadata(audiobook_files: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from audiobook using the new metadata engine"""
    from mk_torrent.core.metadata.engine import MetadataEngine

    console.print("[cyan]📚 Extracting metadata...[/cyan]")

    try:
        # Initialize metadata engine
        engine = MetadataEngine()
        engine.setup_default_processors()

        # Extract metadata
        metadata = engine.extract_metadata(
            audiobook_files["m4b_file"], content_type="audiobook"
        )

        # Enhance metadata with path information
        enhanced_metadata = {
            **metadata,
            "path": audiobook_files["folder_path"],
            "folder_name": audiobook_files["folder_name"],
            "format": "M4B",
            "encoding": metadata.get("bitrate", "Unknown"),
            "media": "WEB",
            "type": "audiobook",
        }

        # For audiobooks: map author to artists if needed
        if (
            not enhanced_metadata.get("artists")
            or enhanced_metadata.get("artists") == "Unknown"
        ):
            if enhanced_metadata.get("author"):
                enhanced_metadata["artists"] = enhanced_metadata["author"]
                console.print(
                    f"[blue]ℹ️  Mapped author to artists: {enhanced_metadata['author']}[/blue]"
                )
            else:
                # Try to extract from folder name like the integration test does
                folder_name = audiobook_files["folder_name"]
                # Try to extract author from folder name patterns like "(Author)" or "[Author]"
                author_match = re.search(r"\(([^)]+)\)", folder_name)
                if author_match:
                    enhanced_metadata["artists"] = author_match.group(1)
                    enhanced_metadata["author"] = author_match.group(1)
                    console.print(
                        f"[blue]ℹ️  Extracted author from folder: {author_match.group(1)}[/blue]"
                    )
                else:
                    console.print(
                        "[yellow]⚠️  Could not extract author from folder name[/yellow]"
                    )

        # Display extracted metadata
        table = Table(title="Extracted Metadata")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        important_fields = [
            "title",
            "artists",
            "author",
            "year",
            "narrator",
            "publisher",
            "genre",
            "duration",
            "bitrate",
        ]

        for field in important_fields:
            value = enhanced_metadata.get(field, "Unknown")
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            table.add_row(field.title(), str(value))

        console.print(table)

        return enhanced_metadata

    except Exception as e:
        console.print(f"[red]❌ Metadata extraction failed: {e}[/red]")
        return None


def validate_with_red(
    metadata: Dict[str, Any], api_key: str
) -> tuple[bool, Optional[Any]]:
    """Validate metadata with RED requirements"""
    from mk_torrent.trackers.red_adapter import REDAdapter, REDConfig

    console.print("[cyan]🎯 Validating with RED requirements...[/cyan]")

    try:
        # Initialize RED API
        red_api = REDAdapter(REDConfig(api_key=api_key))

        # Validate metadata
        validation = red_api.validate_metadata(metadata)

        if validation["valid"]:
            console.print("[green]✅ Metadata validation PASSED[/green]")
        else:
            console.print("[red]❌ Metadata validation FAILED[/red]")
            for error in validation["errors"]:
                console.print(f"  • [red]{error}[/red]")

        if validation["warnings"]:
            console.print("[yellow]⚠️  Warnings:[/yellow]")
            for warning in validation["warnings"]:
                console.print(f"  • [yellow]{warning}[/yellow]")

        # Check path compliance
        folder_name = metadata.get("folder_name", "")
        if folder_name:
            is_compliant = red_api.check_path_compliance(folder_name)
            max_length = red_api.config.max_path_length
            console.print(
                f"📏 Path compliance: {'✅ PASS' if is_compliant else '❌ FAIL'} "
                f"({len(folder_name)}/{max_length} chars)"
            )

        return validation["valid"], red_api

    except Exception as e:
        console.print(f"[red]❌ RED validation failed: {e}[/red]")
        return False, None


def find_torrent_file(metadata: Dict[str, Any]) -> Optional[Path]:
    """Find existing torrent file for the audiobook"""
    console.print("[cyan]📦 Looking for torrent file...[/cyan]")

    try:
        # Get source path
        source_path = metadata["path"]

        # Look for torrent file in common locations
        potential_paths = [
            # Same directory as the audiobook folder
            source_path.parent / f"{source_path.name}.torrent",
            # Inside the audiobook folder
            source_path / f"{source_path.name}.torrent",
            # Common torrent directory patterns
            source_path.parent.parent / "torrents" / f"{source_path.name}.torrent",
        ]

        for torrent_path in potential_paths:
            if torrent_path.exists():
                console.print(f"✅ Found torrent: {torrent_path.name}")
                return torrent_path

        # If no torrent found, create a dummy one for testing
        console.print(
            "[yellow]⚠️  No torrent file found - creating dummy for testing[/yellow]"
        )
        dummy_torrent = source_path.parent / f"{source_path.name}.torrent"

        # Create a minimal dummy torrent file for testing purposes
        dummy_content = b"d8:announce23:https://example.com/announce13:creation datei1694000000e4:infod4:name"
        dummy_content += (
            str(len(source_path.name)).encode() + b":" + source_path.name.encode()
        )
        dummy_content += b"12:piece lengthi32768e6:pieces0:ee"

        with open(dummy_torrent, "wb") as f:
            f.write(dummy_content)

        console.print(f"✅ Created dummy torrent: {dummy_torrent.name}")
        console.print(
            "[blue]ℹ️  In production, use the torrent creation workflow first[/blue]"
        )

        return dummy_torrent

    except Exception as e:
        console.print(f"[red]❌ Could not find or create torrent file: {e}[/red]")
        return None


def perform_upload(
    red_api: Any,
    torrent_path: Path,
    metadata: Dict[str, Any],
    dry_run: bool = True,
) -> bool:
    """Perform the upload to RED"""
    action = "dry run" if dry_run else "upload"
    console.print(f"[cyan]🚀 Performing RED {action}...[/cyan]")

    try:
        result = red_api.upload_torrent(torrent_path, metadata, dry_run=dry_run)

        if result["success"]:
            if dry_run:
                console.print("[green]✅ Dry run completed successfully[/green]")
                console.print("   Ready for actual upload!")

                # Show form data preview if available
                if "form_data" in result:
                    console.print("\n[cyan]Form data that would be sent:[/cyan]")
                    for key, value in list(result["form_data"].items())[:10]:
                        if not key.startswith("_"):
                            console.print(f"  {key}: {value}")

            else:
                console.print("[green]✅ Upload successful![/green]")
                if result.get("torrent_id"):
                    console.print(f"   Torrent ID: {result['torrent_id']}")
                if result.get("url"):
                    console.print(f"   URL: {result['url']}")
        else:
            console.print(f"[red]❌ {action.title()} failed[/red]")
            if result.get("error"):
                console.print(f"   Error: {result['error']}")

        return result["success"]

    except Exception as e:
        console.print(f"[red]❌ {action.title()} error: {e}[/red]")
        return False


def main():
    """Main CLI function"""
    args = parse_arguments()

    console.print(
        Panel.fit(
            "[bold cyan]🎵 RED Upload CLI[/bold cyan]\n"
            "Test RED integration with audiobook metadata\n"
            "Assumes torrent file already exists from workflow",
            border_style="cyan",
        )
    )

    # Validate audiobook path
    if not args.audiobook_path.exists():
        console.print(f"[red]❌ Path not found: {args.audiobook_path}[/red]")
        return 1

    # Get API key
    api_key = get_api_key(args)
    if not api_key:
        return 1

    # Determine upload mode
    is_dry_run = not args.upload  # Default to dry run

    if not is_dry_run:
        console.print(
            "[bold yellow]⚠️  REAL UPLOAD MODE - This will actually upload to RED![/bold yellow]"
        )
        if not Confirm.ask("Are you sure you want to proceed?"):
            console.print("Upload cancelled.")
            return 0
    else:
        console.print(
            "[blue]🔍 DRY RUN MODE - No actual upload will be performed[/blue]"
        )

    # Step 1: Find audiobook files
    audiobook_files = find_audiobook_files(args.audiobook_path)
    if not audiobook_files:
        return 1

    # Step 2: Extract metadata
    metadata = extract_audiobook_metadata(audiobook_files)
    if not metadata:
        return 1

    # Add verbose flag to metadata for debugging
    if args.verbose:
        metadata["verbose"] = True

    # Step 3: Validate with RED
    is_valid, red_api = validate_with_red(metadata, api_key)
    if not is_valid or not red_api:
        console.print("[red]❌ Validation failed. Cannot proceed.[/red]")
        return 1

    # Step 4: Test API connection (only for real uploads)
    if not is_dry_run:
        if not red_api.test_connection():
            console.print("[red]❌ API connection failed. Cannot upload.[/red]")
            return 1

    # Step 5: Find torrent file
    torrent_path = find_torrent_file(metadata)
    if not torrent_path:
        console.print("[red]❌ No torrent file available. Cannot proceed.[/red]")
        console.print("[blue]ℹ️  Run the torrent creation workflow first[/blue]")
        return 1

    # Step 6: Perform upload or dry run
    success = perform_upload(red_api, torrent_path, metadata, dry_run=is_dry_run)

    if success:
        if is_dry_run:
            console.print(
                "\n[bold green]🎉 RED integration test successful![/bold green]"
            )
            console.print(
                "\n[cyan]RED module ready for production workflow integration[/cyan]"
            )
        else:
            console.print("\n[bold green]🎉 Upload successful![/bold green]")
        return 0
    else:
        console.print(
            f"\n[red]❌ RED integration {('upload' if not is_dry_run else 'test')} failed.[/red]"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
