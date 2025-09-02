#!/usr/bin/env python3
"""
Refactor RED modules into better structure
"""

from pathlib import Path
import shutil
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

console = Console()

def show_refactor_plan():
    """Show the refactoring plan"""
    
    console.print("\n[bold cyan]🔄 RED Module Refactoring Plan[/bold cyan]\n")
    
    table = Table(title="Module Reorganization", show_header=True)
    table.add_column("Current Location", style="red")
    table.add_column("New Location", style="green")
    table.add_column("Purpose", style="cyan")
    
    # Refactoring mappings
    mappings = [
        ("api/red_integration.py", "workflows/tracker_integration.py", 
         "Generic tracker integration workflow"),
        ("features/red_uploader.py", "api/trackers/red.py", 
         "RED-specific API client"),
        ("features/metadata_engine.py", "core/metadata/engine.py", 
         "Generic metadata processing"),
        ("utils/red_path_compliance.py", "core/compliance/path_fixer.py", 
         "Path compliance fixing logic"),
        ("utils/red_compliance_rename.py", "[DEPRECATED]", 
         "Replaced by path_fixer.py"),
        ("utils/red_api_parser.py", "utils/api_parser.py", 
         "Generic API doc parser"),
    ]
    
    for current, new, purpose in mappings:
        table.add_row(current, new, purpose)
    
    console.print(table)
    
    console.print("\n[bold yellow]Key Benefits:[/bold yellow]")
    console.print("✅ Tracker-agnostic metadata processing")
    console.print("✅ Clear separation of concerns")
    console.print("✅ Easy to add new trackers (MAM, OPS, etc.)")
    console.print("✅ Reusable compliance tools")
    console.print("✅ Better naming convention")
    console.print("✅ Consolidates overlapping functionality")
    
    console.print("\n[bold cyan]New Structure:[/bold cyan]")
    console.print("""
    api/trackers/           # All tracker APIs in one place
        ├── __init__.py     # Factory function & registry
        ├── base.py         # Abstract interface
        ├── red.py          # RED implementation
        ├── mam.py          # MAM implementation (future)
        └── ops.py          # OPS implementation (future)
    
    core/metadata/          # Content-type specific metadata
        ├── __init__.py     # Main exports
        ├── engine.py       # Main processor engine
        ├── audiobook.py    # Audiobook metadata
        ├── music.py        # Music metadata (future)
        └── video.py        # Video metadata (future)
    
    core/compliance/        # Path compliance tools
        ├── __init__.py     # Main exports
        ├── path_validator.py # Validation rules
        └── path_fixer.py     # Fixing logic (replaces red_path_compliance.py)
    
    utils/
        ├── api_parser.py   # Generic API doc parser (renamed)
        └── async_helpers.py
    """)

def show_current_status():
    """Show what has been created so far"""
    console.print("\n[bold green]✅ Created New Structure:[/bold green]")
    
    created_files = [
        "api/trackers/__init__.py",
        "api/trackers/base.py", 
        "api/trackers/red.py",
        "core/metadata/__init__.py",
        "core/metadata/engine.py",
        "core/metadata/audiobook.py",
        "core/compliance/__init__.py",
        "core/compliance/path_validator.py",
        "core/compliance/path_fixer.py",
        "utils/api_parser.py (renamed)"
    ]
    
    for file_path in created_files:
        console.print(f"  ✅ {file_path}")
    
    console.print("\n[bold yellow]📋 Next Steps:[/bold yellow]")
    console.print("1. Move metadata_engine.py → core/metadata/engine.py (replace generic version)")
    console.print("2. Update imports throughout codebase")
    console.print("3. Create integration workflow")
    console.print("4. Test new structure")
    console.print("5. Remove old files")

def integrate_existing_metadata():
    """Integrate existing metadata engine with new structure"""
    console.print("\n[bold cyan]🔄 Integrating Existing Metadata Engine...[/bold cyan]")
    
    old_metadata = Path("src/mk_torrent/features/metadata_engine.py")
    new_metadata = Path("src/mk_torrent/core/metadata/engine.py")
    
    if old_metadata.exists():
        console.print(f"[green]Found existing metadata engine: {old_metadata}[/green]")
        
        if Confirm.ask("Replace generic engine with existing implementation?", default=True):
            # Would backup and replace the metadata engine
            console.print("[yellow]Implementation needed: Merge existing metadata_engine.py[/yellow]")
            return True
    
    return False

def create_migration_checklist():
    """Create a checklist for the migration"""
    console.print("\n[bold cyan]📋 Migration Checklist:[/bold cyan]")
    
    checklist = [
        "✅ Created new directory structure",
        "✅ Created base tracker API interface", 
        "✅ Created RED tracker implementation",
        "✅ Created metadata processing engine",
        "✅ Created path compliance system",
        "✅ Renamed generic utilities",
        "⏳ Integrate existing metadata_engine.py",
        "⏳ Update import statements",
        "⏳ Create tracker integration workflow", 
        "⏳ Test new implementations",
        "⏳ Update CLI to use new structure",
        "⏳ Remove old duplicate files"
    ]
    
    for item in checklist:
        console.print(f"  {item}")

if __name__ == "__main__":
    show_refactor_plan()
    show_current_status()
    
    console.print("\n[yellow]This refactoring will:[/yellow]")
    console.print("1. Create cleaner module organization")
    console.print("2. Make metadata processing tracker-agnostic")
    console.print("3. Consolidate path compliance tools")
    console.print("4. Prepare for MAM/OPS support")
    console.print("5. Eliminate overlapping functionality")
    
    create_migration_checklist()
    
    console.print("\n[bold green]🎉 Refactoring Structure Created![/bold green]")
    console.print("The new modular structure is ready for integration and testing.")
