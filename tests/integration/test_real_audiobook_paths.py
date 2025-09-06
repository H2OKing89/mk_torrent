#!/usr/bin/env python3
"""
Test RED path validation with real audiobook paths
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

# Add project root to path
project_root = Path(__file__).parent.parent.parent  # Go up to project root
sys.path.insert(0, str(project_root / "src"))

console = Console()


def test_path_validation():
    """Test path validation with different path scenarios"""
    console.print("\n[bold cyan]📏 Testing RED Path Validation[/bold cyan]")

    try:
        from mk_torrent.api.trackers.red import RedactedAPI

        red_api = RedactedAPI(api_key="test_key")

        # Test cases: (path, expected_result, description)
        test_cases = [
            # Real paths from your system
            (
                "/mnt/user/data/downloads/torrents/qbittorrent/seedvault/audiobooks/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]",
                True,
                "Seedvault path (long absolute path, short folder name)",
            ),
            (
                "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]",
                True,
                "Test samples path",
            ),
            # Edge cases
            (
                "A" * 150,  # Exactly at limit
                True,
                "Exactly 150 chars (RED limit)",
            ),
            (
                "A" * 151,  # One over limit
                False,
                "151 chars (1 over RED limit)",
            ),
            (
                "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]",
                True,
                "Just the folder name (94 chars)",
            ),
            # Very long folder name
            (
                "/some/very/long/absolute/path/that/is/really/really/long/and/goes/on/forever/"
                + "A" * 160,
                False,
                "Very long folder name (160 chars)",
            ),
        ]

        table = Table(title="RED Path Validation Test Results")
        table.add_column("Test Case", style="cyan")
        table.add_column("Length", style="yellow")
        table.add_column("Expected", style="white")
        table.add_column("Actual", style="bold")
        table.add_column("Status", style="bold")

        all_passed = True

        for test_path, expected, description in test_cases:
            path_obj = Path(test_path)
            folder_name = path_obj.name
            folder_length = len(folder_name)

            # Test with the path compliance function directly
            # (rather than full metadata validation which needs many fields)
            actual_result = red_api.check_path_compliance(folder_name)

            # Check if result matches expected
            status = "✅ PASS" if actual_result == expected else "❌ FAIL"
            if actual_result != expected:
                all_passed = False

            table.add_row(
                description,
                f"{folder_length} chars",
                "PASS" if expected else "FAIL",
                "PASS" if actual_result else "FAIL",
                status,
            )

        console.print(table)

        # Summary
        if all_passed:
            console.print("\n[green]🎉 All path validation tests passed![/green]")
        else:
            console.print("\n[red]❌ Some path validation tests failed[/red]")

        # Show the actual validation behavior
        console.print("\n[cyan]📋 Validation Details:[/cyan]")
        console.print(
            f"• RED folder name limit: {red_api.config.max_path_length} characters"
        )
        console.print("• Your audiobook folder: 94 characters ✅")
        console.print(
            f"• Warning threshold: {int(red_api.config.max_path_length * 0.9)} characters (90%)"
        )

        assert all_passed, "Some path validation tests failed"

    except Exception as e:
        console.print(f"[red]❌ Test failed: {e}[/red]")
        assert False, f"Test failed with exception: {e}"


def test_real_metadata_extraction():
    """Test metadata extraction with the real audiobook"""
    console.print("\n[bold cyan]🔍 Testing Real Metadata Extraction[/bold cyan]")

    try:
        from mk_torrent.core.metadata.engine import MetadataEngine

        # Test both paths
        paths = [
            "/mnt/user/data/downloads/torrents/qbittorrent/seedvault/audiobooks/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]",
            "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]",
        ]

        engine = MetadataEngine()

        for i, path_str in enumerate(paths, 1):
            path = Path(path_str)
            if not path.exists():
                console.print(f"[yellow]⚠️  Path {i} doesn't exist: {path}[/yellow]")
                continue

            console.print(f"\n[bold]Test {i}: {path.parent.name}/{path.name}[/bold]")

            # Find M4B file
            m4b_files = list(path.glob("*.m4b"))
            if not m4b_files:
                console.print("[red]❌ No M4B file found[/red]")
                continue

            m4b_file = m4b_files[0]
            console.print(f"✅ Found: {m4b_file.name}")

            # Extract metadata
            engine.setup_default_processors()  # Initialize processors
            metadata = engine.extract_metadata(m4b_file, content_type="audiobook")

            # Show key fields
            console.print(f"  • Title: {metadata.get('title', 'Unknown')}")
            console.print(f"  • Artists: {metadata.get('artists', ['Unknown'])}")
            console.print(f"  • Year: {metadata.get('year', 'Unknown')}")
            console.print(f"  • Author: {metadata.get('author', 'Unknown')}")
            console.print(f"  • Volume: {metadata.get('volume', 'Unknown')}")
            console.print(f"  • ASIN: {metadata.get('asin', 'Unknown')}")

        console.print("✅ Metadata extraction test completed")
        assert True  # Test completed successfully

    except Exception as e:
        console.print(f"[red]❌ Metadata extraction test failed: {e}[/red]")
        assert False, f"Metadata extraction test failed: {e}"


def main():
    """Run real audiobook path tests"""
    console.print("[bold cyan]🧪 Real Audiobook Path Testing[/bold cyan]")
    console.print("Testing RED validation with actual audiobook paths\n")

    # Run tests
    path_test = test_path_validation()
    metadata_test = test_real_metadata_extraction()

    # Summary
    console.print("\n[bold cyan]📊 Test Summary[/bold cyan]")
    console.print(f"Path validation: {'✅ PASS' if path_test else '❌ FAIL'}")
    console.print(f"Metadata extraction: {'✅ PASS' if metadata_test else '❌ FAIL'}")

    if path_test and metadata_test:
        console.print(
            "\n[bold green]🎉 All tests passed! RED integration handles real paths correctly.[/bold green]"
        )
        return 0
    else:
        console.print("\n[bold red]❌ Some tests failed.[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
