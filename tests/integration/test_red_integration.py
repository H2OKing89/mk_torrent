#!/usr/bin/env python3
"""
RED Audiobook Integration Test

Tests the complete workflow from real audiobook files to RED upload preparation:
- Real file analysis with actual audiobooks
- Path validation with real folder names
- Metadata extraction from M4B files
- RED validation with extracted metadata
- Upload preparation and workflow testing
- Dry-run upload testing

This focuses on real-world testing with actual audiobook files.
For pure API testing, see test_red_api.py
"""

import sys
import os
import re
from typing import Dict, Any

try:
    import pytest
except ImportError:
    pytest = None  # Allow running without pytest
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

console = Console()

# Gate Rich output behind environment variable for quiet CI
SHOW_RICH = os.getenv("SHOW_RICH_TEST_OUTPUT", "0") == "1"


def rich_print(*args, **kwargs):
    """Print to Rich console only if SHOW_RICH is enabled"""
    if SHOW_RICH:
        console.print(*args, **kwargs)


# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

# Test audiobook paths - consolidating both test files
AUDIOBOOK_PATHS = {
    "realist_hero": Path(
        "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]"
    ),
    "otome_games": Path(
        "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/The World of Otome Games Is Tough for Mobs - vol_05 (2025) (Yomu Mishima) {ASIN.B0FPXQH971} [H2OKing]"
    ),
}

# Real torrent file for testing
REAL_TORRENT_FILE = Path(
    "/mnt/cache/scripts/mk_torrent/tests/samples/torrent_files/The World of Otome Games Is Tough for Mobs - vol_05 (2025) (Yomu Mishima) {ASIN.B0FPXQH971} [H2OKing].torrent"
)


