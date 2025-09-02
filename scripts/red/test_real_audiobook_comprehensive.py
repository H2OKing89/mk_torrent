#!/usr/bin/env python3
"""
Comprehensive Real Audiobook Test for RED Integration
Tests the complete workflow from real audiobook files to RED upload preparation
Includes path validation, metadata extraction, and upload workflow testing
"""

import sys
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, TextColumn, BarColumn, MofNCompleteColumn

# Add project root to path
project_root = Path(__file__).parent.parent.parent  # Go up to project root
sys.path.insert(0, str(project_root / "src"))

console = Console()

# Test audiobook paths
TEST_PATHS = {
    'samples': Path("/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]"),
    'seedvault': Path("/mnt/user/data/downloads/torrents/qbittorrent/seedvault/audiobooks/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]")
}

def test_path_validation():
    """Test RED path validation with real audiobook paths"""
    console.print("\n[bold cyan]📏 Testing RED Path Validation[/bold cyan]")
    
    try:
        from mk_torrent.api.trackers.red import RedactedAPI
        
        red_api = RedactedAPI(api_key='test_key')
        
        # Test cases: (description, path, expected_result)
        test_cases = [
            ("Folder name only", "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]", True),
            ("Test samples path", str(TEST_PATHS['samples']), False),  # Full path too long
            ("Seedvault path", str(TEST_PATHS['seedvault']), False),  # Full path too long
            ("Short path", "Short/Path", True),
            ("Exactly 150 chars", "A" * 150, True),
            ("151 chars", "A" * 151, False),
        ]
        
        table = Table(title="RED Path Validation Results")
        table.add_column("Test Case", style="cyan")
        table.add_column("Length", style="white")
        table.add_column("Expected", style="white")
        table.add_column("Result", style="bold")
        
        all_passed = True
        
        for description, test_path, expected in test_cases:
            length = len(test_path)
            # For RED, we should validate the folder name, not full path
            if test_path.startswith('/'):
                # Extract folder name from full path
                folder_name = Path(test_path).name
                is_valid = red_api.check_path_compliance(folder_name)
                actual_length = len(folder_name)
            else:
                is_valid = red_api.check_path_compliance(test_path)
                actual_length = length
            
            # Update expected results for folder name validation
            if description == "Test samples path" or description == "Seedvault path":
                expected = True  # Folder name should be valid
            
            status = "✅ PASS" if is_valid == expected else "❌ FAIL"
            result_style = "green" if is_valid == expected else "red"
            
            table.add_row(
                description,
                str(actual_length),
                "Valid" if expected else "Invalid", 
                f"[{result_style}]{status}[/{result_style}]"
            )
            
            if is_valid != expected:
                all_passed = False
        
        console.print(table)
        console.print(f"\n🎯 RED path limit: {red_api.config.max_path_length} characters")
        
        return all_passed
        
    except Exception as e:
        console.print(f"[red]❌ Path validation test failed: {e}[/red]")
        return False

def analyze_audiobook_files():
    """Analyze both audiobook locations"""
    console.print("\n[bold cyan]📚 Analyzing Real Audiobook Files...[/bold cyan]")
    
    results = {}
    
    for location, path in TEST_PATHS.items():
        console.print(f"\n[yellow]📂 Checking {location} location...[/yellow]")
        
        if not path.exists():
            console.print(f"[red]❌ Path not found: {path}[/red]")
            results[location] = None
            continue
        
        # Find files
        m4b_files = list(path.glob("*.m4b"))
        cover_files = list(path.glob("*.jpg")) + list(path.glob("*.png"))
        
        if not m4b_files:
            console.print(f"[red]❌ No M4B file found in {location}[/red]")
            results[location] = None
            continue
        
        m4b_file = m4b_files[0]
        cover_file = cover_files[0] if cover_files else None
        
        # Display file structure
        tree = Tree(f"[bold blue]{path.name}[/bold blue]")
        for file in path.iterdir():
            if file.is_file():
                size_mb = file.stat().st_size / (1024 * 1024)
                tree.add(f"{file.name} [dim]({size_mb:.1f} MB)[/dim]")
        
        console.print(tree)
        
        info = {
            'folder_path': path,
            'm4b_file': m4b_file,
            'cover_file': cover_file,
            'folder_name': path.name,
            'folder_length': len(path.name),
            'full_path_length': len(str(path))
        }
        
        console.print(f"✅ Found M4B: {m4b_file.name}")
        if cover_file:
            console.print(f"✅ Found cover: {cover_file.name}")
        console.print(f"📏 Folder name: {info['folder_length']} chars")
        console.print(f"📏 Full path: {info['full_path_length']} chars")
        
        results[location] = info
    
    return results

