#!/usr/bin/env python3
"""
RED Upload CLI - Simple command line interface for uploading to RED
Usage: python red_upload_cli.py [audiobook_path] --api-key [key] [--dry-run]
"""

import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

# Add project root to path
project_root = Path(__file__).parent.parent.parent  # Go up to project root
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


def get_api_key(args):
    """Get API key from arguments or environment or prompt user"""
    import os

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


def extract_audiobook_metadata(audiobook_path):
    """Extract metadata from audiobook"""
    console.print(f"[cyan]📚 Analyzing audiobook: {audiobook_path.name}[/cyan]")

    try:
        from mk_torrent.core.metadata.engine import MetadataEngine
        from mutagen.mp4 import MP4

        # Find M4B file
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
                # Multiple M4B files - choose the largest one (main audiobook)
                m4b_file = max(m4b_files, key=lambda f: f.stat().st_size)
                console.print(
                    f"[yellow]⚠️  Multiple M4B files found, using largest: {m4b_file.name}[/yellow]"
                )
            folder_path = audiobook_path
        else:
            console.print("[red]❌ Invalid audiobook path[/red]")
            return None

        console.print(f"✅ Found M4B: {m4b_file.name}")

        # Extract metadata using our engine
        engine = MetadataEngine()
        metadata = engine.process(m4b_file, content_type="audiobook")

        # Also extract from Mutagen for additional fields
        audio = MP4(str(m4b_file))

        # Parse folder name for additional info
        folder_name = folder_path.name

        # Enhanced metadata combining multiple sources
        enhanced_metadata = {
            **metadata,
            "path": folder_path,
            "m4b_file": m4b_file,
            "folder_name": folder_name,
            "type": "audiobook",
            "format": "M4B",
            "encoding": "AAC",
            "media": "WEB",
        }

        # Try to extract narrator from M4B tags
        if audio.tags:
            # Try multiple possible narrator tag fields
            narrator_fields = ["©wrt", "NARRATOR", "narrator", "©cmt"]
            for field in narrator_fields:
                if field in audio.tags:
                    enhanced_metadata["narrator"] = audio.tags[field][0]
                    break

            # Extract other metadata
            if "cprt" in audio.tags:
                enhanced_metadata["publisher"] = audio.tags["cprt"][0]
            if "©gen" in audio.tags:
                enhanced_metadata["genre"] = audio.tags["©gen"][0]

        # If no narrator found in tags, try to extract from folder name
        if "narrator" not in enhanced_metadata:
            folder_name = folder_path.name.lower()
            # Look for common narrator patterns in folder name
            import re

            narrator_patterns = [
                r"narr?ated?\s+by\s+([^-\[\(]+)",
                r"read\s+by\s+([^-\[\(]+)",
                r"-\s*([^-\[\(]+)\s*$",  # Last part after dash
            ]
            for pattern in narrator_patterns:
                match = re.search(pattern, folder_name, re.IGNORECASE)
                if match:
                    narrator = match.group(1).strip().title()
                    if len(narrator) > 2:  # Reasonable narrator name
                        enhanced_metadata["narrator"] = narrator
                        console.print(
                            f"[blue]ℹ️  Extracted narrator from folder name: {narrator}[/blue]"
                        )
                        break

        # Display extracted metadata
        table = Table(title="Extracted Metadata")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        important_fields = [
            "title",
            "artists",
            "year",
            "narrator",
            "publisher",
            "genre",
            "duration",
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


def validate_with_red(metadata, api_key):
    """Validate metadata with RED requirements"""
    console.print("[cyan]🎯 Validating with RED requirements...[/cyan]")

    try:
        from mk_torrent.api.trackers.red import RedactedAPI

        red_api = RedactedAPI(api_key=api_key)

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
        folder_path = metadata.get("path")
        if folder_path:
            folder_name = Path(folder_path).name
            is_compliant = red_api.check_path_compliance(
                folder_name
            )  # Check folder name, not full path
            console.print(
                f"📏 Path compliance: {'✅ PASS' if is_compliant else '❌ FAIL'}"
            )
            console.print(
                f"   Folder name: {len(folder_name)}/{red_api.config.max_path_length} chars"
            )
            console.print(
                f"   Full path: {len(str(folder_path))} chars (not validated by RED)"
            )

        return validation["valid"], red_api

    except Exception as e:
        console.print(f"[red]❌ RED validation failed: {e}[/red]")
        return False, None


def test_api_connection(red_api):
    """Test connection to RED API"""
    console.print("[cyan]🔌 Testing RED API connection...[/cyan]")

    try:
        if red_api.test_connection():
            console.print("[green]✅ RED API connection successful[/green]")
            return True
        else:
            console.print("[red]❌ RED API connection failed[/red]")
            return False
    except Exception as e:
        console.print(f"[red]❌ API connection error: {e}[/red]")
        return False


def create_torrent(metadata):
    """Create torrent file"""
    console.print("[cyan]📦 Creating torrent file...[/cyan]")

    try:
        from mk_torrent.core.torrent_creator import TorrentCreator

        # Get source path
        source_path = metadata["path"]

        # Create output path
        output_path = source_path.parent / f"{source_path.name}.torrent"

        console.print(f"📂 Source: {source_path.name}")
        console.print(f"📁 Output: {output_path.name}")

        # Initialize torrent creator
        creator = TorrentCreator()

        # Create torrent with RED announce URL
        torrent_data = creator.create_torrent(
            source_path=source_path,
            announce_url="https://flacsfor.me/announce.php",  # RED announce URL
            private=True,
            comment="Created with mk_torrent for RED",
        )

        # Write torrent file
        with open(output_path, "wb") as f:
            f.write(torrent_data)

        console.print("✅ Torrent created successfully")
        return output_path

    except Exception as e:
        console.print(f"[red]❌ Torrent creation failed: {e}[/red]")
        return None


def upload_to_red(red_api, torrent_path, metadata, dry_run=True):
    """Upload to RED"""
    action = "dry run" if dry_run else "upload"
    console.print(f"[cyan]🚀 Performing RED {action}...[/cyan]")

    try:
        result = red_api.upload_torrent(torrent_path, metadata, dry_run=dry_run)

        if result["success"]:
            if dry_run:
                console.print("[green]✅ Dry run completed successfully[/green]")
                console.print("   Ready for actual upload!")
            else:
                console.print("[green]✅ Upload successful![/green]")
                if result.get("torrent_id"):
                    console.print(f"   Torrent ID: {result['torrent_id']}")
                if result.get("url"):
                    console.print(f"   URL: {result['url']}")
        else:
            console.print(f"[red]❌ {action.title()} failed[/red]")

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
            "Upload audiobooks to RED tracker",
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

    # Determine if this is a real upload or dry run
    is_dry_run = args.dry_run
    is_upload = not is_dry_run

    if is_upload:
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

    # Step 1: Extract metadata
    metadata = extract_audiobook_metadata(args.audiobook_path)
    if not metadata:
        return 1

    # Step 2: Validate with RED
    is_valid, red_api = validate_with_red(metadata, api_key)
    if not is_valid or not red_api:
        console.print("[red]❌ Validation failed. Cannot proceed.[/red]")
        return 1

    # Step 3: Test API connection (only for real uploads)
    if is_upload:
        if not test_api_connection(red_api):
            console.print("[red]❌ API connection failed. Cannot upload.[/red]")
            return 1

    # Step 4: Create torrent
    torrent_path = create_torrent(metadata)
    if not torrent_path:
        return 1

    # Step 5: Upload or dry run
    success = upload_to_red(red_api, torrent_path, metadata, dry_run=is_dry_run)

    if success:
        if is_dry_run:
            console.print(
                "\n[bold green]🎉 Dry run successful! Ready for real upload.[/bold green]"
            )
            console.print(
                "\n[cyan]To perform actual upload, run without --dry-run flag[/cyan]"
            )
        else:
            console.print("\n[bold green]🎉 Upload successful![/bold green]")
        return 0
    else:
        console.print(
            f"\n[red]❌ {('Upload' if is_upload else 'Dry run')} failed.[/red]"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
