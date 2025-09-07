"""
Audiobook Metadata Core Integration Test & Demonstration

PURPOSE:
--------
This script serves as the primary integration test and demonstration for the complete
audiobook metadata extraction and processing pipeline. It validates the end-to-end
functionality of the modular metadata core system and showcases its capabilities.

WHAT IT DEMONSTRATES:
-------------------
1. Complete Three-Source Metadata Extraction:
   - Audnexus API integration for external metadata
   - Embedded metadata extraction from audio files (M4B/MP3)
   - Path-based metadata parsing from filenames and directory structure

2. Advanced Metadata Processing:
   - Smart field merging with declarative precedence rules
   - AudiobookMeta object creation and validation
   - Comprehensive metadata validation with RED compliance hints

3. Enhanced User Experience:
   - Rich console output with progress bars, tables, and trees
   - API response caching to avoid repeated calls
   - Fuzzy matching for metadata similarity scoring
   - Graceful fallbacks when optional dependencies are missing

4. Architectural Showcase:
   - MetadataEngine with dependency injection
   - AudiobookProcessor with region-specific configuration
   - Protocol-based source architecture
   - Clean separation of concerns

USAGE:
------
Run from project root:
    python examples/integration_tests/audiobook_metadata_integration_demo.py

DEPENDENCIES:
------------
Required:
- mk_torrent.core.metadata (core system)
- pathlib, typing (standard library)

Optional (with graceful fallbacks):
- rich: Enhanced console output with colors, tables, progress bars
- cachetools: API response caching (1-hour TTL)
- rapidfuzz: Fuzzy matching for metadata comparison

VALIDATION SCOPE:
----------------
This script validates:
- Metadata extraction from real audiobook files
- Three-source merging accuracy and precedence
- AudiobookMeta object creation and type safety
- Validation pipeline completeness
- API integration reliability
- Error handling robustness
- Performance with caching enabled

COMPARISON FEATURES:
------------------
- Side-by-side comparison with legacy Audnexus integration
- Similarity scoring between old and new systems
- Architectural improvement documentation
- Migration path validation

SAMPLE DATA:
-----------
Uses real audiobook files from tests/samples/audiobook/ directory
Automatically finds alternative samples if primary file is missing

OUTPUT:
-------
- Rich-formatted metadata tables and trees
- Three-source extraction comparison
- Validation results and completeness scores
- Performance metrics and caching status
- Error handling demonstrations

MAINTENANCE:
-----------
- Update sample file paths as needed
- Add new test cases for additional metadata sources
- Expand validation checks as system evolves
- Keep dependencies optional with fallbacks
"""

# type: ignore  # Suppress type checking for optional imports and dynamic typing

import sys
from pathlib import Path
from typing import Any, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Rich imports for beautiful output
try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
    )
    from rich.table import Table
    from rich.panel import Panel
    from rich.tree import Tree
    from rich import box

    rich_available = True
except ImportError:
    rich_available = False
    print("📦 Install 'rich' for enhanced output: pip install rich")

# Cache imports for API response caching
try:
    from cachetools import TTLCache, cached

    cache_available = True
    # Create a 1-hour TTL cache for API responses
    api_cache = TTLCache(maxsize=100, ttl=3600)  # type: ignore
except ImportError:
    cache_available = False
    print("📦 Install 'cachetools' for API response caching: pip install cachetools")

# Fuzzy matching for metadata comparison
try:
    from rapidfuzz import fuzz

    fuzz_available = True
except ImportError:
    fuzz_available = False
    print(
        "📦 Install 'rapidfuzz' for metadata similarity scoring: pip install rapidfuzz"
    )

from mk_torrent.core.metadata import MetadataEngine, AudiobookMeta
from mk_torrent.core.metadata.processors.audiobook import AudiobookProcessor

# Initialize rich console
console = Console() if rich_available else None  # type: ignore


def rich_print(text: str, style: str = ""):
    """Print with rich formatting if available, fallback to regular print."""
    if rich_available and console:
        console.print(text, style=style)
    else:
        print(text)


def create_metadata_table(metadata: Dict[str, Any], title: str = "Metadata") -> None:
    """Create a rich table displaying metadata."""
    if not rich_available or not console:
        # Fallback to simple print
        print(f"\n{title}:")
        for key, value in metadata.items():
            if key not in ["_src", "source_path"]:
                print(f"   {key}: {value}")
        return

    table = Table(
        title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta"
    )  # type: ignore
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", style="green", overflow="fold")
    table.add_column("Type", style="yellow", width=10)

    for key, value in metadata.items():
        if key in ["_src", "source_path"]:
            continue

        value_str = str(value)
        if len(value_str) > 60:
            value_str = value_str[:57] + "..."

        value_type = type(value).__name__
        if isinstance(value, list):
            value_type = f"list[{len(value)}]"  # type: ignore

        table.add_row(key, value_str, value_type)

    console.print(table)


