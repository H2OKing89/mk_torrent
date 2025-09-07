#!/usr/bin/env python3
"""
RED Upload Test Script - Dry Run and Real Upload Support

This script supports both DRY RUN mode (preview) and REAL UPLOAD mode.
    console.print()
    console.print("✅ [bold green]Form data preview temporarily disabled - all other functionality working![/bold green]")

def main():
    # Form data preview
    console.print(Panel("📊 RED Form Data (What Gets Sent to API)", style="bold magenta"))
    form_adapter = REDFormAdapter()
    form_data = form_adapter.convert_to_form_data(upload_spec)

    # Display as JSON for readability
    form_json = json.dumps(form_data, indent=2, default=str)
    console.print(Syntax(form_json, "json", word_wrap=True))data preview
    console.print(Panel("📊 RED Form Data (What Gets Sent to API)", style="bold magenta"))
    form_adapter = REDFormAdapter()
    form_data = form_adapter.convert_to_form_data(upload_spec)data preview
    console.print(Panel("📊 RED Form Data (What Gets Sent to API)", style="bold magenta"))
    form_adapter = REDFormAdapter()
    form_data = form_adapter.convert_to_form_data(upload_spec)

    # Display as JSON for readability
    form_json = json.dumps(form_data, indent=2, default=str)
    console.print(Syntax(form_json, "json", word_wrap=True))and REAL UPLOAD mode.

DRY RUN MODE:
- Shows exactly what would be uploaded
- Displays full form data and description
- Safe for testing and verification
- No actual upload to RED

REAL UPLOAD MODE:
- ⚠️  WARNING: PERFORMS ACTUAL UPLOAD TO RED TRACKER ⚠️
- Creates real torrent on RED
- Only run if you're certain about the upload

Usage:
- Default: DRY RUN mode (safe)
- Add --real flag for actual upload
"""

import sys
import os
import argparse
import json
from pathlib import Path

# Add src to path
sys.path.append("src")

from mk_torrent.core.metadata.engine import MetadataEngine
from mk_torrent.core.metadata.processors.audiobook import AudiobookProcessor
from mk_torrent.core.metadata.mappers.red import REDMapper
from mk_torrent.core.metadata.base import AudiobookMeta
from mk_torrent.trackers.red.api_client import REDAPIClient
from mk_torrent.trackers.red.upload_spec import REDUploadSpec, REDFormAdapter
from mk_torrent.trackers.red.upload_spec import (
    AudioFormat,
    AudioBitrate,
    ReleaseType,
    Artist,
    ArtistType,
)

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.syntax import Syntax


# Load environment variables from .env file
def load_env_file(env_path: Path) -> dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


# Available test files
AVAILABLE_FILES = {
    "realist": {
        "name": "How a Realist Hero Rebuilt the Kingdom - vol_03",
        "audiobook_path": "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]",
        "torrent_file": "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing].torrent",
    },
    "evil_lord": {
        "name": "Im the Evil Lord of an Intergalactic Empire - vol_03",
        "audiobook_path": "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_09 (2023) (Dojyomaru) {ASIN.B0CPML76KX} [H2OKing]",
        "torrent_file": "How a Realist Hero Rebuilt the Kingdom - vol_09 (2023) (Dojyomaru) {ASIN.B0CPML76KX} [H2OKing].torrent",
    },
}

# Default to "evil_lord" since we have both audiobook and torrent files available
DEFAULT_FILE = "evil_lord"

# Load .env file
env_file = Path("tests/.env")
env_vars = load_env_file(env_file)


