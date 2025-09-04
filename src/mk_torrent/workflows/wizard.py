#!/usr/bin/env python3
"""Interactive wizard for common torrent creation tasks"""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table

console = Console()


def run_wizard():
    """Run the interactive wizard"""
    console.print(
        Panel.fit(
            "[bold cyan]🧙 Torrent Creation Wizard[/bold cyan]", border_style="cyan"
        )
    )
    console.print("[cyan]I'll help you create torrents easily![/cyan]\n")

    # Determine user's goal
    console.print("What would you like to do?")
    options = [
        "1. Create a single torrent (simple)",
        "2. Create torrents for a TV series/season",
        "3. Create torrents for a music collection",
        "4. Create torrents for multiple folders",
        "5. Re-create existing torrents",
        "6. Learn about torrent creation",
    ]

    for opt in options:
        console.print(f"  {opt}")

    choice = Prompt.ask(
        "\nSelect option", choices=["1", "2", "3", "4", "5", "6"], default="1"
    )

    if choice == "1":
        wizard_single_torrent()
    elif choice == "2":
        wizard_tv_series()
    elif choice == "3":
        wizard_music_collection()
    elif choice == "4":
        wizard_multiple_folders()
    elif choice == "5":
        wizard_recreate_torrents()
    elif choice == "6":
        show_tutorial()


def wizard_single_torrent():
    """Wizard for creating a single torrent"""
    console.print("\n[cyan]Single Torrent Creation[/cyan]")

    # Get path using file browser if available
    path = browse_for_path("Select file or folder")
    if not path:
        return

    # Determine torrent type
    if path.is_file():
        console.print(f"📄 Creating torrent for file: [green]{path.name}[/green]")
    else:
        size = calculate_folder_size(path)
        console.print(f"📁 Creating torrent for folder: [green]{path.name}[/green]")
        console.print(f"   Size: [yellow]{format_size(size)}[/yellow]")

    # Quick options
    console.print("\n[cyan]Quick Options:[/cyan]")

    preset = Prompt.ask(
        "Choose preset",
        choices=["public", "private", "custom"],
        default="private",  # Changed default to private
    )

    from ..core.torrent_creator import TorrentCreator
    from ..config import load_config

    config = load_config()
    creator = TorrentCreator(config=config)

    # Check if we have API connection
    if not creator.client:
        console.print(
            "[red]❌ qBittorrent API not connected. Please run setup first.[/red]"
        )
        return

    if preset == "public":
        # Use public trackers
        creator.trackers = get_public_trackers()
        creator.private = False
        creator.auto_management = True
        creator.torrent_format = "v1"  # Use v1 for maximum compatibility
    elif preset == "private":
        # Use private tracker settings
        creator.load_default_trackers()
        creator.private = True
        creator.auto_management = config.get("auto_torrent_management", True)
        creator.torrent_format = config.get(
            "default_torrent_format", "v1"
        )  # Use configured format, default v1
    else:
        # Custom configuration
        creator.load_default_trackers()
        creator.private = Confirm.ask(
            "Make private?", default=config.get("default_private", True)
        )
        creator.auto_management = Confirm.ask(
            "Enable automatic management?",
            default=config.get("auto_torrent_management", True),
        )

        # Ask about format
        console.print("\n[cyan]Torrent Format:[/cyan]")
        format_choice = Prompt.ask(
            "Format",
            choices=["v1", "v2", "hybrid"],
            default=config.get("default_torrent_format", "v1"),
        )
        creator.torrent_format = format_choice

        if format_choice == "v2":
            console.print(
                "[yellow]⚠️ Warning: Many trackers don't support v2 torrents[/yellow]"
            )

    # Apply default category and tags from config
    creator.category = config.get("default_category", "")
    creator.tags = config.get("default_tags", [])

    # Ask about auto-seeding
    creator.start_seeding = Confirm.ask(
        "Start seeding automatically?", default=config.get("auto_start_seeding", True)
    )

    # Ask about category/tags if not set
    if not creator.category:
        if Confirm.ask("Set category?", default=False):
            categories = creator._get_available_categories()
            if categories:
                console.print(f"Available: {', '.join(categories[:10])}")
                if len(categories) > 10:
                    console.print(f"  ... and {len(categories) - 10} more")
            creator.category = Prompt.ask("Category", default="")

    if not creator.tags:
        if Confirm.ask("Add tags?", default=False):
            tags = creator._get_available_tags()
            if tags:
                console.print(f"Available: {', '.join(tags[:10])}")
                if len(tags) > 10:
                    console.print(f"  ... and {len(tags) - 10} more")
            tag_input = Prompt.ask("Tags (comma-separated)", default="")
            creator.tags = [t.strip() for t in tag_input.split(",") if t.strip()]

    # Create torrent
    output_dir = Path(config.get("output_directory", Path.home() / "torrents"))
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{path.name}.torrent"

    # Use the qBittorrent API to create the torrent
    if creator.create_torrent_via_api(path, output_path):
        console.print(f"[green]✅ Torrent created: {output_path}[/green]")

        if creator.start_seeding:
            console.print(
                "[green]✅ Torrent added to qBittorrent and seeding started[/green]"
            )

            # Show applied settings
            console.print("\n[cyan]Applied Settings:[/cyan]")
            if creator.category:
                console.print(f"  Category: {creator.category}")
            if creator.tags:
                console.print(f"  Tags: {', '.join(creator.tags)}")
            console.print(f"  Private: {'Yes' if creator.private else 'No'}")
            console.print(
                f"  Auto Management: {'Enabled' if creator.auto_management else 'Disabled'}"
            )
    else:
        console.print("[red]❌ Failed to create torrent[/red]")