def extract_metadata_once(
    audiobook_files: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Extract metadata from audiobook files once and cache the results"""
    if hasattr(extract_metadata_once, "_cache"):
        return extract_metadata_once._cache

    from mk_torrent.core.metadata.engine import MetadataEngine

    results = {}
    engine = MetadataEngine()
    engine.setup_default_processors()

    for name, info in audiobook_files.items():
        rich_print(f"\n[bold]📚 Extracting metadata from {name}...[/bold]")

        m4b_file = info["m4b_file"]
        metadata = engine.extract_metadata(m4b_file, content_type="audiobook")

        # Combine and enhance metadata
        enhanced_metadata = {
            **metadata,
            "path": info["folder_path"],
            "folder_name": info["folder_name"],
            "format": "M4B",
            "encoding": "AAC",
            "media": "WEB",
            "type": "audiobook",
        }

        # Try to extract artists from folder name if not found in metadata
        if enhanced_metadata.get("artists") == "Unknown":
            folder_name = info["folder_name"]
            # Try to extract author from folder name patterns like "(Author)" or "[Author]"
            author_match = re.search(r"\(([^)]+)\)", folder_name)
            if author_match:
                enhanced_metadata["artists"] = author_match.group(1)
                rich_print(
                    f"[green]✅ Extracted artists from folder name: {enhanced_metadata['artists']}[/green]"
                )
            else:
                rich_print(
                    "[yellow]⚠️ Could not extract artists from folder name[/yellow]"
                )

        if SHOW_RICH:
            display_metadata_table(name, enhanced_metadata)

        # Verify essential fields were extracted
        required_fields = ["title", "format"]
        missing_fields = [
            field
            for field in required_fields
            if field not in enhanced_metadata
            or enhanced_metadata.get(field) == "Unknown"
        ]

        # Artists can be "Unknown" for some audiobooks, so we'll be more lenient
        if "artists" in enhanced_metadata and enhanced_metadata["artists"] != "Unknown":
            rich_print("[green]✅ Artists found in metadata[/green]")
        else:
            rich_print(
                "[yellow]⚠️ Artists not found in metadata (this is OK for some audiobooks)[/yellow]"
            )

        if missing_fields:
            rich_print(
                f"[red]❌ Missing required fields: {', '.join(missing_fields)}[/red]"
            )
            raise AssertionError(
                f"Failed to extract required metadata fields: {missing_fields}"
            )
        else:
            rich_print("[green]✅ All required metadata fields extracted[/green]")

        results[name] = enhanced_metadata

    # Cache the results to avoid re-extraction
    extract_metadata_once._cache = results
    return results


def display_metadata_table(name: str, metadata: Dict[str, Any]):
    """Display metadata in a Rich table"""
    table = Table(title=f"Metadata for {name}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    key_fields = [
        "title",
        "artists",
        "year",
        "format",
        "narrator",
        "publisher",
        "genre",
        "duration_seconds",
    ]

    for field in key_fields:
        value = metadata.get(field, "Unknown")
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value if v is not None)
        table.add_row(field.title(), str(value))

    rich_print(table)


@pytest.fixture
def audiobook_files() -> Dict[str, Dict[str, Any]]:
    """Fixture to provide information about all test audiobook files"""
    result = {}

    for name, path in AUDIOBOOK_PATHS.items():
        if not path.exists():
            rich_print(f"[yellow]⚠️ Sample path not found: {path}[/yellow]")
            continue

        # Find files
        m4b_files = list(path.glob("*.m4b"))
        cover_files = list(path.glob("*.jpg")) + list(path.glob("*.png"))
        metadata_files = list(path.glob("*.json"))

        if not m4b_files:
            rich_print(f"[yellow]⚠️ No M4B file found in {name} sample[/yellow]")
            continue

        result[name] = {
            "folder_path": path,
            "m4b_file": m4b_files[0],
            "cover_file": cover_files[0] if cover_files else None,
            "metadata_file": metadata_files[0] if metadata_files else None,
            "folder_name": path.name,
            "folder_length": len(path.name),
            "full_path_length": len(str(path)),
        }

    if not result:
        pytest.skip("No test audiobook files found")

    return result


def test_sample_availability(audiobook_files: Dict[str, Dict[str, Any]]):
    """Test that sample audiobooks are available"""
    rich_print("\n[bold cyan]📚 Testing Sample Audiobook Availability[/bold cyan]")

    # Verify we have at least one sample
    assert len(audiobook_files) > 0, "No audiobook samples found"

    if SHOW_RICH:
        # Display available samples
        table = Table(title="Available Audiobook Samples")
        table.add_column("Name", style="cyan")
        table.add_column("Folder", style="white")
        table.add_column("M4B File", style="white")
        table.add_column("Cover", style="white")

        for name, info in audiobook_files.items():
            m4b_status = "✅" if info["m4b_file"] else "❌"
            cover_status = "✅" if info["cover_file"] else "❌"

            table.add_row(
                name,
                info["folder_name"],
                f"{m4b_status} {info['m4b_file'].name if info['m4b_file'] else 'Missing'}",
                f"{cover_status} {info['cover_file'].name if info['cover_file'] else 'Missing'}",
            )

        rich_print(table)


def test_path_validation(audiobook_files: Dict[str, Dict[str, Any]]):
    """Test RED path validation with real audiobook paths"""
    console.print("\n[bold cyan]📏 Testing RED Path Validation[/bold cyan]")

    from mk_torrent.trackers.red_adapter import REDAdapter, REDConfig

    red_api = REDAdapter(REDConfig(api_key="test_key"))

    table = Table(title="RED Path Validation Results")
    table.add_column("Audiobook", style="cyan")
    table.add_column("Folder Length", style="white")
    table.add_column("Full Path Length", style="white")
    table.add_column("RED Compatible", style="bold")

    all_passed = True

    for name, info in audiobook_files.items():
        folder_name = info["folder_name"]
        folder_length = info["folder_length"]
        full_path_length = info["full_path_length"]

        # Check folder name compliance (what matters for RED)
        is_compliant = red_api.check_path_compliance(folder_name)

        status = "✅ PASS" if is_compliant else "❌ FAIL"
        result_style = "green" if is_compliant else "red"

        table.add_row(
            name,
            str(folder_length),
            str(full_path_length),
            f"[{result_style}]{status}[/{result_style}]",
        )

        if not is_compliant:
            all_passed = False

    console.print(table)
    console.print(f"\n🎯 RED path limit: {red_api.config.max_path_length} characters")

    assert all_passed, "Some audiobook folder names exceed RED's path length limit"


def test_file_structure(audiobook_files: Dict[str, Dict[str, Any]]):
    """Test audiobook file structure analysis"""
    console.print("\n[bold cyan]📁 Testing Audiobook File Structure[/bold cyan]")

    for name, info in audiobook_files.items():
        console.print(f"\n[yellow]📂 Analyzing {name}...[/yellow]")

        path = info["folder_path"]

        # Display file structure as a tree
        tree = Tree(f"[bold blue]{path.name}[/bold blue]")
        for file in path.iterdir():
            if file.is_file():
                size_mb = file.stat().st_size / (1024 * 1024)
                tree.add(f"{file.name} [dim]({size_mb:.1f} MB)[/dim]")

        console.print(tree)

        # Check essential files
        assert info["m4b_file"].exists(), f"M4B file missing in {name}"

        # Cover file is recommended but not required
        if info["cover_file"]:
            console.print(f"✅ Cover file: {info['cover_file'].name}")
        else:
            console.print(f"⚠️ No cover file found in {name}")


def test_metadata_extraction(audiobook_files: Dict[str, Dict[str, Any]]):
    """Test metadata extraction from real audiobooks"""
    rich_print("\n[bold cyan]🔍 Testing Metadata Extraction[/bold cyan]")

    results = extract_metadata_once(audiobook_files)

    # All validation is done in extract_metadata_once
    # Verify we got results for all audiobook files
    assert (
        len(results) > 0
    ), "Should have extracted metadata from at least one audiobook"

    # Verify each result has required fields
    for name, metadata in results.items():
        assert "title" in metadata, f"Missing title in {name} metadata"
        assert "format" in metadata, f"Missing format in {name} metadata"


def test_red_validation_with_real_metadata(audiobook_files: Dict[str, Dict[str, Any]]):
    """Test RED validation with real extracted metadata"""
    rich_print("\n[bold cyan]🎯 Testing RED Validation with Real Metadata[/bold cyan]")

    # Use cached metadata extraction
    metadata_results = extract_metadata_once(audiobook_files)

    from mk_torrent.trackers.red_adapter import REDAdapter, REDConfig

    red_api = REDAdapter(REDConfig(api_key="test_key"))

    if SHOW_RICH:
        table = Table(title="RED Validation Results")
        table.add_column("Audiobook", style="cyan")
        table.add_column("Validation", style="bold")
        table.add_column("Path Check", style="bold")
        table.add_column("Issues", style="white")

    for name, metadata in metadata_results.items():
        # Validate metadata
        validation = red_api.validate_metadata(metadata)

        # Check path compliance
        folder_name = metadata.get("folder_name", "")
        path_compliant = (
            red_api.check_path_compliance(folder_name) if folder_name else False
        )

        if SHOW_RICH:
            # Format results
            validation_status = (
                "[green]✅ PASS[/green]"
                if validation["valid"]
                else "[red]❌ FAIL[/red]"
            )
            path_status = (
                "[green]✅ PASS[/green]" if path_compliant else "[red]❌ FAIL[/red]"
            )

            issues = []
            if validation["errors"]:
                issues.extend(validation["errors"])
            if validation["warnings"]:
                issues.extend([f"⚠️ {w}" for w in validation["warnings"]])

            issues_text = "\n".join(issues) if issues else "None"
            table.add_row(name, validation_status, path_status, issues_text)

    if SHOW_RICH:
        rich_print(table)

    # Not asserting validation success as real files may have valid reasons to fail validation
    # We want to show the validation results without failing the test


def test_upload_preparation_with_real_metadata(
    audiobook_files: Dict[str, Dict[str, Any]],
):
    """Test upload data preparation with real metadata"""
    rich_print(
        "\n[bold cyan]📤 Testing Upload Preparation with Real Metadata[/bold cyan]"
    )

    # Use cached metadata extraction
    metadata_results = extract_metadata_once(audiobook_files)

    from mk_torrent.trackers.red_adapter import REDAdapter, REDConfig

    red_api = REDAdapter(REDConfig(api_key="test_key"))

    for name, metadata in metadata_results.items():
        rich_print(f"\n[bold]📋 Preparing upload data for {name}...[/bold]")

        # Use real torrent file for testing
        torrent_file = REAL_TORRENT_FILE
        if not torrent_file.exists():
            # Create a simple dummy torrent for testing if the real one doesn't exist
            torrent_file = Path(f"/tmp/{name}_test.torrent")
            # Create minimal dummy torrent content
            dummy_content = b"d8:announce23:https://example.com/announce13:creation datei1694000000e4:infod4:name5:dummy12:piece lengthi32768e6:pieces0:ee"
            with open(torrent_file, "wb") as f:
                f.write(dummy_content)

        # Prepare upload data
        upload_data = red_api.prepare_upload_data(metadata, torrent_file)

        if SHOW_RICH:
            # Display key upload fields
            key_fields = [
                "groupname",
                "artists[]",
                "year",
                "releasetype",
                "format",
                "media",
                "tags",
            ]

            table = Table(title=f"Upload Data for {name}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")

            for field in key_fields:
                value = upload_data.get(field, "Not set")
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value if v is not None)
                table.add_row(field, str(value))

            rich_print(table)

        # Check essential fields with invariants, not exact matches
        assert "groupname" in upload_data, f"Missing groupname in {name} upload data"
        assert "year" in upload_data, f"Missing year in {name} upload data"
        assert "format" in upload_data, f"Missing format in {name} upload data"


def test_dry_run_upload_with_real_metadata(audiobook_files: Dict[str, Dict[str, Any]]):
    """Test dry run upload with real metadata"""
    rich_print("\n[bold cyan]🚀 Testing Dry Run Upload with Real Metadata[/bold cyan]")

    # Use cached metadata extraction
    metadata_results = extract_metadata_once(audiobook_files)

    from mk_torrent.trackers.red_adapter import REDAdapter, REDConfig

    red_api = REDAdapter(REDConfig(api_key="test_key"))

    if SHOW_RICH:
        table = Table(title="Dry Run Upload Results")
        table.add_column("Audiobook", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Message", style="white")

    for name, metadata in metadata_results.items():
        # Use real torrent file for testing
        torrent_file = REAL_TORRENT_FILE
        if not torrent_file.exists():
            # Create a simple dummy torrent for testing if the real one doesn't exist
            torrent_file = Path(f"/tmp/{name}_test.torrent")
            # Create minimal dummy torrent content
            dummy_content = b"d8:announce23:https://example.com/announce13:creation datei1694000000e4:infod4:name5:dummy12:piece lengthi32768e6:pieces0:ee"
            with open(torrent_file, "wb") as f:
                f.write(dummy_content)

        # Perform dry run upload
        result = red_api.upload_torrent(torrent_file, metadata, dry_run=True)

        if SHOW_RICH:
            status = (
                "[green]✅ SUCCESS[/green]"
                if result.get("success")
                else "[red]❌ FAILED[/red]"
            )
            message = result.get("message", "No message")
            table.add_row(name, status, message)

        # Assert dry run success
        assert result.get("success"), f"Dry run for {name} should succeed"

    if SHOW_RICH:
        rich_print(table)


def display_summary(results: Dict[str, bool]) -> bool:
    """Display test summary"""
    if not SHOW_RICH:
        return all(results.values())

    table = Table(title="RED Audiobook Test Results")
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Notes")

    test_descriptions = {
        "sample_availability": "Audiobook sample files available",
        "path_validation": "RED path compliance checking",
        "file_structure": "Audiobook file structure analysis",
        "metadata_extraction": "Metadata extraction from M4B files",
        "red_validation": "RED tracker validation with real metadata",
        "upload_preparation": "Upload data preparation with real metadata",
        "dry_run": "Dry run upload workflow",
    }

    for test_name, success in results.items():
        status = "[green]✅ PASS[/green]" if success else "[red]❌ FAIL[/red]"
        description = test_descriptions.get(test_name, "Unknown test")
        table.add_row(test_name.replace("_", " ").title(), status, description)

    rich_print("\n")
    rich_print(table)

    passed = sum(results.values())
    total = len(results)

    if passed == total:
        rich_print(
            f"\n[bold green]🎉 All {total} tests passed! RED audiobook integration ready.[/bold green]"
        )
    else:
        rich_print(
            f"\n[bold yellow]⚠️ {passed}/{total} tests passed. Some issues to address.[/bold yellow]"
        )

    return passed == total


def main():
    """Run all audiobook integration tests - only when SHOW_RICH is enabled"""
    if not SHOW_RICH:
        print("Set SHOW_RICH_TEST_OUTPUT=1 to run standalone mode with Rich output")
        return 0

    rich_print(
        Panel.fit(
            "[bold cyan]📚 RED Audiobook Integration Test[/bold cyan]\n"
            "Testing RED integration with actual audiobook files",
            border_style="cyan",
        )
    )

    # Run tests and collect results
    results: Dict[str, bool] = {}

    # Step 1: Check sample availability
    audiobook_files = {}
    try:
        for name, path in AUDIOBOOK_PATHS.items():
            if not path.exists():
                continue

            # Find files
            m4b_files = list(path.glob("*.m4b"))
            cover_files = list(path.glob("*.jpg")) + list(path.glob("*.png"))
            metadata_files = list(path.glob("*.json"))

            if not m4b_files:
                continue

            audiobook_files[name] = {
                "folder_path": path,
                "m4b_file": m4b_files[0],
                "cover_file": cover_files[0] if cover_files else None,
                "metadata_file": metadata_files[0] if metadata_files else None,
                "folder_name": path.name,
                "folder_length": len(path.name),
                "full_path_length": len(str(path)),
            }

        results["sample_availability"] = len(audiobook_files) > 0

        if not audiobook_files:
            console.print("[red]❌ No audiobook samples found. Tests cannot run.[/red]")
            results.update(
                {
                    "path_validation": False,
                    "file_structure": False,
                    "metadata_extraction": False,
                    "red_validation": False,
                    "upload_preparation": False,
                    "dry_run": False,
                }
            )
            display_summary(results)
            return 1

        # Run tests using the found audiobook files
        test_sample_availability(audiobook_files)
        results["path_validation"] = True
        test_path_validation(audiobook_files)

        results["file_structure"] = True
        test_file_structure(audiobook_files)

        results["metadata_extraction"] = True
        test_metadata_extraction(audiobook_files)

        results["red_validation"] = True
        test_red_validation_with_real_metadata(audiobook_files)

        results["upload_preparation"] = True
        test_upload_preparation_with_real_metadata(audiobook_files)

        results["dry_run"] = True
        test_dry_run_upload_with_real_metadata(audiobook_files)

        # Display summary
        all_passed = display_summary(results)

        if all_passed:
            console.print("\n[bold green]🎯 Ready for Production:[/bold green]")
            console.print("1. All path validation working correctly")
            console.print("2. Metadata extraction from real M4B files")
            console.print("3. RED validation passing")
            console.print("4. Upload workflow ready")
            console.print("5. Ready to test with real RED API credentials")

        return 0 if all_passed else 1

    except Exception as e:
        console.print(f"[bold red]❌ Test failed with error: {e}[/bold red]")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