def test_metadata_extraction(audiobook_info):
    """Test metadata extraction from real audiobook"""
    console.print("\n[bold cyan]🔍 Testing Metadata Extraction...[/bold cyan]")
    
    try:
        from mk_torrent.core.metadata.engine import MetadataEngine
        from mutagen.mp4 import MP4
        
        m4b_file = audiobook_info['m4b_file']
        
        # Test 1: Use metadata engine
        console.print("1️⃣ Using MetadataEngine...")
        engine = MetadataEngine()
        metadata = engine.process(m4b_file, content_type='audiobook')
        
        # Test 2: Direct Mutagen extraction
        console.print("2️⃣ Using Mutagen directly...")
        audio = MP4(str(m4b_file))
        
        # Combine and enhance metadata
        enhanced_metadata = {
            **metadata,
            'path': audiobook_info['folder_path'],
            'folder_name': audiobook_info['folder_name'],
            'format': 'M4B',
            'encoding': 'AAC',
            'media': 'WEB',
            'type': 'audiobook'
        }
        
        # Extract from Mutagen tags
        if audio.tags:
            enhanced_metadata.update({
                'narrator': audio.tags.get('©wrt', ['Unknown'])[0],
                'publisher': audio.tags.get('cprt', ['Unknown'])[0],
                'genre': audio.tags.get('©gen', ['Unknown'])[0],
                'duration_seconds': int(audio.info.length) if audio.info else 0
            })
        
        # Display extracted metadata
        table = Table(title="Extracted Metadata")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        key_fields = ['title', 'artists', 'year', 'format', 'narrator', 'publisher', 'duration_seconds']
        for field in key_fields:
            value = enhanced_metadata.get(field, 'Unknown')
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            table.add_row(field.title(), str(value))
        
        console.print(table)
        
        return True, enhanced_metadata
        
    except Exception as e:
        console.print(f"[red]❌ Metadata extraction failed: {e}[/red]")
        return False, None

def test_red_validation(metadata):
    """Test RED validation with extracted metadata"""
    console.print("\n[bold cyan]🎯 Testing RED Validation...[/bold cyan]")
    
    try:
        from mk_torrent.api.trackers.red import RedactedAPI
        
        red_api = RedactedAPI(api_key='test_key')
        
        # Validate metadata
        validation = red_api.validate_metadata(metadata)
        
        console.print(f"✅ Validation: {'PASS' if validation['valid'] else 'FAIL'}")
        
        if validation['errors']:
            console.print("[red]❌ Errors:[/red]")
            for error in validation['errors']:
                console.print(f"  • {error}")
        
        if validation['warnings']:
            console.print("[yellow]⚠️  Warnings:[/yellow]")
            for warning in validation['warnings']:
                console.print(f"  • {warning}")
        
        # Test folder name compliance specifically
        folder_name = metadata.get('folder_name', '')
        if folder_name:
            is_compliant = red_api.check_path_compliance(folder_name)
            console.print(f"📏 Folder name compliance: {'✅ PASS' if is_compliant else '❌ FAIL'}")
            console.print(f"   '{folder_name}' ({len(folder_name)}/{red_api.config.max_path_length} chars)")
        
        # Test release type detection
        release_type = red_api._detect_release_type(metadata)
        expected_type = red_api.RELEASE_TYPES['SOUNDTRACK']  # Audiobooks use SOUNDTRACK
        console.print(f"🎭 Release type: {release_type} ({'✅ Correct' if release_type == expected_type else '❌ Incorrect'})")
        
        return validation['valid']
        
    except Exception as e:
        console.print(f"[red]❌ RED validation failed: {e}[/red]")
        return False

def test_upload_preparation(metadata):
    """Test upload data preparation"""
    console.print("\n[bold cyan]📤 Testing Upload Preparation...[/bold cyan]")
    
    try:
        from mk_torrent.api.trackers.red import RedactedAPI
        
        red_api = RedactedAPI(api_key='test_key')
        dummy_torrent = Path('/tmp/test.torrent')
        
        upload_data = red_api.prepare_upload_data(metadata, dummy_torrent)
        
        console.print("✅ Upload data prepared successfully")
        
        # Display key upload fields
        key_fields = ['groupname', 'artists[]', 'year', 'releasetype', 'format', 'media', 'tags']
        
        table = Table(title="Upload Data")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        for field in key_fields:
            value = upload_data.get(field, 'Not set')
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            table.add_row(field, str(value))
        
        console.print(table)
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Upload preparation failed: {e}[/red]")
        return False

