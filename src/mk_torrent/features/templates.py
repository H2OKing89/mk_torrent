#!/usr/bin/env python3
"""Template management for torrent creation"""

from pathlib import Path
from typing import Dict, Any, List
import json

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm  # Add these imports

console = Console()


def save_template(template: Dict[str, Any]) -> bool:
    """Save a template to disk"""
    templates_dir = Path.home() / ".config" / "torrent_creator" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from template name
    name = template.get("name", "template")
    filename = f"{name.replace(' ', '_').lower()}.json"
    template_file = templates_dir / filename

    try:
        with open(template_file, "w") as f:
            json.dump(template, f, indent=2)
        console.print(f"[green]✓ Template saved: {template_file}[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Failed to save template: {e}[/red]")
        return False


def load_templates() -> List[Dict[str, Any]]:
    """Load all templates from disk"""
    templates_dir = Path.home() / ".config" / "torrent_creator" / "templates"
    if not templates_dir.exists():
        return []

    templates = []
    for template_file in templates_dir.glob("*.json"):
        try:
            with open(template_file) as f:
                template = json.load(f)
                template["filename"] = template_file.name
                templates.append(template)
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not load template {template_file.name}: {e}[/yellow]"
            )

    return templates


def save_templates(templates: List[Dict[str, Any]]) -> None:
    """Save multiple templates"""
    for template in templates:
        save_template(template)  # Fix: This line was incorrectly indented


def list_templates() -> List[Dict[str, Any]]:
    """List all available templates"""
    return load_templates()


def apply_template_cli(template_name: str, source_path: Path) -> bool:
    """Apply a template via CLI"""
    templates = list_templates()

    # Find template by name
    template = None
    for t in templates:
        if (
            t.get("name") == template_name
            or t.get("filename") == f"{template_name}.json"
        ):
            template = t
            break

    if not template:
        console.print(f"[red]Template not found: {template_name}[/red]")
        return False

    console.print(
        f"[cyan]Applying template: {template.get('name', template_name)}[/cyan]"
    )

    # Apply template settings (this would integrate with torrent_creator)
    # For now, just show what would be applied
    table = Table()
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="yellow")

    for key, value in template.items():
        if key not in ["filename", "name", "description"]:
            table.add_row(key, str(value))

    console.print(table)
    return True


def view_templates(templates: Dict[str, Any]):
    """Display all templates"""
    if not templates:
        console.print("[yellow]No templates saved[/yellow]")
        return

    table = Table(title="Saved Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Trackers", style="yellow")
    table.add_column("Private", style="magenta")

    for name, template in templates.items():
        table.add_row(
            name,
            template.get("type", "general"),
            str(len(template.get("trackers", []))),
            "Yes" if template.get("private", False) else "No",
        )

    console.print(table)


def create_template(templates: Dict[str, Any]):
    """Create a new template"""
    name = Prompt.ask("Template name")
    if name in templates:
        if not Confirm.ask(f"Template '{name}' exists. Overwrite?", default=False):
            return

    template = {
        "name": name,
        "type": Prompt.ask(
            "Type",
            choices=["general", "movie", "tv", "music", "software"],
            default="general",
        ),
        "trackers": [],  # Initialize as list
        "private": Confirm.ask("Private torrent?", default=False),
        "piece_size": Prompt.ask("Piece size", default="Auto"),
        "comment": Prompt.ask("Default comment", default=""),
        "category": Prompt.ask("Category", default=""),
        "tags": Prompt.ask("Tags (comma-separated)", default="").split(","),
    }

    # Add trackers
    console.print("Add tracker URLs (empty to finish):")
    while True:
        tracker = Prompt.ask("Tracker", default="")
        if not tracker:
            break
        # Fix: Ensure trackers is a list before appending
        if isinstance(template["trackers"], list):
            template["trackers"].append(tracker)
        else:
            template["trackers"] = [tracker]

    templates[name] = template
    console.print(f"[green]✅ Template '{name}' created[/green]")


def edit_template(templates: Dict[str, Any]):
    """Edit existing template"""
    if not templates:
        console.print("[yellow]No templates to edit[/yellow]")
        return

    name = Prompt.ask("Template to edit", choices=list(templates.keys()))
    template = templates[name]

    # Edit each field
    template["type"] = Prompt.ask("Type", default=template.get("type", "general"))
    template["private"] = Confirm.ask(
        "Private?", default=template.get("private", False)
    )
    template["piece_size"] = Prompt.ask(
        "Piece size", default=template.get("piece_size", "Auto")
    )

    console.print(f"[green]✅ Template '{name}' updated[/green]")


def delete_template(templates: Dict[str, Any]):
    """Delete a template"""
    if not templates:
        console.print("[yellow]No templates to delete[/yellow]")
        return

    name = Prompt.ask("Template to delete", choices=list(templates.keys()))

    if Confirm.ask(f"Delete template '{name}'?", default=False):
        del templates[name]
        console.print(f"[green]✅ Template '{name}' deleted[/green]")


def apply_template(templates: Dict[str, Any]):
    """Apply a template to create torrent"""
    if not templates:
        console.print("[yellow]No templates available[/yellow]")
        return

    name = Prompt.ask("Template to apply", choices=list(templates.keys()))
    template = templates[name]

    # Get path for torrent
    path_str = Prompt.ask("Path to create torrent for")
    path = Path(path_str).expanduser().resolve()

    if not path.exists():
        console.print(f"[red]Path does not exist: {path}[/red]")
        return

    # Create torrent using template
    from ..core.torrent_creator import TorrentCreator
    from ..config import load_config

    config = load_config()
    creator = TorrentCreator(config=config)

    # Apply template settings
    creator.trackers = template.get("trackers", [])
    creator.private = template.get("private", False)
    creator.piece_size = template.get("piece_size", "Auto")
    creator.comment = template.get("comment", "")
    creator.category = template.get("category", "")

    # Fix: Ensure tags is a list
    template_tags = template.get("tags", [])
    if isinstance(template_tags, list):
        creator.tags = template_tags
    elif isinstance(template_tags, str):
        creator.tags = [template_tags]
    else:
        creator.tags = []

    # Create torrent
    output_path = Path(config.get("output_directory", ".")) / f"{path.name}.torrent"

    with console.status("Creating torrent from template...", spinner="dots"):
        # Fix: Use create_torrent_via_api instead of create_torrent_file
        if creator.create_torrent_via_api(path, output_path):
            console.print(f"[green]✅ Torrent created: {output_path}[/green]")
        else:
            console.print("[red]❌ Failed to create torrent[/red]")
