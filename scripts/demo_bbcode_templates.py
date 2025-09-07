#!/usr/bin/env python3
"""
Demo script showcasing BBCode templates with rich console output.

This script demonstrates the BBCode template rendering system by extracting
real metadata from a sample audiobook and generating both the full description
template and the release info template.

Usage:
    python scripts/demo_bbcode_templates.py
"""

import sys
from pathlib import Path
from typing import Any, Dict
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mk_torrent.core.metadata.engine import MetadataEngine
from mk_torrent.core.metadata.mappers.red import REDMapper
from mk_torrent.core.metadata.base import AudiobookMeta
from mk_torrent.core.metadata.templates.renderer import TemplateRenderer

console = Console()

# Sample audiobook path
SAMPLE_AUDIOBOOK = Path(
    "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/"
    "How a Realist Hero Rebuilt the Kingdom - vol_09 (2023) (Dojyomaru) "
    "{ASIN.B0CPML76KX} [H2OKing]/How a Realist Hero Rebuilt the Kingdom - "
    "vol_09 {ASIN.B0CPML76KX}.m4b"
)


def extract_metadata() -> Dict[str, Any]:
    """Extract metadata from the sample audiobook."""
    console.print("\n[cyan]📚 Extracting metadata from sample audiobook...[/cyan]")

    if not SAMPLE_AUDIOBOOK.exists():
        console.print(f"[red]❌ Sample audiobook not found: {SAMPLE_AUDIOBOOK}[/red]")
        sys.exit(1)

    # Initialize metadata engine
    engine = MetadataEngine()
    engine.setup_default_processors()

    # Extract metadata
    metadata = engine.extract_metadata(SAMPLE_AUDIOBOOK, content_type="audiobook")

    console.print(f"[green]✅ Extracted {len(metadata)} metadata fields[/green]")
    return metadata


def create_audiobook_meta(metadata: Dict[str, Any]) -> AudiobookMeta:
    """Convert raw metadata to AudiobookMeta object."""
    console.print("\n[cyan]🔄 Converting to AudiobookMeta object...[/cyan]")

    # Create AudiobookMeta from extracted metadata
    audiobook_meta = AudiobookMeta.from_dict(metadata)

    console.print(f"[green]✅ Created AudiobookMeta: '{audiobook_meta.title}'[/green]")
    return audiobook_meta


def demo_template_data_building():
    """Demonstrate template data building process."""
    console.print("\n[cyan]🔧 Building template data structure...[/cyan]")

    # Extract metadata
    raw_metadata = extract_metadata()

    # Use the real AudiobookMeta.from_dict() method to create proper metadata object
    audiobook_meta = AudiobookMeta.from_dict(raw_metadata)

    # Create mapper and build template data
    mapper = REDMapper()
    template_data = mapper.build_template_data(audiobook_meta)

    # Display template data structure
    table = Table(
        title="Template Data Structure", show_header=True, header_style="bold magenta"
    )
    table.add_column("Section", style="cyan")
    table.add_column("Key Fields", style="yellow")
    table.add_column("Sample Value", style="green")

    # Description section
    desc = template_data["description"]
    table.add_row("description.title", "Main title", desc["title"])
    table.add_row(
        "description.subtitle", "Series info", str(desc.get("subtitle", "None"))
    )
    table.add_row(
        "description.book_info.authors",
        "Author list",
        str(desc["book_info"]["authors"]),
    )
    table.add_row(
        "description.book_info.narrators",
        "Narrator list",
        str(desc["book_info"]["narrators"]),
    )
    table.add_row(
        "description.book_info.publisher", "Publisher", desc["book_info"]["publisher"]
    )
    table.add_row("description.chapters", "Chapter count", str(len(desc["chapters"])))

    # Release section
    release = template_data["release"]
    table.add_row("release.container", "File format", release["container"])
    table.add_row("release.codec", "Audio codec", release["codec"])
    table.add_row("release.bitrate_kbps", "Bitrate", str(release["bitrate_kbps"]))
    table.add_row("release.duration_ms", "Duration", str(release["duration_ms"]))
    table.add_row("release.filesize_bytes", "File size", str(release["filesize_bytes"]))

    console.print(table)
    return template_data


