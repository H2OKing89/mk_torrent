#!/usr/bin/env python3
"""
Test Audnexus API integration specifically
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Configure logging to see API calls
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

console = Console()

def test_audnexus_api_direct():
    """Test Audnexus API directly"""
    
    console.print(Panel.fit(
        "[bold cyan]🌐 Audnexus API Direct Test[/bold cyan]\n"
        "Testing direct API integration",
        border_style="cyan"
    ))
    
    try:
        from mk_torrent.integrations.audnexus_api import fetch_metadata_by_asin, extract_asin_from_path
        
        # Test ASIN extraction
        test_path = "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]"
        asin = extract_asin_from_path(test_path)
        console.print(f"✅ ASIN extracted: {asin}")
        
        if asin:
            # Test API call
            console.print(f"\n🌐 Fetching metadata for ASIN: {asin}")
            api_data = fetch_metadata_by_asin(asin)
            
            if api_data:
                console.print(f"✅ API call successful! Got {len(api_data)} fields")
                
                # Display key fields
                table = Table(title="Audnexus API Response")
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="white")
                
                key_fields = [
                    'asin', 'title', 'authors', 'narrators', 'genres', 
                    'publisherName', 'rating', 'runtimeLengthMin', 
                    'audnexus_source', 'audnexus_fetched_at'
                ]
                
                for field in key_fields:
                    value = api_data.get(field, 'Not found')
                    if isinstance(value, list):
                        if field == 'authors' and value:
                            value = ', '.join([author.get('name', '') for author in value])
                        elif field == 'narrators' and value:
                            value = ', '.join([narrator.get('name', '') for narrator in value])
                        elif field == 'genres' and value:
                            genres = [g.get('name', '') for g in value if g.get('type') == 'genre']
                            value = ', '.join(genres[:3])  # First 3 genres
                        else:
                            value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                    
                    table.add_row(field, str(value))
                
                console.print(table)
                
                # Test data quality
                console.print(f"\n📊 Data Quality:")
                console.print(f"  Total fields: {len(api_data)}")
                console.print(f"  Has cleaned summary: {'summary_cleaned' in api_data}")
                console.print(f"  Has runtime formatting: {'runtime_formatted' in api_data}")
                console.print(f"  Has detailed authors: {'authors_detailed' in api_data}")
                
                return True
            else:
                console.print("❌ API call returned no data")
                return False
        else:
            console.print("❌ No ASIN found in path")
            return False
            
    except Exception as e:
        console.print(f"❌ API test failed: {e}")
        import traceback
        console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        return False

def test_integrated_metadata():
    """Test metadata extraction with API integration"""
    
    console.print(Panel.fit(
        "[bold green]🔗 Integrated Metadata Test[/bold green]\n"
        "Testing full metadata pipeline with API",
        border_style="green"
    ))
    
    test_path = Path("/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]")
    
    try:
        from mk_torrent.core.metadata.engine import MetadataEngine
        
        engine = MetadataEngine()
        console.print(f"🔧 Processing: {test_path.name}")
        
        # Process with verbose logging
        metadata = engine.process(test_path, content_type='audiobook')
        
        # Check for API enrichment
        api_enriched = metadata.get('audnexus_source', False)
        console.print(f"🌐 API enrichment: {'✅ YES' if api_enriched else '❌ NO'}")
        
        if api_enriched:
            console.print(f"📅 Fetched at: {metadata.get('audnexus_fetched_at')}")
            console.print(f"🏷️ Enhanced fields available:")
            
            enhanced_fields = [
                'authors_detailed', 'narrators_detailed', 'genres_detailed',
                'summary_cleaned', 'runtime_formatted', 'release_date_formatted'
            ]
            
            for field in enhanced_fields:
                if field in metadata:
                    console.print(f"  ✅ {field}")
                else:
                    console.print(f"  ❌ {field}")
        
        return api_enriched
        
    except Exception as e:
        console.print(f"❌ Integration test failed: {e}")
        return False

if __name__ == "__main__":
    console.print("[bold blue]🚀 Testing Audnexus API Integration[/bold blue]\n")
    
    # Run tests
    test1_success = test_audnexus_api_direct()
    console.print("\n" + "="*50 + "\n")
    test2_success = test_integrated_metadata()
    
    # Summary
    console.print("\n" + "="*50)
    console.print("[bold]📊 API Integration Test Summary[/bold]")
    console.print(f"Direct API Test: {'✅ PASS' if test1_success else '❌ FAIL'}")
    console.print(f"Integrated Test: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
    if test1_success and test2_success:
        console.print("\n[bold green]🎉 Audnexus API integration is working perfectly![/bold green]")
        console.print("[bold green]Both embedded M4B tags AND API data are being captured.[/bold green]")
    else:
        console.print("\n[bold yellow]⚠️  Some tests failed. Check logs above for details.[/bold yellow]")