def display_upload_preview(
    console: Console,
    upload_spec: REDUploadSpec,
    red_fields: dict,
    metadata: AudiobookMeta,
    torrent_path: Path,
):
    """Display a comprehensive preview of what would be uploaded."""

    console.print(
        Panel("📋 UPLOAD PREVIEW - What Would Be Uploaded", style="bold blue")
    )

    # Basic info table
    info_table = Table(title="🔍 Upload Information")
    info_table.add_column("Field", style="cyan")
    info_table.add_column("Value", style="white")

    info_table.add_row("Title", upload_spec.title)
    info_table.add_row(
        "Artist", upload_spec.artists[0].name if upload_spec.artists else "Unknown"
    )
    info_table.add_row("Year", str(upload_spec.year))
    info_table.add_row("Category", upload_spec.category)
    info_table.add_row("Format", upload_spec.format.value)
    info_table.add_row(
        "Bitrate", upload_spec.other_bitrate or str(upload_spec.bitrate.value)
    )
    info_table.add_row("Release Type", upload_spec.release_type.value)
    info_table.add_row("Media", upload_spec.media.value)
    info_table.add_row(
        "Tags", ", ".join(upload_spec.tags) if upload_spec.tags else "None"
    )
    info_table.add_row("Torrent File", torrent_path.name if torrent_path else "None")

    console.print(info_table)
    console.print()

    # Technical metadata table
    tech_table = Table(title="🎵 Technical Metadata (From Real File Analysis)")
    tech_table.add_column("Property", style="cyan")
    tech_table.add_column("Value", style="white")

    tech_table.add_row(
        "Duration",
        f"{metadata.duration_sec:.1f} seconds" if metadata.duration_sec else "Unknown",
    )
    tech_table.add_row(
        "Bitrate", f"{metadata.bitrate} bps" if metadata.bitrate else "Unknown"
    )
    tech_table.add_row("Bitrate Mode", metadata.bitrate_mode or "Unknown")
    tech_table.add_row(
        "Sample Rate",
        f"{metadata.sample_rate} Hz" if metadata.sample_rate else "Unknown",
    )
    tech_table.add_row(
        "Channels", str(metadata.channels) if metadata.channels else "Unknown"
    )
    tech_table.add_row("Codec", metadata.codec or "Unknown")
    tech_table.add_row(
        "File Size",
        f"{metadata.file_size_mb:.1f} MB" if metadata.file_size_mb else "Unknown",
    )

    console.print(tech_table)
    console.print()

    # Description preview
    console.print(Panel("📝 Generated Description (BBCode)", style="bold green"))
    if upload_spec.description:
        # Show first 500 characters of description
        desc_preview = upload_spec.description[:500] + (
            "..." if len(upload_spec.description) > 500 else ""
        )
        console.print(Syntax(desc_preview, "bbcode", word_wrap=True))
        console.print(
            f"\n[dim]Total description length: {len(upload_spec.description)} characters[/dim]"
        )
    else:
        console.print("[yellow]No description generated[/yellow]")

    console.print()

    # Form data preview
    console.print(
        Panel("� RED Form Data (What Gets Sent to API)", style="bold magenta")
    )
    form_adapter = REDFormAdapter()
    form_data = form_adapter.to_form_data(upload_spec)

    # Display as JSON for readability
    form_json = json.dumps(form_data, indent=2, default=str)
    console.print(Syntax(form_json, "json", word_wrap=True))