def wizard_tv_series():
    """Wizard for TV series torrents"""
    console.print("\n[cyan]TV Series Torrent Creation[/cyan]")

    # Get base directory
    base_dir = browse_for_path("Select TV series folder")
    if not base_dir or not base_dir.is_dir():
        return

    # Detect structure
    console.print("\n[cyan]Detecting series structure...[/cyan]")

    # Look for season folders
    season_folders = sorted(
        [
            d
            for d in base_dir.iterdir()
            if d.is_dir() and ("season" in d.name.lower() or "s0" in d.name.lower())
        ]
    )

    if season_folders:
        console.print(f"Found {len(season_folders)} seasons:")
        for folder in season_folders:
            episode_count = len(list(folder.glob("*.mkv")) + list(folder.glob("*.mp4")))
            console.print(f"  📁 {folder.name} ({episode_count} episodes)")

        # Ask strategy
        strategy = Prompt.ask(
            "How to create torrents?",
            choices=["per-season", "per-episode", "whole-series"],
            default="per-season",
        )

        create_tv_torrents(base_dir, season_folders, strategy)
    else:
        # Single season or flat structure
        episodes = list(base_dir.glob("*.mkv")) + list(base_dir.glob("*.mp4"))
        console.print(f"Found {len(episodes)} episodes")

        if Confirm.ask("Create one torrent for all episodes?", default=True):
            create_single_torrent_guided(base_dir)
        else:
            create_episode_torrents(episodes)


def wizard_music_collection():
    """Wizard for music collection torrents"""
    console.print("\n[cyan]Music Collection Torrent Creation[/cyan]")

    base_dir = browse_for_path("Select music collection folder")
    if not base_dir or not base_dir.is_dir():
        return

    # Detect structure (artist/album)
    console.print("\n[cyan]Analyzing music structure...[/cyan]")

    # Common music patterns
    album_folders = []
    for item in base_dir.iterdir():
        if item.is_dir():
            # Check if it contains music files
            music_files = (
                list(item.glob("*.mp3"))
                + list(item.glob("*.flac"))
                + list(item.glob("*.m4a"))
            )
            if music_files:
                album_folders.append(item)

    if album_folders:
        console.print(f"Found {len(album_folders)} albums:")

        table = Table()
        table.add_column("Album", style="cyan")
        table.add_column("Tracks", style="yellow")
        table.add_column("Format", style="green")

        for folder in album_folders[:10]:  # Show first 10
            tracks = (
                list(folder.glob("*.mp3"))
                + list(folder.glob("*.flac"))
                + list(folder.glob("*.m4a"))
            )
            formats = {t.suffix[1:].upper() for t in tracks}
            table.add_row(folder.name, str(len(tracks)), ", ".join(formats))

        console.print(table)

        if len(album_folders) > 10:
            console.print(f"[dim]... and {len(album_folders) - 10} more[/dim]")

        # Strategy
        strategy = Prompt.ask(
            "How to create torrents?",
            choices=["per-album", "per-artist", "whole-collection"],
            default="per-album",
        )

        create_music_torrents(base_dir, album_folders, strategy)


