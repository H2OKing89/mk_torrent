#!/usr/bin/env python3
"""Cross-seeding utilities for torrent management"""

from pathlib import Path
from typing import List, Tuple
import hashlib
import bencode  # pip install bencode.py

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

console = Console()


class CrossSeedManager:
    """Manage torrents for cross-seeding across multiple trackers"""

    def __init__(self, backup_dir: Path):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def prepare_for_cross_seed(
        self, original_torrent: Path, new_tracker: str, new_source: str
    ) -> Path:
        """
        Prepare a torrent for cross-seeding on another tracker

        Args:
            original_torrent: Path to original .torrent file
            new_tracker: New tracker announce URL
            new_source: New source tag

        Returns:
            Path to modified torrent file
        """
        # Read original torrent
        with open(original_torrent, "rb") as f:
            torrent_data = bencode.decode(f.read())

        # Modify for new tracker
        torrent_data[b"announce"] = new_tracker.encode()

        # Update source if present
        if b"info" in torrent_data and b"source" in torrent_data[b"info"]:
            torrent_data[b"info"][b"source"] = new_source.encode()

        # Remove any tracker-specific fields
        if b"comment" in torrent_data:
            del torrent_data[b"comment"]
        if b"created by" in torrent_data:
            torrent_data[b"created by"] = b"qBittorrent Torrent Creator (cross-seed)"

        # Save modified torrent
        output_name = f"{original_torrent.stem}_{new_source}.torrent"
        output_path = self.backup_dir / output_name

        with open(output_path, "wb") as f:
            f.write(bencode.encode(torrent_data))

        return output_path

    def verify_cross_seed_compatibility(
        self, torrent1: Path, torrent2: Path
    ) -> Tuple[bool, str]:
        """
        Verify two torrents are compatible for cross-seeding

        Returns:
            (compatible, message)
        """
        try:
            with open(torrent1, "rb") as f:
                data1 = bencode.decode(f.read())
            with open(torrent2, "rb") as f:
                data2 = bencode.decode(f.read())

            # Check piece size
            if data1[b"info"][b"piece length"] != data2[b"info"][b"piece length"]:
                return False, "Different piece sizes"

            # Check file structure
            if b"files" in data1[b"info"]:
                # Multi-file torrent
                files1 = sorted(
                    [(f[b"path"], f[b"length"]) for f in data1[b"info"][b"files"]]
                )
                files2 = sorted(
                    [(f[b"path"], f[b"length"]) for f in data2[b"info"][b"files"]]
                )
                if files1 != files2:
                    return False, "Different file structure"
            else:
                # Single file torrent
                if data1[b"info"][b"length"] != data2[b"info"][b"length"]:
                    return False, "Different file size"

            # Check info hash (should be different due to source)
            info_hash1 = hashlib.sha1(bencode.encode(data1[b"info"])).hexdigest()
            info_hash2 = hashlib.sha1(bencode.encode(data2[b"info"])).hexdigest()

            if info_hash1 == info_hash2:
                return False, "Identical info hashes (no source differentiation)"

            return True, "Compatible for cross-seeding"

        except Exception as e:
            return False, f"Error: {e}"

    def list_backup_torrents(self) -> List[Path]:
        """List all backed up torrent files"""
        return sorted(self.backup_dir.glob("*.torrent"))

    def organize_by_source(self):
        """Organize backed up torrents by source tag"""
        torrents_by_source = {}

        for torrent_file in self.list_backup_torrents():
            # Try to extract source from filename
            parts = torrent_file.stem.split("_")
            if len(parts) > 1:
                source = parts[-1]
            else:
                source = "unknown"

            if source not in torrents_by_source:
                torrents_by_source[source] = []
            torrents_by_source[source].append(torrent_file)

        return torrents_by_source


def cross_seed_wizard():
    """Interactive wizard for cross-seeding setup"""
    from config import load_config

    config = load_config()
    backup_dir = Path(config.get("backup_directory", Path.home() / "torrent_backups"))

    manager = CrossSeedManager(backup_dir)

    console.print("[bold cyan]🔄 Cross-Seeding Wizard[/bold cyan]")

    # List available torrents
    torrents = manager.list_backup_torrents()
    if not torrents:
        console.print("[yellow]No backup torrents found[/yellow]")
        return

    console.print(f"\nFound {len(torrents)} backup torrents")

    # Organize by source
    by_source = manager.organize_by_source()

    table = Table(title="Torrents by Source")
    table.add_column("Source", style="cyan")
    table.add_column("Count", style="yellow")
    table.add_column("Latest", style="green")

    for source, files in by_source.items():
        latest = max(files, key=lambda p: p.stat().st_mtime)
        table.add_row(source, str(len(files)), latest.name[:40] + "...")

    console.print(table)

    # Select action
    action = Prompt.ask(
        "\nWhat would you like to do?",
        choices=["prepare", "verify", "list", "exit"],
        default="exit",
    )

    if action == "prepare":
        # Prepare for cross-seeding
        source_torrents = Prompt.ask("Enter path to torrent file")
        new_tracker = Prompt.ask("New tracker announce URL")
        new_source = Prompt.ask("New source tag")

        try:
            new_torrent = manager.prepare_for_cross_seed(
                Path(source_torrents), new_tracker, new_source
            )
            console.print(f"[green]✓ Created cross-seed torrent: {new_torrent}[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    elif action == "verify":
        # Verify compatibility
        torrent1 = Prompt.ask("First torrent path")
        torrent2 = Prompt.ask("Second torrent path")

        compatible, message = manager.verify_cross_seed_compatibility(
            Path(torrent1), Path(torrent2)
        )

        if compatible:
            console.print(f"[green]✓ {message}[/green]")
        else:
            console.print(f"[red]✗ {message}[/red]")
