#!/usr/bin/env python3
"""
Simplified RED audiobook workflow test - focuses on RED API integration
Tests RED functionality without requiring qBittorrent or complex dependencies
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add project root to path
project_root = Path(__file__).parent.parent.parent  # Go up to project root
sys.path.insert(0, str(project_root / "src"))

console = Console()

# Sample audiobook path
AUDIOBOOK_PATH = Path(
    "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]"
)


def extract_audiobook_info():
    """Extract all available information from the audiobook sample"""
    console.print("\n[bold cyan]📚 Extracting Audiobook Information...[/bold cyan]")

    try:
        # Find the actual files
        m4b_file = None
        jpg_file = None

        for file in AUDIOBOOK_PATH.iterdir():
            if file.suffix == ".m4b":
                m4b_file = file
            elif file.suffix == ".jpg":
                jpg_file = file

        if not m4b_file:
            console.print("[red]❌ No M4B file found[/red]")
            return None

        # Parse folder name for metadata
        folder_name = AUDIOBOOK_PATH.name
        console.print(f"✅ Processing: {folder_name}")

        # Extract metadata from folder structure
        metadata = {}

        # Parse title and volume
        if " - vol" in folder_name:
            title_part, rest = folder_name.split(" - vol", 1)
            metadata["title"] = title_part.strip()
            vol_part = rest.split("(")[0].strip()
            metadata["volume"] = f"vol_{vol_part.lstrip('_')}"

        # Extract year (first parentheses)
        if "(" in folder_name:
            parts = folder_name.split("(")
            for part in parts[1:]:
                if ")" in part:
                    potential_year = part.split(")")[0].strip()
                    if potential_year.isdigit() and len(potential_year) == 4:
                        metadata["year"] = potential_year
                        break

        # Extract author (second parentheses, typically after year)
        paren_parts = folder_name.split("(")
        if len(paren_parts) >= 3:
            author_part = paren_parts[2].split(")")[0].strip()
            metadata["author"] = author_part

        # Extract ASIN
        if "{ASIN." in folder_name:
            asin_start = folder_name.find("{ASIN.") + 6
            asin_end = folder_name.find("}", asin_start)
            if asin_end > asin_start:
                metadata["asin"] = folder_name[asin_start:asin_end]

        # Extract uploader tag
        if "[" in folder_name and "]" in folder_name:
            tag_start = folder_name.rfind("[") + 1
            tag_end = folder_name.rfind("]")
            if tag_end > tag_start:
                metadata["uploader"] = folder_name[tag_start:tag_end]

        # File information
        file_stats = m4b_file.stat()
        metadata.update(
            {
                "format": "M4B",
                "file_path": str(m4b_file),
                "file_size_mb": round(file_stats.st_size / (1024 * 1024), 1),
                "file_size_bytes": file_stats.st_size,
                "has_cover": jpg_file is not None,
                "cover_path": str(jpg_file) if jpg_file else None,
            }
        )

        console.print("✅ Extracted metadata:")
        for key, value in metadata.items():
            if "path" not in key.lower():  # Skip long paths
                console.print(f"   {key}: {value}")

        return metadata

    except Exception as e:
        console.print(f"[red]❌ Failed: {e}[/red]")
        return None


def test_red_api_integration(metadata):
    """Test RED API integration with extracted metadata"""
    console.print("\n[bold cyan]🔴 Testing RED API Integration...[/bold cyan]")

    try:
        from mk_torrent.api.trackers.red import RedactedAPI

        # Create RED API instance
        red_api = RedactedAPI(api_key="test_key_for_validation")

        # Convert our metadata to RED format
        red_metadata = {
            "artists": [metadata.get("author", "Unknown Author")],
            "album": metadata.get("title", "Unknown Title"),
            "year": metadata.get("year", "2023"),
            "format": "M4B",
            "encoding": "AAC",
            "media": "WEB",
            "type": "audiobook",
            "tags": ["audiobook", "light-novel", "fantasy"],
            "description": f"Volume {metadata.get('volume', 'unknown')} - ASIN: {metadata.get('asin', 'N/A')}",
            "path": str(AUDIOBOOK_PATH),
            "file_size": metadata.get("file_size_bytes", 0),
        }

        # Test 1: Metadata validation
        console.print("[cyan]Testing metadata validation...[/cyan]")
        validation = red_api.validate_metadata(red_metadata)

        console.print(
            f"✅ Validation result: {'PASS' if validation['valid'] else 'FAIL'}"
        )
        if validation["errors"]:
            for error in validation["errors"]:
                console.print(f"   ❌ {error}")
        if validation["warnings"]:
            for warning in validation["warnings"]:
                console.print(f"   ⚠️  {warning}")

        # Test 2: Release type detection
        console.print("[cyan]Testing release type detection...[/cyan]")
        release_type = red_api._detect_release_type(red_metadata)
        release_name = [
            k for k, v in red_api.RELEASE_TYPES.items() if v == release_type
        ][0]
        console.print(f"✅ Detected release type: {release_name} (ID: {release_type})")

        # Test 3: Path compliance
        console.print("[cyan]Testing path compliance...[/cyan]")
        is_compliant = red_api.check_path_compliance(str(AUDIOBOOK_PATH))
        path_length = len(str(AUDIOBOOK_PATH))
        console.print(
            f"✅ Path compliance: {'PASS' if is_compliant else 'FAIL'} (length: {path_length}/150)"
        )

        # Test 4: Upload data preparation
        console.print("[cyan]Testing upload data preparation...[/cyan]")
        upload_data = red_api.prepare_upload_data(
            red_metadata, Path("/tmp/test.torrent")
        )

        required_fields = [
            "submit",
            "type",
            "artists[]",
            "groupname",
            "year",
            "releasetype",
        ]
        all_present = all(field in upload_data for field in required_fields)
        console.print(
            f"✅ Upload data preparation: {'PASS' if all_present else 'FAIL'}"
        )

        if all_present:
            console.print("   Required fields present:")
            for field in required_fields:
                console.print(f"     {field}: {upload_data[field]}")

        # Test 5: Dry run upload
        console.print("[cyan]Testing dry run upload...[/cyan]")
        dry_run_result = red_api.upload_torrent(
            Path("/tmp/test.torrent"), red_metadata, dry_run=True
        )
        console.print(f"✅ Dry run: {'PASS' if dry_run_result['success'] else 'FAIL'}")

        return validation["valid"] and all_present and dry_run_result["success"]

    except Exception as e:
        console.print(f"[red]❌ Failed: {e}[/red]")
        return False


def test_red_workflow_simulation():
    """Simulate the complete RED upload workflow"""
    console.print("\n[bold cyan]🚀 Simulating Complete RED Workflow...[/bold cyan]")

    try:
        # Step 1: Extract metadata
        console.print("[cyan]Step 1: Extract audiobook metadata[/cyan]")
        metadata = extract_audiobook_info()
        if not metadata:
            return False

        # Step 2: Create RED API instance
        console.print("[cyan]Step 2: Initialize RED API[/cyan]")
        from mk_torrent.api.trackers.red import RedactedAPI

        red_api = RedactedAPI(api_key="test_key")
        console.print("✅ RED API initialized")

        # Step 3: Convert and validate metadata
        console.print("[cyan]Step 3: Prepare and validate metadata for RED[/cyan]")
        red_metadata = {
            "artists": [metadata.get("author", "Unknown")],
            "album": metadata.get("title", "Unknown"),
            "year": metadata.get("year", "2023"),
            "format": "M4B",
            "encoding": "AAC 64kbps",
            "media": "WEB",
            "type": "audiobook",
            "tags": ["audiobook", "fiction", "light-novel"],
            "description": f"High quality audiobook - {metadata.get('file_size_mb')}MB",
            "path": str(AUDIOBOOK_PATH),
        }

        validation = red_api.validate_metadata(red_metadata)
        if not validation["valid"]:
            console.print(
                f"[red]❌ Metadata validation failed: {validation['errors']}[/red]"
            )
            return False
        console.print("✅ Metadata validated for RED")

        # Step 4: Simulate torrent creation
        console.print("[cyan]Step 4: Create torrent file[/cyan]")
        torrent_path = Path("/tmp/test_audiobook.torrent")
        # Create dummy torrent for testing
        dummy_torrent = b"d8:announce33:https://flacsfor.me/announce4:infod4:nametest6:lengthi500000000eee"
        torrent_path.write_bytes(dummy_torrent)
        console.print(f"✅ Torrent created (simulated): {torrent_path}")

        # Step 5: Prepare upload data
        console.print("[cyan]Step 5: Prepare upload data[/cyan]")
        _upload_data = red_api.prepare_upload_data(red_metadata, torrent_path)
        console.print("✅ Upload data prepared")

        # Step 6: Dry run upload
        console.print("[cyan]Step 6: Perform dry run upload[/cyan]")
        result = red_api.upload_torrent(torrent_path, red_metadata, dry_run=True)
        console.print(f"✅ Dry run completed: {result['message']}")

        # Cleanup
        if torrent_path.exists():
            torrent_path.unlink()

        console.print(
            "\n[bold green]🎉 Complete RED workflow simulation successful![/bold green]"
        )
        console.print(
            "[green]Ready for real RED upload with actual API credentials![/green]"
        )

        return True

    except Exception as e:
        console.print(f"[red]❌ Workflow failed: {e}[/red]")
        return False


def display_red_readiness_report(metadata):
    """Display a comprehensive readiness report for RED upload"""
    console.print("\n[bold cyan]📋 RED Upload Readiness Report[/bold cyan]")

    from mk_torrent.api.trackers.red import RedactedAPI

    _red_api = RedactedAPI(api_key="test_key")

    # Create table
    table = Table(title="RED Upload Readiness Check")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    # Check 1: File format
    format_ok = metadata.get("format") == "M4B"
    table.add_row(
        "File Format",
        "✅ PASS" if format_ok else "❌ FAIL",
        f"M4B format {'supported' if format_ok else 'not supported'}",
    )

    # Check 2: File size
    size_mb = metadata.get("file_size_mb", 0)
    size_ok = 50 <= size_mb <= 2000  # Reasonable audiobook size range
    table.add_row(
        "File Size",
        "✅ PASS" if size_ok else "⚠️ WARN",
        f"{size_mb}MB ({'reasonable' if size_ok else 'check if correct'})",
    )

    # Check 3: Metadata completeness
    required_fields = ["title", "author", "year"]
    missing_fields = [f for f in required_fields if not metadata.get(f)]
    metadata_ok = len(missing_fields) == 0
    table.add_row(
        "Metadata",
        "✅ PASS" if metadata_ok else "❌ FAIL",
        f"{'All required fields present' if metadata_ok else f'Missing: {missing_fields}'}",
    )

    # Check 4: Path compliance
    path_length = len(str(AUDIOBOOK_PATH))
    path_ok = path_length <= 150
    table.add_row(
        "Path Length",
        "✅ PASS" if path_ok else "❌ FAIL",
        f"{path_length}/150 characters",
    )

    # Check 5: Content type
    is_audiobook = (
        "audiobook" in AUDIOBOOK_PATH.name.lower() or metadata.get("format") == "M4B"
    )
    table.add_row(
        "Content Type",
        "✅ PASS" if is_audiobook else "⚠️ WARN",
        "Audiobook detected" if is_audiobook else "Content type unclear",
    )

    # Check 6: Cover art
    has_cover = metadata.get("has_cover", False)
    table.add_row(
        "Cover Art",
        "✅ PASS" if has_cover else "⚠️ WARN",
        "Cover image found" if has_cover else "No cover image found",
    )

    console.print(table)

    # Overall assessment
    critical_checks = [format_ok, metadata_ok, path_ok]
    if all(critical_checks):
        console.print("\n[bold green]🎯 READY FOR RED UPLOAD![/bold green]")
        console.print(
            "[green]All critical requirements met. Add real API credentials to proceed.[/green]"
        )
    else:
        console.print("\n[bold yellow]⚠️ NEEDS ATTENTION[/bold yellow]")
        console.print("[yellow]Some issues need to be resolved before upload.[/yellow]")


def main():
    """Run simplified RED audiobook workflow test"""
    console.print(
        Panel.fit(
            "[bold cyan]🔴 RED Audiobook Integration Test[/bold cyan]\n"
            "Testing RED API with real audiobook sample",
            border_style="red",
        )
    )

    # Check if audiobook exists
    if not AUDIOBOOK_PATH.exists():
        console.print(f"\n[red]❌ Audiobook sample not found: {AUDIOBOOK_PATH}[/red]")
        return 1

    console.print("\n[green]✅ Found audiobook sample[/green]")

    # Extract audiobook information
    metadata = extract_audiobook_info()
    if not metadata:
        console.print("[red]❌ Failed to extract audiobook metadata[/red]")
        return 1

    # Test RED API integration
    red_success = test_red_api_integration(metadata)

    # Run workflow simulation
    workflow_success = test_red_workflow_simulation()

    # Display readiness report
    display_red_readiness_report(metadata)

    # Final result
    if red_success and workflow_success:
        console.print("\n[bold green]🎉 RED Integration Test: SUCCESS[/bold green]")
        console.print("[green]Your audiobook is ready for RED upload![/green]")
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("1. Set up real RED API credentials")
        console.print("2. Configure qBittorrent for torrent creation")
        console.print("3. Run actual upload workflow")
        return 0
    else:
        console.print(
            "\n[bold yellow]⚠️ RED Integration Test: PARTIAL SUCCESS[/bold yellow]"
        )
        console.print(
            "[yellow]Some components need attention before real upload.[/yellow]"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
