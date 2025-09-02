#!/usr/bin/env python3
"""
Comprehensive metadata testing with real audiobook files
Tests the metadata system with filtering for binary data
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

console = Console()

def test_metadata_extraction():
    """Test metadata extraction with real audiobook"""
    
    # Test file path
    test_path = Path("/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]")
    
    console.print(Panel.fit(
        "[bold cyan]🧪 Comprehensive Metadata Testing[/bold cyan]\n"
        "Testing with real audiobook files",
        border_style="cyan"
    ))
    
    if not test_path.exists():
        console.print(f"[red]❌ Test path not found: {test_path}[/red]")
        return False
    
    console.print(f"[cyan]📂 Testing path: {test_path.name}[/cyan]")
    
    try:
        # Test 1: Basic engine import
        console.print("\n[bold]🔧 Test 1: Engine Import[/bold]")
        from mk_torrent.core.metadata.engine import MetadataEngine
        from mk_torrent.core.metadata.audiobook import AudiobookMetadata
        console.print("✅ Metadata engine imported successfully")
        
        # Test 2: Engine initialization
        console.print("\n[bold]🔧 Test 2: Engine Initialization[/bold]")
        engine = MetadataEngine()
        console.print(f"✅ Engine initialized with processors: {engine.list_supported_types()}")
        
        # Test 3: Content type detection
        console.print("\n[bold]🔧 Test 3: Content Type Detection[/bold]")
        detected_type = engine._detect_content_type(test_path)
        console.print(f"✅ Detected content type: {detected_type}")
        
        # Test 4: Metadata extraction
        console.print("\n[bold]🔧 Test 4: Full Metadata Extraction[/bold]")
        metadata = engine.process(test_path, content_type='audiobook')
        
        # Display filtered metadata
        console.print("\n[bold]📋 Extracted Metadata (filtered for readability):[/bold]")
        
        table = Table(title="Audiobook Metadata")
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")
        table.add_column("Source", style="yellow")
        
        # Important fields to display
        important_fields = [
            ('title', 'Title'),
            ('album', 'Album'),
            ('author', 'Author'), 
            ('artists', 'Artists'),
            ('narrator', 'Narrator'),
            ('year', 'Year'),
            ('asin', 'ASIN'),
            ('genre', 'Genre'),
            ('publisher', 'Publisher'),
            ('duration', 'Duration'),
            ('format', 'Format'),
            ('encoding', 'Encoding'),
            ('file_size', 'File Size'),
            ('uploader', 'Uploader'),
            ('series', 'Series'),
            ('volume', 'Volume')
        ]
        
        for field_key, field_name in important_fields:
            value = metadata.get(field_key, 'Not found')
            
            # Format the value for display
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            elif isinstance(value, (int, float)) and field_key == 'file_size':
                # Format file size nicely
                size_mb = value / (1024 * 1024)
                value = f"{size_mb:.1f} MB"
            elif isinstance(value, str) and len(value) > 100:
                # Truncate very long values
                value = value[:100] + "..."
            
            # Determine source
            source = "Path" if field_key in ['title', 'author', 'year', 'asin', 'uploader', 'volume'] else "M4B Tags"
            if field_key in ['artists', 'album']:
                source = "Both"
                
            table.add_row(field_name, str(value), source)
        
        console.print(table)
        
        # Test 5: Validation
        console.print("\n[bold]🔧 Test 5: Metadata Validation[/bold]")
        validation = metadata.get('validation', {})
        
        if validation.get('valid'):
            console.print("✅ Metadata validation: PASSED")
        else:
            console.print("❌ Metadata validation: FAILED")
            
        if validation.get('errors'):
            console.print("  Errors:")
            for error in validation['errors']:
                console.print(f"    • [red]{error}[/red]")
                
        if validation.get('warnings'):
            console.print("  Warnings:")
            for warning in validation['warnings']:
                console.print(f"    • [yellow]{warning}[/yellow]")
        
        completeness = validation.get('completeness', 0)
        console.print(f"  Completeness: {completeness:.1%}")
        
        # Test 6: RED compatibility check
        console.print("\n[bold]🔧 Test 6: RED Compatibility Check[/bold]")
        red_required_fields = ['artists', 'album', 'year', 'format']
        missing_fields = []
        
        for field in red_required_fields:
            if not metadata.get(field):
                missing_fields.append(field)
        
        if not missing_fields:
            console.print("✅ All RED required fields present")
        else:
            console.print(f"❌ Missing RED fields: {', '.join(missing_fields)}")
        
        # Test 7: Enhanced metadata
        console.print("\n[bold]🔧 Test 7: Enhanced Metadata Features[/bold]")
        enhanced_fields = ['tags', 'display_name', 'series_info']
        for field in enhanced_fields:
            if metadata.get(field):
                console.print(f"✅ {field}: {metadata[field]}")
        
        console.print(f"\n[green]🎉 All tests completed successfully![/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Test failed: {e}[/red]")
        import traceback
        console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        return False

def test_m4b_tags_filtered():
    """Test M4B tag extraction with proper filtering"""
    
    console.print(Panel.fit(
        "[bold cyan]🏷️  M4B Tags Testing[/bold cyan]\n"
        "Direct M4B tag extraction with filtering",
        border_style="cyan"
    ))
    
    m4b_path = Path("/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.m4b")
    
    if not m4b_path.exists():
        console.print(f"[red]❌ M4B file not found: {m4b_path}[/red]")
        return False
    
    try:
        import mutagen
        from mutagen.mp4 import MP4
        
        audio = MP4(str(m4b_path))
        console.print(f"✅ M4B loaded: {len(audio.tags) if audio.tags else 0} tags found")
        
        if audio.tags:
            # Create table for tags
            table = Table(title="M4B Tags (Filtered)")
            table.add_column("Tag", style="cyan")
            table.add_column("Value", style="white")
            table.add_column("Type", style="yellow")
            
            for key, value in audio.tags.items():
                # Filter out binary data and large text
                if key == 'covr':
                    # Cover art - show size info only
                    if isinstance(value, list) and len(value) > 0:
                        cover_data = value[0]
                        size_kb = len(cover_data) / 1024
                        table.add_row(key, f"[COVER ART - {size_kb:.1f} KB]", "Binary")
                    else:
                        table.add_row(key, "[COVER ART]", "Binary")
                        
                elif isinstance(value, list) and len(value) > 0:
                    val = str(value[0])
                    if len(val) > 150:
                        # Large text data
                        table.add_row(key, f"{val[:100]}... [TRUNCATED - {len(val)} chars]", "Large Text")
                    else:
                        table.add_row(key, val, "Text")
                        
                elif isinstance(value, tuple):
                    table.add_row(key, str(value), "Tuple")
                    
                else:
                    table.add_row(key, str(value), "Other")
            
            console.print(table)
            
            # Audio info
            if audio.info:
                console.print(f"\n⏱️  Duration: {audio.info.length:.0f} seconds ({audio.info.length/3600:.1f} hours)")
                console.print(f"🎵 Bitrate: {audio.info.bitrate} bps")
                console.print(f"📊 Channels: {getattr(audio.info, 'channels', 'Unknown')}")
        
        return True
        
    except ImportError:
        console.print("[red]❌ Mutagen not available[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Error reading M4B: {e}[/red]")
        return False

if __name__ == "__main__":
    console.print("[bold blue]🚀 Starting Comprehensive Metadata Tests[/bold blue]\n")
    
    # Run tests
    test1_success = test_metadata_extraction()
    console.print("\n" + "="*50 + "\n")
    test2_success = test_m4b_tags_filtered()
    
    # Summary
    console.print("\n" + "="*50)
    console.print("[bold]📊 Test Summary[/bold]")
    console.print(f"Metadata Extraction: {'✅ PASS' if test1_success else '❌ FAIL'}")
    console.print(f"M4B Tags Testing: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
    if test1_success and test2_success:
        console.print("\n[bold green]🎉 All tests passed! Metadata system is working correctly.[/bold green]")
    else:
        console.print("\n[bold red]❌ Some tests failed. Check errors above.[/bold red]")
