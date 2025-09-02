#!/usr/bin/env python3
"""
Test script for Audnexus API integration
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

def test_audnexus_api_integration():
    """Test the Audnexus API integration with real audiobook"""
    
    console.print(Panel.fit(
        "[bold cyan]🔗 Audnexus API Integration Test[/bold cyan]\n"
        "Testing HTTPX-based API calls with real ASIN",
        border_style="cyan"
    ))
    
    # Test ASIN from our real file
    test_asin = "B0C8ZW5N6Y"  # How a Realist Hero Rebuilt the Kingdom vol 3
    
    try:
        console.print(f"\n[bold]🧪 Testing ASIN: {test_asin}[/bold]")
        
        # Test direct API call
        from mk_torrent.integrations.audnexus import get_audnexus_metadata
        
        console.print("📡 Fetching from Audnexus API...")
        api_data = get_audnexus_metadata(test_asin)
        
        if api_data:
            console.print("[green]✅ API call successful![/green]")
            
            # Display key API data
            table = Table(title="Audnexus API Response")
            table.add_column("Field", style="cyan", no_wrap=True)
            table.add_column("Value", style="white")
            table.add_column("Type", style="yellow")
            
            # Important fields to show
            display_fields = [
                ('asin', 'ASIN'),
                ('title', 'Title'),
                ('authors', 'Authors'),
                ('narrators', 'Narrators'),
                ('publisherName', 'Publisher'),
                ('releaseDate', 'Release Date'),
                ('runtimeLengthMin', 'Runtime (min)'),
                ('runtime_formatted', 'Runtime (formatted)'),
                ('formatType', 'Format Type'),
                ('literatureType', 'Literature Type'),
                ('language', 'Language'),
                ('rating', 'Rating'),
                ('isbn', 'ISBN'),
                ('genres', 'Genres'),
                ('series', 'Series'),
                ('image', 'Cover Image'),
                ('audnexus_source', 'API Source'),
                ('audnexus_fetched_at', 'Fetched At')
            ]
            
            for field_key, field_name in display_fields:
                value = api_data.get(field_key, 'Not found')
                
                if isinstance(value, list):
                    if field_key == 'authors':
                        # Show author names
                        value = ', '.join([author.get('name', 'Unknown') for author in value])
                        value_type = f"List ({len(api_data.get(field_key, []))} authors)"
                    elif field_key == 'narrators':
                        # Show narrator names  
                        value = ', '.join([narrator.get('name', 'Unknown') for narrator in value])
                        value_type = f"List ({len(api_data.get(field_key, []))} narrators)"
                    elif field_key == 'genres':
                        # Show genre names
                        genre_names = [g.get('name', 'Unknown') for g in value if g.get('type') == 'genre']
                        value = ', '.join(genre_names)
                        value_type = f"List ({len(api_data.get(field_key, []))} total)"
                    else:
                        value = ', '.join(str(v) for v in value)
                        value_type = f"List ({len(value)})"
                elif isinstance(value, dict):
                    if field_key == 'series':
                        value = f"{value.get('name', 'Unknown')} #{value.get('position', '?')}"
                        value_type = "Series Object"
                    else:
                        value = str(value)
                        value_type = "Object"
                elif isinstance(value, str) and len(value) > 80:
                    value = value[:80] + "..."
                    value_type = "Long String"
                elif isinstance(value, bool):
                    value = "Yes" if value else "No"
                    value_type = "Boolean"
                else:
                    value_type = type(value).__name__
                
                table.add_row(field_name, str(value), value_type)
            
            console.print(table)
            
            # Test HTML cleaning
            if api_data.get('summary'):
                console.print(f"\n[bold]🧹 HTML Cleaning Test[/bold]")
                original_summary = api_data.get('summary_raw', api_data.get('summary', ''))
                cleaned_summary = api_data.get('summary_cleaned', '')
                
                console.print(f"Original length: {len(original_summary)} chars")
                console.print(f"Cleaned length: {len(cleaned_summary)} chars")
                console.print(f"HTML removed: {len(original_summary) - len(cleaned_summary)} chars")
                
                if len(cleaned_summary) > 200:
                    console.print(f"Cleaned preview: {cleaned_summary[:200]}...")
                else:
                    console.print(f"Cleaned content: {cleaned_summary}")
            
            # Count total fields
            total_fields = len(api_data)
            api_fields = sum(1 for k in api_data.keys() if not k.startswith('_'))
            console.print(f"\n[cyan]📊 Total fields: {total_fields} | API fields: {api_fields}[/cyan]")
            
            return True
            
        else:
            console.print("[red]❌ API call failed or returned no data[/red]")
            return False
            
    except ImportError as e:
        console.print(f"[red]❌ Import error: {e}[/red]")
        console.print("[yellow]Note: Make sure httpx and nh3 are installed[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Test failed: {e}[/red]")
        import traceback
        console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        return False

if __name__ == "__main__":
    console.print("[bold blue]🚀 Starting Audnexus API Tests[/bold blue]\n")
    
    # Run test
    test_success = test_audnexus_api_integration()
    
    # Summary
    console.print("\n" + "="*50)
    console.print("[bold]📊 API Test Summary[/bold]")
    console.print(f"Direct API Test: {'✅ PASS' if test_success else '❌ FAIL'}")
    
    if test_success:
        console.print("\n[bold green]🎉 Audnexus API integration is working![/bold green]")
    else:
        console.print("\n[bold red]❌ API test failed. Check errors above.[/bold red]")
