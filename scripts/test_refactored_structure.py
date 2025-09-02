#!/usr/bin/env python3
"""
Test the new refactored structure
"""

from rich.console import Console
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

console = Console()

def test_tracker_api():
    """Test the new tracker API structure"""
    console.print("\n[bold cyan]🧪 Testing Tracker API Structure...[/bold cyan]")
    
    try:
        # Test importing the base API
        from mk_torrent.api.trackers.base import TrackerAPI, TrackerConfig
        console.print("✅ Imported base tracker API")
        
        # Test importing RED implementation  
        from mk_torrent.api.trackers.red import RedactedAPI
        console.print("✅ Imported RED API implementation")
        
        # Test factory function
        from mk_torrent.api.trackers import get_tracker_api, list_available_trackers
        console.print("✅ Imported factory functions")
        
        # Test tracker registry
        trackers = list_available_trackers()
        console.print(f"✅ Available trackers: {trackers}")
        
        # Test RED tracker config
        red_api = RedactedAPI(api_key="test_key")
        config = red_api.get_tracker_config()
        console.print(f"✅ RED config: {config.name}, max_length={config.max_path_length}")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Tracker API test failed: {e}")
        return False

def test_metadata_engine():
    """Test the new metadata engine structure"""
    console.print("\n[bold cyan]🧪 Testing Metadata Engine...[/bold cyan]")
    
    try:
        # Test importing metadata engine
        from mk_torrent.core.metadata.engine import MetadataEngine, process_metadata
        console.print("✅ Imported metadata engine")
        
        # Test importing audiobook processor
        from mk_torrent.core.metadata.audiobook import AudiobookMetadata
        console.print("✅ Imported audiobook metadata processor")
        
        # Test engine creation
        engine = MetadataEngine()
        supported_types = engine.list_supported_types()
        console.print(f"✅ Supported content types: {supported_types}")
        
        # Test content type detection
        test_path = Path("/test/audiobook.m4b")
        content_type = engine._detect_content_type(test_path)
        console.print(f"✅ Detected content type for .m4b: {content_type}")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Metadata engine test failed: {e}")
        return False

def test_compliance_system():
    """Test the new compliance system"""
    console.print("\n[bold cyan]🧪 Testing Compliance System...[/bold cyan]")
    
    try:
        # Test importing path validator
        from mk_torrent.core.compliance.path_validator import PathValidator, PathRule
        console.print("✅ Imported path validator")
        
        # Test importing path fixer
        from mk_torrent.core.compliance.path_fixer import PathFixer, ComplianceConfig
        console.print("✅ Imported path fixer")
        
        # Test RED validator
        red_validator = PathValidator('red')
        console.print(f"✅ RED validator max length: {red_validator.rule.max_length}")
        
        # Test path validation
        test_path = "short/path.m4b"
        valid, issues = red_validator.validate(Path(test_path))
        console.print(f"✅ Path validation result: valid={valid}")
        
        # Test compliance comparison
        long_path = "x" * 200 + "/file.m4b"
        comparison = PathValidator.compare_trackers(long_path)
        console.print(f"✅ Tracker comparison for long path: {len(comparison)} trackers")
        
        # Test path fixer
        fixer = PathFixer('red')
        console.print(f"✅ Path fixer created for RED (max: {fixer.config.max_full_path})")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Compliance system test failed: {e}")
        return False

def test_integration():
    """Test integration between components"""
    console.print("\n[bold cyan]🧪 Testing Component Integration...[/bold cyan]")
    
    try:
        # Test RED API with compliance checking
        from mk_torrent.api.trackers import get_tracker_api
        from mk_torrent.core.compliance import PathValidator
        
        red_api = get_tracker_api('red', api_key='test')
        validator = PathValidator('red')
        
        # Test compliance check using tracker config
        test_path = "test/path.m4b"
        compliant = red_api.check_path_compliance(test_path)
        console.print(f"✅ RED API compliance check: {compliant}")
        
        # Test compliance report
        paths = ["short.m4b", "very_long_path_that_exceeds_limits.m4b"]
        report = red_api.get_compliance_report(paths)
        console.print(f"✅ Compliance report: {report['compliance_rate']:.1%} compliant")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    console.print("[bold green]🚀 Testing New Refactored Structure[/bold green]")
    
    tests = [
        ("Tracker API", test_tracker_api),
        ("Metadata Engine", test_metadata_engine), 
        ("Compliance System", test_compliance_system),
        ("Component Integration", test_integration)
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
    
    # Summary
    console.print("\n[bold cyan]📊 Test Summary:[/bold cyan]")
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASSED" if passed_test else "❌ FAILED"
        console.print(f"  {status}: {test_name}")
    
    console.print(f"\n[bold {'green' if passed == total else 'yellow'}]Results: {passed}/{total} tests passed[/bold {'green' if passed == total else 'yellow'}]")
    
    if passed == total:
        console.print("\n[bold green]🎉 All tests passed! The refactored structure is working correctly.[/bold green]")
    else:
        console.print("\n[bold yellow]⚠️ Some tests failed. Check import paths and dependencies.[/bold yellow]")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