def main():
    parser = argparse.ArgumentParser(description="RED Upload Test Script")
    parser.add_argument(
        "--real", action="store_true", help="Perform REAL upload (default: dry run)"
    )
    parser.add_argument(
        "--file",
        choices=list(AVAILABLE_FILES.keys()),
        default=DEFAULT_FILE,
        help=f"Test file to use (default: {DEFAULT_FILE})",
    )
    args = parser.parse_args()

    console = Console()

    # Display mode
    if args.real:
        console.print(Panel("🚨 REAL UPLOAD MODE 🚨", style="bold red"))
        console.print(
            "[bold red]⚠️  WARNING: This will perform a REAL upload to RED tracker![/bold red]"
        )
        console.print(
            "[bold red]⚠️  The torrent will be created and go live on the site![/bold red]"
        )
    else:
        console.print(Panel("🔍 DRY RUN MODE (Safe Preview)", style="bold green"))
        console.print(
            "[bold green]✅ This is a safe preview - no actual upload will occur[/bold green]"
        )
        console.print(
            "[bold green]✅ Add --real flag to perform actual upload[/bold green]"
        )

    console.print()

    # File selection
    file_config = AVAILABLE_FILES[args.file]
    console.print(f"📁 Using test file: [bold]{file_config['name']}[/bold]")

    # Safety confirmations for real uploads
    if args.real:
        if not Confirm.ask("Are you absolutely sure you want to do a REAL upload?"):
            console.print("❌ Upload cancelled for safety")
            return

        if not Confirm.ask(
            "Have you verified this audiobook doesn't already exist on RED?"
        ):
            console.print("❌ Please check for duplicates first")
            return

        if not Confirm.ask("Do you have the rights to upload this content?"):
            console.print("❌ Only upload content you have rights to distribute")
            return

    console.print(
        f"\n🚀 {'Proceeding with REAL upload...' if args.real else 'Generating preview...'}"
    )

    # Set up paths
    # Find the audiobook file
    audiobook_dir = Path(file_config["audiobook_path"])
    audiobook_files = []

    if audiobook_dir.exists():
        # Look for .m4b or .mp3 files
        audiobook_files = list(audiobook_dir.glob("*.m4b")) + list(
            audiobook_dir.glob("*.mp3")
        )

    if not audiobook_files:
        console.print(f"❌ No audiobook files found in: {audiobook_dir}")
        return

    audiobook_path = audiobook_files[0]  # Use first found file
    torrent_path = Path(
        f"/mnt/cache/scripts/mk_torrent/tests/samples/torrent_files/{file_config['torrent_file']}"
    )

    console.print(f"📖 Audiobook: {audiobook_path.name}")
    console.print(f"🧲 Torrent: {torrent_path.name}")

    # Check files exist
    if not audiobook_path.exists():
        console.print(f"❌ Audiobook file not found: {audiobook_path}")
        return

    if not torrent_path.exists():
        console.print(f"❌ Torrent file not found: {torrent_path}")
        return

    # Load .env file
    env_file = Path("tests/.env")
    env_vars = load_env_file(env_file)

    # Get API key (only needed for real uploads)
    api_key = None
    if args.real:
        api_key = env_vars.get("RED_API_KEY") or os.environ.get("RED_API_KEY")
        if not api_key:
            console.print(
                "❌ RED_API_KEY not found in tests/.env file or environment variables"
            )
            console.print("   Add it to tests/.env: RED_API_KEY=your_api_key_here")
            return

        console.print(
            f"✅ Found API key from {'tests/.env file' if env_vars.get('RED_API_KEY') else 'environment'}"
        )
    else:
        console.print("🔍 API key not required for dry run mode")

    try:
        # Step 1: Extract metadata
        console.print("\n📖 Extracting metadata...")
        engine = MetadataEngine()
        audiobook_processor = AudiobookProcessor()
        engine.register_processor("audiobook", audiobook_processor)
        engine.set_default_processor("audiobook")

        metadata_dict = engine.extract_metadata(audiobook_path)

        # Convert to AudiobookMeta
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

        metadata = AudiobookMeta(**filtered_metadata)
        console.print(f"✅ Extracted metadata: {metadata.title} by {metadata.author}")

        # Step 2: Map to RED format
        console.print("\n🔴 Mapping to RED format...")
        red_mapper = REDMapper()
        red_fields = red_mapper.map_to_red_upload(metadata)
        console.print(f"✅ Generated {len(red_fields)} RED fields")

        # Step 3: Create upload spec
        console.print("\n📋 Creating upload specification...")

        # Parse tags string into list
        tags_string = red_fields.get("tags", "audiobook")
        if isinstance(tags_string, str):
            tags_list = [tag.strip() for tag in tags_string.split(",")]
        else:
            tags_list = tags_string if isinstance(tags_string, list) else ["audiobook"]

        upload_spec = REDUploadSpec(
            title=red_fields.get("title", "Unknown Title"),
            artists=[
                Artist(
                    name=red_fields.get("artists[]", ["Unknown Artist"])[0]
                    if red_fields.get("artists[]")
                    else "Unknown Artist",
                    type=ArtistType.MAIN,
                )
            ],
            year=int(red_fields.get("year", 2023)),
            category="Audiobooks",
            format=AudioFormat.AAC,  # Based on our real file analysis
            bitrate=AudioBitrate.OTHER,  # Using "Other" with other_bitrate field
            other_bitrate=red_fields.get(
                "other_bitrate", "125k VBR"
            ),  # Real bitrate string
            release_type=ReleaseType.ALBUM,
            media="WEB",
            tags=tags_list,  # Now properly converted to list
            description=red_fields.get("album_desc", ""),
        )
        console.print(f"✅ Created upload spec for: {upload_spec.title}")

        # Step 4: Display preview (always show this)
        console.print()
        display_upload_preview(console, upload_spec, red_fields, metadata, torrent_path)

        if not args.real:
            # DRY RUN MODE - Just show preview and exit
            console.print()
            console.print(Panel("✅ DRY RUN COMPLETE", style="bold green"))
            console.print(
                "[bold green]This was a preview only - no upload was performed[/bold green]"
            )
            console.print(
                "[bold blue]To perform actual upload, run with --real flag[/bold blue]"
            )
            console.print(
                f"[dim]Command: python {sys.argv[0]} --file {args.file} --real[/dim]"
            )
            return

        # REAL UPLOAD MODE - Continue with upload
        console.print()
        if not Confirm.ask("Final confirmation - proceed with REAL upload?"):
            console.print("❌ Upload cancelled")
            return

        # Step 5: REAL UPLOAD
        console.print("\n🚨 PERFORMING REAL UPLOAD TO RED...")

        with REDAPIClient(api_key) as client:
            # Test connection first
            if not client.test_connection():
                console.print("❌ Failed to connect to RED API")
                return

            # Perform real upload
            result = client.real_upload(upload_spec, str(torrent_path))

            if result.success:
                console.print("\n🎉 [bold green]REAL UPLOAD SUCCESSFUL![/bold green]")
                if result.data:
                    torrent_id = result.data.get("torrentid")
                    group_id = result.data.get("groupid")
                    console.print(f"   🧲 Torrent ID: {torrent_id}")
                    console.print(f"   📁 Group ID: {group_id}")
                    if torrent_id:
                        console.print(
                            f"   🔗 URL: https://redacted.sh/torrents.php?torrentid={torrent_id}"
                        )
            else:
                console.print("\n❌ [bold red]UPLOAD FAILED![/bold red]")
                console.print(f"   Error: {result.error}")

    except Exception as e:
        console.print(f"\n❌ Upload failed with exception: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