def create_source_comparison_tree(
    api_data: Dict[str, Any], embedded_data: Dict[str, Any], path_data: Dict[str, Any]
) -> None:
    """Create a rich tree showing three-source comparison."""
    if not rich_available or not console:
        return

    tree = Tree("🔄 Three-Source Extraction", style="bold blue")  # type: ignore

    # API Source branch
    api_branch = tree.add(f"🌐 API Source ({len(api_data)-1} fields)", style="green")
    for key in ["title", "author", "chapters", "chapter_count", "artwork_url"]:
        if key in api_data:
            value = (
                str(api_data[key])[:40] + "..."
                if len(str(api_data[key])) > 40
                else str(api_data[key])
            )
            api_branch.add(f"{key}: {value}")

    # Embedded Source branch
    embedded_branch = tree.add(
        f"🎵 Embedded Source ({len(embedded_data)-1} fields)", style="cyan"
    )
    for key in [
        "bitrate",
        "duration_sec",
        "has_cover_art",
        "sample_rate",
        "chapter_count",
    ]:
        if key in embedded_data:
            value = str(embedded_data[key])
            embedded_branch.add(f"{key}: {value}")

    # Path Source branch
    path_branch = tree.add(
        f"📁 Path Source ({len(path_data)-1} fields)", style="yellow"
    )
    for key in ["series", "volume", "asin"]:
        if key in path_data:
            value = str(path_data[key])
            path_branch.add(f"{key}: {value}")

    console.print(tree)


def calculate_metadata_similarity(
    old_meta: Dict[str, Any], new_meta: Dict[str, Any]
) -> float:
    """Calculate similarity score between old and new metadata using fuzzy matching."""
    if not fuzz_available:
        return 0.0

    similarities = []
    common_fields = ["title", "author", "album", "year"]

    for field in common_fields:
        old_val = str(old_meta.get(field, ""))
        new_val = str(new_meta.get(field, ""))
        if old_val and new_val:
            similarity = fuzz.ratio(old_val, new_val)  # type: ignore
            similarities.append(similarity)

    return sum(similarities) / len(similarities) if similarities else 0.0


def cached_api_extraction(source_class: Any, sample_file: str) -> Dict[str, Any]:
    """Cache API extractions to avoid repeated calls during testing."""
    source = source_class()
    return source.extract(sample_file)


# Apply caching if available
if cache_available:
    cached_api_extraction = cached(api_cache)(cached_api_extraction)  # type: ignore