def demo_bbcode_description(template_data: Dict[str, Any]):
    """Generate and display the full BBCode description."""
    console.print("\n[cyan]📝 Generating BBCode description template...[/cyan]")

    # Initialize template renderer
    renderer = TemplateRenderer()

    try:
        # Render the description template
        description_bbcode = renderer.render_template(
            "bbcode_desc.jinja", **template_data
        )

        # Display in a panel
        console.print(
            Panel(
                Syntax(
                    description_bbcode, "bbcode", theme="monokai", line_numbers=False
                ),
                title="[bold yellow]BBCode Description Template[/bold yellow]",
                border_style="yellow",
            )
        )

        return description_bbcode

    except Exception as e:
        console.print(f"[red]❌ Error rendering description template: {e}[/red]")
        return None


def demo_bbcode_release_info(template_data: Dict[str, Any]):
    """Generate and display the release info BBCode."""
    console.print("\n[cyan]🎵 Generating BBCode release info template...[/cyan]")

    # Initialize template renderer
    renderer = TemplateRenderer()

    try:
        # Render the release info template
        release_bbcode = renderer.render_template(
            "bbcode_release_desc.jinja", **template_data
        )

        # Display in a panel
        console.print(
            Panel(
                Syntax(release_bbcode, "bbcode", theme="monokai", line_numbers=False),
                title="[bold blue]BBCode Release Info Template[/bold blue]",
                border_style="blue",
            )
        )

        return release_bbcode

    except Exception as e:
        console.print(f"[red]❌ Error rendering release template: {e}[/red]")
        return None


def demo_red_mapping():
    """Demonstrate complete RED mapping with templates."""
    console.print("\n[cyan]🎯 Demonstrating complete RED mapping...[/cyan]")

    # Extract metadata and use real AudiobookMeta
    raw_metadata = extract_metadata()
    audiobook_meta = AudiobookMeta.from_dict(raw_metadata)

    # Create RED mapper and generate upload data
    mapper = REDMapper()
    red_upload_data = mapper.map_to_red_upload(audiobook_meta, include_description=True)

    # Display key RED fields
    table = Table(
        title="RED Upload Data", show_header=True, header_style="bold magenta"
    )
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="yellow")

    # Add key fields to table
    for key, value in red_upload_data.items():
        if key == "description" and len(str(value)) > 100:
            table.add_row(key, f"{str(value)[:100]}...")
        else:
            table.add_row(key, str(value))

    console.print(table)
    return red_upload_data


def main():
    """Main demo function."""
    console.rule("[bold red]BBCode Templates Demo", style="red")

    try:
        # 1. Build template data
        template_data = demo_template_data_building()

        # 2. Generate BBCode description
        description_bbcode = demo_bbcode_description(template_data)

        # 3. Generate BBCode release info
        release_bbcode = demo_bbcode_release_info(template_data)

        # 4. Demonstrate complete RED mapping
        demo_red_mapping()

        # 5. Summary
        console.rule("[bold green]Demo Complete", style="green")
        console.print("\n[green]✅ Successfully demonstrated:[/green]")
        console.print("  • Metadata extraction from real audiobook")
        console.print("  • Template data structure building")
        console.print("  • BBCode description generation")
        console.print("  • BBCode release info generation")
        console.print("  • Complete RED tracker mapping")

        if description_bbcode and release_bbcode:
            console.print(
                "\n[yellow]📋 Both templates rendered successfully with real data![/yellow]"
            )

    except Exception as e:
        console.print(f"\n[red]❌ Demo failed: {e}[/red]")
        import traceback

        console.print(f"[red]{traceback.format_exc()}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