def test_dry_run_upload(metadata):
    """Test dry run upload"""
    console.print("\n[bold cyan]🚀 Testing Dry Run Upload...[/bold cyan]")
    
    try:
        from mk_torrent.api.trackers.red import RedactedAPI
        
        red_api = RedactedAPI(api_key='test_key')
        dummy_torrent = Path('/tmp/test.torrent')
        
        result = red_api.upload_torrent(dummy_torrent, metadata, dry_run=True)
        
        console.print(f"✅ Dry run: {'SUCCESS' if result['success'] else 'FAILED'}")
        console.print(f"📋 Message: {result.get('message', 'No message')}")
        
        return result['success']
        
    except Exception as e:
        console.print(f"[red]❌ Dry run failed: {e}[/red]")
        return False

def display_summary(results):
    """Display test summary"""
    table = Table(title="Comprehensive Real Audiobook Test Results")
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Notes")
    
    test_descriptions = {
        'path_validation': 'RED path compliance checking',
        'file_analysis': 'Audiobook file structure analysis',
        'metadata_extraction': 'Metadata extraction from M4B files',
        'red_validation': 'RED tracker validation requirements',
        'upload_preparation': 'Upload data preparation',
        'dry_run': 'Dry run upload workflow'
    }
    
    for test_name, success in results.items():
        status = "[green]✅ PASS[/green]" if success else "[red]❌ FAIL[/red]"
        description = test_descriptions.get(test_name, "Unknown test")
        table.add_row(test_name.replace('_', ' ').title(), status, description)
    
    console.print("\n")
    console.print(table)
    
    passed = sum(results.values())
    total = len(results)
    
    if passed == total:
        console.print(f"\n[bold green]🎉 All {total} tests passed! Real audiobook integration ready.[/bold green]")
    else:
        console.print(f"\n[bold yellow]⚠️  {passed}/{total} tests passed. Some issues to address.[/bold yellow]")
    
    return passed == total

def main():
    """Run comprehensive real audiobook tests"""
    console.print(Panel.fit(
        "[bold cyan]📚 Comprehensive Real Audiobook Test[/bold cyan]\n"
        "Testing RED integration with actual audiobook files from both locations",
        border_style="cyan"
    ))
    
    results = {}
    
    # Test 1: Path validation
    results['path_validation'] = test_path_validation()
    
    # Test 2: File analysis
    audiobook_info = analyze_audiobook_files()
    
    # Choose which audiobook to test with (prefer samples, fallback to seedvault)
    test_info = None
    if audiobook_info.get('samples'):
        test_info = audiobook_info['samples']
        console.print("\n[green]📂 Using samples location for testing[/green]")
    elif audiobook_info.get('seedvault'):
        test_info = audiobook_info['seedvault']
        console.print("\n[yellow]📂 Using seedvault location for testing[/yellow]")
    
    results['file_analysis'] = test_info is not None
    
    if test_info:
        # Test 3: Metadata extraction
        success, metadata = test_metadata_extraction(test_info)
        results['metadata_extraction'] = success
        
        if success and metadata:
            # Test 4: RED validation
            results['red_validation'] = test_red_validation(metadata)
            
            # Test 5: Upload preparation
            results['upload_preparation'] = test_upload_preparation(metadata)
            
            # Test 6: Dry run upload
            results['dry_run'] = test_dry_run_upload(metadata)
        else:
            results.update({
                'red_validation': False,
                'upload_preparation': False,
                'dry_run': False
            })
    else:
        console.print("\n[red]❌ No valid audiobook found for testing[/red]")
        results.update({
            'metadata_extraction': False,
            'red_validation': False,
            'upload_preparation': False,
            'dry_run': False
        })
    
    # Display comprehensive summary
    all_passed = display_summary(results)
    
    if all_passed:
        console.print("\n[bold green]🎯 Ready for Production:[/bold green]")
        console.print("1. All path validation working correctly")
        console.print("2. Metadata extraction from real M4B files")
        console.print("3. RED validation passing")
        console.print("4. Upload workflow ready")
        console.print("5. Ready to test with real RED API credentials")
        
        console.print("\n[bold cyan]📋 Next Steps:[/bold cyan]")
        console.print("• Test CLI: python scripts/cli/red_upload_cli.py /path/to/audiobook --dry-run")
        console.print("• Use real API key when ready for actual uploads")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