def browse_for_path(prompt: str) -> Path:
    """Simple path browser"""
    console.print(f"\n[cyan]{prompt}[/cyan]")

    # Try to use fzf if available
    import subprocess

    try:
        result = subprocess.run(
            ["fzf", "--prompt", f"{prompt}: "], capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # Fallback to manual entry
    path_str = Prompt.ask("Enter path", default=".")
    return Path(path_str).expanduser().resolve()


def calculate_folder_size(folder: Path) -> int:
    """Calculate total size of folder"""
    total = 0
    for file in folder.rglob("*"):
        if file.is_file():
            total += file.stat().st_size
    return total


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable"""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def get_public_trackers() -> list[str]:
    """Get list of reliable public trackers"""
    return [
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://open.stealth.si:80/announce",
        "udp://tracker.torrent.eu.org:451/announce",
        "udp://exodus.desync.com:6969/announce",
        "udp://tracker.moeking.me:6969/announce",
    ]


def show_tutorial():
    """Show torrent creation tutorial"""
    console.print(
        Panel.fit(
            "[bold cyan]📚 Torrent Creation Tutorial[/bold cyan]", border_style="cyan"
        )
    )

    sections = [
        (
            "What is a torrent?",
            "A torrent file contains metadata about files and folders to be distributed, "
            "and tracker URLs to coordinate distribution.",
        ),
        (
            "Public vs Private",
            "Public torrents can be shared freely and use public trackers. "
            "Private torrents are for specific trackers and cannot be modified.",
        ),
        (
            "Piece Size",
            "Smaller pieces = more overhead but better for small files. "
            "Larger pieces = less overhead but worse for small files. "
            "Auto mode picks the best size.",
        ),
        (
            "Trackers",
            "Trackers coordinate peers. More trackers = better availability. "
            "Private trackers usually require specific announce URLs.",
        ),
        (
            "Best Practices",
            "• Use descriptive names\n"
            "• Include NFO files for information\n"
            "• Test torrents before sharing\n"
            "• Seed to at least 1.0 ratio",
        ),
    ]

    for title, content in sections:
        console.print(f"\n[cyan]{title}[/cyan]")
        console.print(content)

    console.print(
        "\n[green]Ready to create your first torrent? Run 'python run.py wizard'[/green]"
    )


# Helper functions for batch operations
def create_tv_torrents(base_dir: Path, folders: list[Path], strategy: str):
    """Create torrents for TV content"""
    from ..core.torrent_creator import TorrentCreator
    from ..config import load_config

    config = load_config()
    creator = TorrentCreator(config=config)

    if not creator.client:
        console.print("[red]❌ qBittorrent API not connected[/red]")
        return

    # Load default trackers
    creator.load_default_trackers()

    # TV-specific settings
    creator.category = "TV Shows"  # Override with TV category
    creator.tags = ["tv", "series"]
    creator.start_seeding = True
    creator.torrent_format = config.get(
        "default_torrent_format", "v1"
    )  # Use v1 for compatibility

    output_dir = Path(config.get("output_directory", Path.home() / "torrents")) / "TV"
    output_dir.mkdir(parents=True, exist_ok=True)

    if strategy == "per-season":
        for folder in folders:
            console.print(f"\n[cyan]Creating torrent for: {folder.name}[/cyan]")
            output_path = output_dir / f"{folder.name}.torrent"

            if creator.create_torrent_via_api(folder, output_path):
                console.print(f"[green]✓ Created: {output_path.name}[/green]")
            else:
                console.print(f"[red]✗ Failed: {folder.name}[/red]")

    elif strategy == "whole-series":
        output_path = output_dir / f"{base_dir.name}.torrent"
        if creator.create_torrent_via_api(base_dir, output_path):
            console.print(
                f"[green]✓ Created series torrent: {output_path.name}[/green]"
            )
        else:
            console.print("[red]✗ Failed to create series torrent[/red]")


def create_music_torrents(base_dir: Path, folders: list[Path], strategy: str):
    """Create torrents for music content"""
    # Implementation for music torrent creation
    pass


def create_episode_torrents(episodes: list[Path]):
    """Create individual torrents for episodes"""
    # Implementation for episode torrent creation
    pass


def create_single_torrent_guided(path: Path):
    """Create a single torrent with guidance"""
    # Implementation for guided single torrent
    pass


def wizard_multiple_folders():
    """Wizard for multiple folder torrents with smart selection"""
    console.print("\n[cyan]Multiple Folder Torrent Creation[/cyan]")

    base_dir = browse_for_path("Select base directory")
    if not base_dir or not base_dir.is_dir():
        return

    # Count items
    all_items = [
        d for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
    ]
    console.print(f"[cyan]Found {len(all_items)} folders[/cyan]")

    if len(all_items) == 0:
        console.print("[yellow]No folders found[/yellow]")
        return

    # Selection strategy
    console.print("\n[cyan]How would you like to select folders?[/cyan]")
    strategy = Prompt.ask(
        "Selection method",
        choices=["first-n", "last-n", "pattern", "size", "manual"],
        default="first-n",
    )

    selected_items = []

    if strategy == "first-n":
        # Fix: Use IntPrompt without min_value/max_value
        while True:
            try:
                n = IntPrompt.ask(f"How many folders? (1-{len(all_items)})", default=5)
                if 1 <= n <= len(all_items):
                    break
                console.print(
                    f"[red]Please enter a number between 1 and {len(all_items)}[/red]"
                )
            except ValueError:
                console.print("[red]Please enter a valid number[/red]")
        selected_items = sorted(all_items)[:n]

    elif strategy == "last-n":
        # Fix: Use IntPrompt without min_value/max_value
        while True:
            try:
                n = IntPrompt.ask(f"How many folders? (1-{len(all_items)})", default=5)
                if 1 <= n <= len(all_items):
                    break
                console.print(
                    f"[red]Please enter a number between 1 and {len(all_items)}[/red]"
                )
            except ValueError:
                console.print("[red]Please enter a valid number[/red]")
        selected_items = sorted(all_items)[-n:]

    elif strategy == "pattern":
        pattern = Prompt.ask("Pattern (e.g., *2024*, Season*)")
        import fnmatch

        selected_items = [d for d in all_items if fnmatch.fnmatch(d.name, pattern)]

    elif strategy == "size":
        # Select by size
        console.print("Calculating folder sizes...")
        items_with_size = []
        for item in all_items:
            size = calculate_folder_size(item)
            items_with_size.append((item, size))

        # Sort by size
        items_with_size.sort(key=lambda x: x[1], reverse=True)

        # Show sizes
        console.print("\n[cyan]Folders by size:[/cyan]")
        for i, (item, size) in enumerate(items_with_size[:20], 1):
            console.print(f"{i:3d}. {item.name} [{format_size(size)}]")

        if len(items_with_size) > 20:
            console.print(f"[dim]... and {len(items_with_size) - 20} more[/dim]")

        # Fix: Use IntPrompt without min_value/max_value
        while True:
            try:
                n = IntPrompt.ask(
                    f"Select top N largest folders (1-{len(items_with_size)})",
                    default=5,
                )
                if 1 <= n <= len(items_with_size):
                    break
                console.print(
                    f"[red]Please enter a number between 1 and {len(items_with_size)}[/red]"
                )
            except ValueError:
                console.print("[red]Please enter a valid number[/red]")
        selected_items = [item for item, size in items_with_size[:n]]

    elif strategy == "manual":
        # Manual selection with numbers
        console.print("\n[cyan]Available folders:[/cyan]")
        for i, item in enumerate(sorted(all_items), 1):
            console.print(f"{i:3d}. {item.name}")

        selection = Prompt.ask("Enter numbers (e.g., 1-5,7,9-12)", default="1-5")

        indices = parse_number_selection(selection, len(all_items))
        selected_items = [all_items[i - 1] for i in indices]

    if not selected_items:
        console.print("[yellow]No items selected[/yellow]")
        return

    # Show selection
    console.print(f"\n[green]Selected {len(selected_items)} folders:[/green]")
    for item in selected_items[:10]:
        console.print(f"  • {item.name}")
    if len(selected_items) > 10:
        console.print(f"  [dim]... and {len(selected_items) - 10} more[/dim]")

    if not Confirm.ask("\nProceed with torrent creation?", default=True):
        return

    # Create torrents
    from ..core.torrent_creator import TorrentCreator
    from ..config import load_config

    config = load_config()
    creator = TorrentCreator(config=config)

    if not creator.client:
        console.print("[red]❌ qBittorrent API not connected[/red]")
        return

    # Load settings
    creator.load_default_trackers()
    creator.private = config.get("default_private", True)
    creator.torrent_format = config.get("default_torrent_format", "v1")
    creator.start_seeding = config.get("auto_start_seeding", True)

    output_dir = Path(config.get("output_directory", Path.home() / "torrents"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create torrents
    successful = 0
    failed = 0

    # Ask about parallel creation for large batches
    use_parallel = False
    if len(selected_items) > 5:
        use_parallel = Confirm.ask(
            f"\n[cyan]Create {len(selected_items)} torrents in parallel?[/cyan]",
            default=True,
        )

    if use_parallel:
        # Prepare paths for parallel creation
        from ..utils.async_helpers import run_async_batch

        paths = []
        for item in selected_items:
            output_path = output_dir / f"{item.name}.torrent"
            paths.append((item, output_path))

        console.print("\n[cyan]Creating torrents in parallel...[/cyan]")
        results = run_async_batch(paths, creator)

        successful = sum(1 for r in results if r)
        failed = sum(1 for r in results if not r)
    else:
        # Original synchronous approach
        for item in selected_items:
            console.print(f"\n[cyan]Creating torrent for: {item.name}[/cyan]")
            output_path = output_dir / f"{item.name}.torrent"

            if creator.create_torrent_via_api(item, output_path):
                successful += 1
                console.print(f"[green]✓ Created: {output_path.name}[/green]")
            else:
                failed += 1
                console.print(f"[red]✗ Failed: {item.name}[/red]")

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  [green]Successful: {successful}[/green]")
    if failed > 0:
        console.print(f"  [red]Failed: {failed}[/red]")


def parse_number_selection(selection: str, max_num: int) -> list[int]:
    """Parse number selection like '1-5,7,9-12' into list of indices"""
    indices = set()

    try:
        for part in selection.split(","):
            part = part.strip()
            if "-" in part:
                # Range
                start, end = part.split("-")
                start, end = int(start.strip()), int(end.strip())
                indices.update(range(max(1, start), min(max_num + 1, end + 1)))
            else:
                # Single number
                num = int(part)
                if 1 <= num <= max_num:
                    indices.add(num)
    except ValueError:
        console.print("[red]Invalid selection format[/red]")
        return []

    return sorted(indices)


def wizard_recreate_torrents():
    """Wizard for recreating existing torrents"""
    console.print("\n[cyan]Torrent Recreation[/cyan]")
    console.print(
        "[yellow]This feature helps you recreate torrents from existing data[/yellow]"
    )

    # Get the directory containing data
    data_dir = browse_for_path("Select directory with existing torrent data")
    if not data_dir or not data_dir.is_dir():
        return

    console.print("\n[cyan]Looking for .torrent files...[/cyan]")

    # Find existing torrent files
    torrent_files = list(data_dir.glob("*.torrent"))
    if not torrent_files:
        console.print("[yellow]No .torrent files found in directory[/yellow]")
        console.print(
            "[dim]Place the original .torrent files in the same directory as the data[/dim]"
        )
        return

    console.print(f"Found {len(torrent_files)} torrent files")

    # For now, just inform the user
    console.print("\n[yellow]Recreation feature coming soon![/yellow]")
    console.print("This will allow you to:")
    console.print("  • Recreate torrents with the same piece boundaries")
    console.print("  • Preserve the original info hash")
    console.print("  • Update tracker URLs")
    console.print("  • Convert between v1/v2/hybrid formats")
