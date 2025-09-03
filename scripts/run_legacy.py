#!/usr/bin/env python3
"""Entry point for the torrent creator application"""

import sys
from pathlib import Path

from rich.console import Console

console = Console()

# Add the script directory to path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent))

try:
    from cli import main

    if __name__ == "__main__":
        main()
except ImportError as e:
    console.print(f"[red]Error: {e}[/red]")
    console.print("\n[dim]Please ensure you're in the correct directory:[/dim]")
    console.print("  [cyan]cd /mnt/cache/scripts/mk_torrent[/cyan]")
    console.print("  [cyan]python run.py [command][/cyan]")
    sys.exit(1)
