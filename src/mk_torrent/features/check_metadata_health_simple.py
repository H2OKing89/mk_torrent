#!/usr/bin/env python3
"""Simple Metadata Health Check Script"""

import sys
from rich.console import Console

console = Console()


def main():
    """Main entry point"""
    console.print("[bold blue]Metadata Health Checker[/bold blue]")
    console.print("Basic health check for metadata processing capabilities\n")

    try:
        # Check basic dependencies
        console.print("[cyan]Checking Dependencies...[/cyan]")

        import importlib.util

        missing = []
        if importlib.util.find_spec("mutagen") is not None:
            console.print("  ✅ mutagen: Available")
        else:
            console.print("  ❌ mutagen: Missing")
            missing.append("mutagen")

        if importlib.util.find_spec("requests") is not None:
            console.print("  ✅ requests: Available")
        else:
            console.print("  ❌ requests: Missing")
            missing.append("requests")

        # Check capabilities
        console.print("\n[cyan]Checking Capabilities...[/cyan]")

        if importlib.util.find_spec("mutagen.mp3") is not None:
            console.print("  ✅ MP3 support: Available")
        else:
            console.print("  ❌ MP3 support: Missing")

        if importlib.util.find_spec("mutagen.flac") is not None:
            console.print("  ✅ FLAC support: Available")
        else:
            console.print("  ❌ FLAC support: Missing")

        # Summary
        console.print("\n[bold green]Health Check Complete[/bold green]")

        if missing:
            console.print(f"[yellow]Missing packages: {', '.join(missing)}[/yellow]")
            console.print(
                "[yellow]Install with: pip install {' '.join(missing)}[/yellow]"
            )
        else:
            console.print("[green]All basic dependencies available![/green]")

    except Exception as e:
        console.print(f"[red]Health check failed: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
