#!/usr/bin/env python3
"""Database operations for torrent history tracking"""

from pathlib import Path
from typing import Any
import json
from datetime import datetime

from rich.console import Console

console = Console()


def get_history(limit: int = 10) -> list[dict[str, Any]]:
    """Get torrent creation history"""
    # Simple JSON-based history for now
    history_file = get_history_file()
    if not history_file.exists():
        return []

    try:
        with open(history_file) as f:
            history = json.load(f)
        return history[-limit:] if limit > 0 else history
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def clear_history() -> None:
    """Clear all history"""
    history_file = get_history_file()
    if history_file.exists():
        history_file.unlink()
        console.print("[green]History cleared[/green]")
    else:
        console.print("[yellow]No history to clear[/yellow]")


def add_history_entry(path: str, size: int, status: str) -> None:
    """Add entry to history"""
    history_file = get_history_file()
    history_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing history
    history = get_history(0)  # Get all

    # Add new entry
    entry = {
        "timestamp": datetime.now().isoformat(),
        "path": path,
        "size": size,
        "status": status,
    }
    history.append(entry)

    # Keep only last 100 entries
    history = history[-100:]

    # Save back
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)


def get_history_file() -> Path:
    """Get path to history file"""
    return Path.home() / ".config" / "torrent_creator" / "history.json"


def save_torrent_history(
    source: Path, output: Path, trackers: list[str], private: bool
):
    """Save torrent creation to history"""
    # Calculate file size
    if source.is_file():
        size = source.stat().st_size
    else:
        size = sum(f.stat().st_size for f in source.rglob("*") if f.is_file())

    add_history_entry(path=str(source), size=size, status="created")


def get_recent_torrents(limit: int = 10) -> list[dict[str, Any]]:
    """Get recent torrent creations"""
    return get_history(limit)