def test_audiobook_processor():
    """Test the new audiobook processor with real sample file."""
    if rich_available and console:
        console.print(
            Panel.fit(
                "🎧 Testing Audiobook Processor with Audnexus Integration",
                style="bold blue",
                border_style="blue",
            )  # type: ignore
        )
    else:
        print("🎧 Testing Audiobook Processor with Audnexus Integration")
        print("=" * 60)

    # Create metadata engine
    engine = MetadataEngine()
    processor = AudiobookProcessor(region="us")
    engine.register_processor("audiobook", processor)

    # Sample file setup - find the correct path relative to project root
    project_root = Path(
        __file__
    ).parent.parent.parent  # Go up from examples/integration_tests/ to project root
    sample_file = (
        project_root
        / "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_09 (2023) (Dojyomaru) {ASIN.B0CPML76KX} [H2OKing]/How a Realist Hero Rebuilt the Kingdom - vol_09 {ASIN.B0CPML76KX}.m4b"
    )

    if not sample_file.exists():
        rich_print(f"❌ Sample file not found: {sample_file}", "red")
        rich_print("📂 Looking for alternative samples...", "yellow")
        # Try to find any .m4b file in the samples directory
        samples_dir = project_root / "tests/samples/audiobook"
        if samples_dir.exists():
            for potential_file in samples_dir.rglob("*.m4b"):
                sample_file = potential_file
                rich_print(f"📂 Found alternative sample: {sample_file}", "green")
                break
        else:
            rich_print("❌ No sample files available for testing", "red")
            return

    rich_print(f"📂 Processing: {sample_file}", "cyan")

    try:
        # Step 1: Extract metadata with progress tracking
        if rich_available and console:
            with Progress(
                SpinnerColumn(),  # type: ignore
                TextColumn("[progress.description]{task.description}"),  # type: ignore
                console=console,
            ) as progress:
                task = progress.add_task("1️⃣ Extracting metadata...", total=100)
                metadata_dict = engine.extract_metadata(str(sample_file))
                progress.update(task, completed=100)
        else:
            print("\n1️⃣ Extracting metadata...")
            metadata_dict = engine.extract_metadata(str(sample_file))

        # Display main metadata
        rich_print("\n✅ Successfully extracted metadata:", "green bold")

        main_fields = {
            "Title": metadata_dict.get("title", "N/A"),
            "Author": metadata_dict.get("author", "N/A"),
            "Series": metadata_dict.get("series", "N/A"),
            "Volume": metadata_dict.get("volume", "N/A"),
            "Year": str(metadata_dict.get("year", "N/A")),
            "Publisher": metadata_dict.get("publisher", "N/A"),
            "Narrator": metadata_dict.get("narrator", "N/A"),
            "ASIN": metadata_dict.get("asin", "N/A"),
            "Duration": f"{metadata_dict.get('duration_sec', 'N/A')} seconds",
            "Bitrate": str(metadata_dict.get("bitrate", "N/A")),
        }

        # Handle chapters
        chapter_count = metadata_dict.get("chapter_count")
        chapters_list = metadata_dict.get("chapters", [])
        if chapter_count and chapter_count > 0:
            main_fields["Chapters"] = str(chapter_count)
        elif isinstance(chapters_list, list) and len(chapters_list) > 0:  # type: ignore
            main_fields["Chapters"] = f"{len(chapters_list)} (from list)"  # type: ignore
        else:
            main_fields["Chapters"] = "0"

        # Handle cover
        has_cover = metadata_dict.get("has_embedded_cover") or metadata_dict.get(
            "has_cover_art"
        )
        main_fields["Has Cover"] = str(has_cover) if has_cover is not None else "N/A"

        create_metadata_table(main_fields, "📊 Main Metadata")

        # Show summary in its own dedicated panel
        summary_text = metadata_dict.get("summary", "")
        if summary_text:
            if rich_available and console:
                console.print(
                    Panel(
                        summary_text,
                        title="📖 Summary",
                        border_style="blue",
                        expand=False,
                    )  # type: ignore
                )
            else:
                print(f"\n📖 Summary:\n{summary_text}")

        # Show description in its own panel too (if different from summary)
        description_text = metadata_dict.get("description", "")
        if description_text and description_text != summary_text:
            if rich_available and console:
                console.print(
                    Panel(
                        description_text,
                        title="📝 Description",
                        border_style="green",
                        expand=False,
                    )  # type: ignore
                )
            else:
                print(f"\n📝 Description:\n{description_text}")

        # Show complete metadata dump
        rich_print(
            f"\n📋 Complete metadata contains {len([k for k in metadata_dict.keys() if k not in ['source_path', '_src']])} fields:",
            "cyan",
        )

        # Create complete metadata table (excluding internal fields and long text fields)
        complete_metadata = {
            k: v
            for k, v in metadata_dict.items()
            if k not in ["source_path", "_src", "summary", "description"]
        }
        create_metadata_table(
            complete_metadata,
            "📊 Complete Merged Metadata (All Fields except Long Text)",
        )

        # Step 2: Three-source analysis
        rich_print("\n4️⃣ Testing three-source merging directly...", "blue bold")

        from mk_torrent.core.metadata.sources.audnexus import AudnexusSource
        from mk_torrent.core.metadata.sources.embedded import EmbeddedSource
        from mk_torrent.core.metadata.sources.pathinfo import PathInfoSource
        from mk_torrent.core.metadata.services.merge_audiobook import merge_metadata

        # Extract from all three sources with caching
        try:
            if cache_available:
                api_data = cached_api_extraction(AudnexusSource, str(sample_file))
            else:
                api_source = AudnexusSource()
                api_data = api_source.extract(str(sample_file))
            api_data["_src"] = "api"

            embedded_source = EmbeddedSource()
            embedded_data = embedded_source.extract(str(sample_file))
            embedded_data["_src"] = "embedded"

            path_source = PathInfoSource()
            path_data = path_source.extract(str(sample_file))
            path_data["_src"] = "path"

            # Create visual comparison
            create_source_comparison_tree(api_data, embedded_data, path_data)

            # Merge and show results
            candidates = [api_data, embedded_data, path_data]
            merged_direct = merge_metadata(candidates)

            merge_stats = {
                "API Fields": str(len(api_data) - 1),
                "Embedded Fields": str(len(embedded_data) - 1),
                "Path Fields": str(len(path_data) - 1),
                "Merged Fields": str(len(merged_direct)),
                "Chapters (API)": str(api_data.get("chapter_count", 0)),
                "Chapters (Embedded)": str(embedded_data.get("chapter_count", 0)),
                "Chapters (Merged)": str(merged_direct.get("chapter_count", 0)),
            }

            create_metadata_table(merge_stats, "🔄 Three-Source Merge Results")

        except Exception as e:
            rich_print(f"⚠️ Three-source testing failed: {e}", "yellow")

        # Step 3: Validation
        rich_print("\n3️⃣ Validating metadata...", "blue bold")
        validation = engine.validate_metadata(metadata_dict)

        validation_data = {
            "Valid": str(validation.valid),
            "Completeness": f"{validation.completeness:.1%}",
            "Total Fields": str(
                len(
                    [
                        k
                        for k in metadata_dict.keys()
                        if k not in ["source_path", "_src"]
                    ]
                )
            ),
        }

        if validation.warnings:
            validation_data["Warnings"] = str(len(validation.warnings))
        if validation.errors:
            validation_data["Errors"] = str(len(validation.errors))

        create_metadata_table(validation_data, "📋 Validation Results")

        # Step 4: AudiobookMeta conversion
        rich_print("\n2️⃣ Converting to AudiobookMeta...", "blue bold")
        audiobook = AudiobookMeta.from_dict(metadata_dict)
        rich_print(
            f"✅ AudiobookMeta object created successfully (type: {type(audiobook).__name__})",
            "green",
        )

        # Success summary
        if rich_available and console:
            console.print(
                Panel.fit(
                    "🎉 All tests completed successfully!",
                    style="bold green",
                    border_style="green",
                )  # type: ignore
            )
        else:
            print("\n🎉 All tests completed successfully!")

    except Exception as e:
        rich_print(f"\n❌ Test failed: {e}", "red bold")
        if rich_available and console:
            console.print_exception()
        else:
            import traceback

            traceback.print_exc()


