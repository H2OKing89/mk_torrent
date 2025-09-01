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

        missing = []
        try:
            import mutagen
            console.print("  ✅ mutagen: Available")
        except ImportError:
            console.print("  ❌ mutagen: Missing")
            missing.append("mutagen")

        try:
            import requests
            console.print("  ✅ requests: Available")
        except ImportError:
            console.print("  ❌ requests: Missing")
            missing.append("requests")

        # Check capabilities
        console.print("\n[cyan]Checking Capabilities...[/cyan]")

        try:
            from mutagen.mp3 import MP3
            console.print("  ✅ MP3 support: Available")
        except ImportError:
            console.print("  ❌ MP3 support: Missing")

        try:
            from mutagen.flac import FLAC
            console.print("  ✅ FLAC support: Available")
        except ImportError:
            console.print("  ❌ FLAC support: Missing")

        # Summary
        console.print("\n[bold green]Health Check Complete[/bold green]")

        if missing:
            console.print(f"[yellow]Missing packages: {', '.join(missing)}[/yellow]")
            console.print("[yellow]Install with: pip install {' '.join(missing)}[/yellow]")
        else:
            console.print("[green]All basic dependencies available![/green]")

    except Exception as e:
        console.print(f"[red]Health check failed: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
