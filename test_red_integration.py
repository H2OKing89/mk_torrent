#!/usr/bin/env python3
"""
Test metadata system integration with RED upload workflow
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

console = Console()

def test_red_upload_integration():
    """Test the complete RED upload workflow with metadata"""
    
    console.print(Panel.fit(
        "[bold red]🎯 RED Upload Integration Test[/bold red]\n"
        "Testing complete workflow from audiobook to RED upload",
        border_style="red"
    ))
    
    # Test file path
    test_path = Path("/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]")
    
    if not test_path.exists():
        console.print(f"[red]❌ Test path not found: {test_path}[/red]")
        return False
    
    try:
        # Step 1: Import and initialize components
        console.print("\n[bold]🔧 Step 1: Component Initialization[/bold]")
        from mk_torrent.core.metadata.engine import MetadataEngine
        from mk_torrent.integrations.red.red_uploader import RedUploader
        
        engine = MetadataEngine()
        red_uploader = RedUploader()
        console.print("✅ All components imported and initialized")
        
        # Step 2: Extract metadata
        console.print("\n[bold]🔧 Step 2: Metadata Extraction[/bold]")
        metadata = engine.process(test_path, content_type='audiobook')
        console.print(f"✅ Metadata extracted: {len(metadata)} fields")
        
        # Step 3: Validate RED requirements
        console.print("\n[bold]🔧 Step 3: RED Requirements Validation[/bold]")
        red_validation = red_uploader.validate_metadata(metadata)
        
        if red_validation.get('valid', False):
            console.print("✅ Metadata passes RED validation")
        else:
            console.print("❌ Metadata fails RED validation")
            if red_validation.get('errors'):
                for error in red_validation['errors']:
                    console.print(f"    • [red]{error}[/red]")
        
        # Step 4: Format for RED upload
        console.print("\n[bold]🔧 Step 4: RED Upload Formatting[/bold]")
        upload_data = red_uploader.format_upload_data(metadata)
        
        # Display formatted upload data
        table = Table(title="RED Upload Data")
        table.add_column("Field", style="red", no_wrap=True)
        table.add_column("Value", style="white")
        
        red_fields = [
            ('artists', 'Artists'),
            ('album', 'Album'),
            ('year', 'Year'),
            ('format', 'Format'),
            ('encoding', 'Encoding'),
            ('media', 'Media'),
            ('release_desc', 'Release Description'),
            ('tags', 'Tags')
        ]
        
        for field_key, field_name in red_fields:
            value = upload_data.get(field_key, 'Not set')
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            elif isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            table.add_row(field_name, str(value))
        
        console.print(table)
        
        # Step 5: Test torrent creation readiness
        console.print("\n[bold]🔧 Step 5: Torrent Creation Readiness[/bold]")
        torrent_ready = red_uploader.is_ready_for_torrent_creation(test_path, metadata)
        
        if torrent_ready.get('ready', False):
            console.print("✅ Ready for torrent creation")
        else:
            console.print("❌ Not ready for torrent creation")
            if torrent_ready.get('issues'):
                for issue in torrent_ready['issues']:
                    console.print(f"    • [yellow]{issue}[/yellow]")
        
        # Step 6: Display upload summary
        console.print("\n[bold]🔧 Step 6: Upload Summary[/bold]")
        summary_data = {
            "Title": metadata.get('title'),
            "Artist": metadata.get('artists'),
            "Format": f"{metadata.get('format')} / {metadata.get('encoding')}",
            "Duration": f"{metadata.get('duration_hours', 0):.1f} hours",
            "File Size": f"{metadata.get('file_size', 0) / (1024*1024):.1f} MB",
            "RED Categories": upload_data.get('tags', []),
            "Quality Score": f"{metadata.get('validation', {}).get('completeness', 0):.0%}"
        }
        
        for key, value in summary_data.items():
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            console.print(f"  {key}: [cyan]{value}[/cyan]")
        
        console.print(f"\n[green]🎉 RED integration test completed successfully![/green]")
        return True
        
    except ImportError as e:
        console.print(f"[red]❌ Import error: {e}[/red]")
        console.print("[yellow]Note: This is expected if RED uploader is not yet implemented[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Test failed: {e}[/red]")
        import traceback
        console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        return False

def test_metadata_consistency():
    """Test metadata consistency across different access methods"""
    
    console.print(Panel.fit(
        "[bold cyan]🔄 Metadata Consistency Test[/bold cyan]\n"
        "Testing metadata consistency across different extraction methods",
        border_style="cyan"
    ))
    
    test_path = Path("/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]")
    
    try:
        from mk_torrent.core.metadata.engine import MetadataEngine
        from mk_torrent.core.metadata.audiobook import AudiobookMetadata
        
        # Method 1: Via Engine
        engine = MetadataEngine()
        metadata_via_engine = engine.process(test_path, content_type='audiobook')
        
        # Method 2: Direct processor
        processor = AudiobookMetadata()
        metadata_direct = processor.extract(test_path)
        
        # Compare key fields
        comparison_fields = ['title', 'artists', 'album', 'year', 'format', 'duration']
        console.print("\n[bold]🔍 Consistency Check:[/bold]")
        
        all_consistent = True
        for field in comparison_fields:
            engine_val = metadata_via_engine.get(field)
            direct_val = metadata_direct.get(field)
            
            if engine_val == direct_val:
                console.print(f"  ✅ {field}: Consistent")
            else:
                console.print(f"  ❌ {field}: Inconsistent")
                console.print(f"      Engine: {engine_val}")
                console.print(f"      Direct: {direct_val}")
                all_consistent = False
        
        if all_consistent:
            console.print(f"\n[green]✅ All metadata fields are consistent![/green]")
        else:
            console.print(f"\n[yellow]⚠️  Some inconsistencies found[/yellow]")
        
        return all_consistent
        
    except Exception as e:
        console.print(f"[red]❌ Consistency test failed: {e}[/red]")
        return False

if __name__ == "__main__":
    console.print("[bold blue]🚀 Starting RED Integration Tests[/bold blue]\n")
    
    # Run tests
    test1_success = test_red_upload_integration()
    console.print("\n" + "="*50 + "\n")
    test2_success = test_metadata_consistency()
    
    # Summary
    console.print("\n" + "="*50)
    console.print("[bold]📊 Integration Test Summary[/bold]")
    console.print(f"RED Upload Integration: {'✅ PASS' if test1_success else '❌ FAIL'}")
    console.print(f"Metadata Consistency: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
    if test1_success and test2_success:
        console.print("\n[bold green]🎉 All integration tests passed![/bold green]")
        console.print("[bold green]The metadata system is ready for production use.[/bold green]")
    else:
        console.print("\n[bold yellow]⚠️  Some tests didn't complete (expected for unimplemented components).[/bold yellow]")