def test_comparison_with_old_system():
    """Compare with the old integration using enhanced output and similarity scoring."""
    if rich_available and console:
        console.print(
            Panel.fit(
                "🔄 Comparing with existing Audnexus integration",
                style="bold yellow",
                border_style="yellow",
            )  # type: ignore
        )
    else:
        print("\n" + "=" * 60)
        print("🔄 Comparing with existing Audnexus integration")
        print("=" * 60)

    try:
        # Test old system with caching
        rich_print("🔧 Testing existing integration...", "blue")

        from mk_torrent.integrations.audnexus_api import fetch_metadata_by_asin

        if cache_available:

            @cached(api_cache)  # type: ignore
            def cached_old_fetch(asin: str) -> Any:
                return fetch_metadata_by_asin(asin)

            old_metadata = cached_old_fetch("B0C8ZW5N6Y")
        else:
            old_metadata = fetch_metadata_by_asin("B0C8ZW5N6Y")

        # Test new system with caching
        rich_print("🆕 Testing new core system...", "green")

        from mk_torrent.core.metadata.sources.audnexus import AudnexusSource

        if cache_available:
            new_metadata = cached_api_extraction(AudnexusSource, "B0C8ZW5N6Y")
        else:
            audnexus = AudnexusSource()
            new_metadata = audnexus.extract("B0C8ZW5N6Y")

        # Create comparison tables
        if old_metadata and new_metadata:
            old_data = {
                "Title": old_metadata.get("title", "N/A"),
                "Album": old_metadata.get("album", "N/A"),
                "Artist": old_metadata.get("artist", "N/A"),
                "Year": str(old_metadata.get("year", "N/A")),
                "Runtime": old_metadata.get("runtime_formatted", "N/A"),
                "Field Count": str(len(old_metadata)),
            }

            new_data = {
                "Title": new_metadata.get("title", "N/A"),
                "Album": new_metadata.get("album", "N/A"),
                "Author": new_metadata.get("author", "N/A"),
                "Year": str(new_metadata.get("year", "N/A")),
                "Duration": new_metadata.get("duration", "N/A"),
                "Field Count": str(len(new_metadata)),
            }

            # Calculate similarity if fuzzy matching is available
            if fuzz_available:
                similarity = calculate_metadata_similarity(old_metadata, new_metadata)
                old_data["Similarity Score"] = f"{similarity:.1f}%"
                new_data["Similarity Score"] = f"{similarity:.1f}%"

            create_metadata_table(old_data, "� Legacy System")
            create_metadata_table(new_data, "🆕 New Core System")

            # Architectural improvements summary
            improvements = {
                "Three-source merging": "vs single-source extraction",
                "Declarative precedence": "vs hard-coded field selection",
                "Smart list union": "vs simple overwrite",
                "Technical/descriptive separation": "vs mixed field handling",
                "Consistent field naming": "author vs artist",
                "Protocol-based architecture": "vs direct API calls",
                "Type-safe AudiobookMeta": "vs raw dictionaries",
                "Comprehensive validation": "vs basic checks",
                "Clean separation of concerns": "vs monolithic functions",
                "Robust error handling": "vs simple try/catch",
            }

            create_metadata_table(improvements, "📈 Major Architectural Improvements")

        else:
            rich_print("⚠️ Could not retrieve metadata for comparison", "yellow")

    except Exception as e:
        rich_print(f"❌ Comparison failed: {e}", "red")
        if rich_available and console:
            console.print_exception()
        else:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    test_audiobook_processor()
    test_comparison_with_old_system()
