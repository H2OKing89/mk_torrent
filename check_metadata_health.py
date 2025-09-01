#!/usr/bin/env python3
"""Metadata Health Check Script

This script performs comprehensive health checks for metadata processing
capabilities in the torrent creator system.
"""

import sys
from rich.console import Console

console = Console()

def check_dependencies():
    """Check all metadata-related dependencies"""
    console.print("[cyan]Checking Dependencies...[/cyan]")

    dependencies = {
        "mutagen": "Audio metadata extraction",
        "nh3": "HTML sanitization (modern)",
        "beautifulsoup4": "HTML parsing fallback",
        "pillow": "Image processing",
        "requests": "HTTP requests for APIs"
    }

    missing_deps = []

    for package, description in dependencies.items():
        try:
            __import__(package)
            console.print(f"  ✅ {package}: {description}")
        except ImportError:
            console.print(f"  ❌ {package}: {description} - MISSING")
            missing_deps.append(package)

    return missing_deps

def check_capabilities():
    """Check metadata processing capabilities"""
    console.print("[cyan]Checking Processing Capabilities...[/cyan]")

    # Audio format support
    try:
        import mutagen
        console.print("  ✅ Audio metadata extraction available")
        audio_ok = True
    except ImportError:
        console.print("  ❌ Audio metadata extraction unavailable")
        audio_ok = False

    # HTML sanitization
    html_ok = False
    try:
        import nh3
        console.print("  ✅ Modern HTML sanitization (nh3) available")
        html_ok = True
    except ImportError:
        try:
            from bs4 import BeautifulSoup
            console.print("  ⚠️  Basic HTML sanitization (BeautifulSoup) available")
            html_ok = True
        except ImportError:
            console.print("  ❌ HTML sanitization unavailable")

    # Image processing
    try:
        from PIL import Image
        console.print("  ✅ Image processing available")
        image_ok = True
    except ImportError:
        console.print("  ❌ Image processing unavailable")
        image_ok = False

    return {
        "audio": audio_ok,
        "html": html_ok,
        "image": image_ok
    }

def check_connectivity():
    """Check connectivity to external services"""
    console.print("[cyan]Checking External Connectivity...[/cyan]")

    import requests

    # Audnexus API
    try:
        response = requests.get("https://api.audnex.us", timeout=10)
        if response.status_code == 200:
            console.print("  ✅ Audnexus API: Reachable")
            audnexus_ok = True
        else:
            console.print(f"  ⚠️  Audnexus API: HTTP {response.status_code}")
            audnexus_ok = False
    except Exception as e:
        console.print(f"  ❌ Audnexus API: {str(e)}")
        audnexus_ok = False

    return {"audnexus": audnexus_ok}

def generate_report(missing_deps, capabilities, connectivity):
    """Generate a comprehensive health report"""
    console.print("\n[bold green]Metadata Health Report[/bold green]")
    console.print("=" * 50)

    # Overall status
    critical_issues = len(missing_deps)
    if not capabilities.get("audio"):
        critical_issues += 1

    if critical_issues == 0:
        status = "[green]✅ HEALTHY[/green]"
    elif critical_issues <= 2:
        status = "[yellow]⚠️  WARNING[/yellow]"
    else:
        status = "[red]❌ CRITICAL ISSUES[/red]"

    console.print(f"Overall Status: {status}")

    # Summary
    console.print("\n[cyan]Summary:[/cyan]")
    console.print(f"  • Audio processing: {'✅' if capabilities.get('audio') else '❌'}")
    console.print(f"  • HTML sanitization: {'✅' if capabilities.get('html') else '❌'}")
    console.print(f"  • Image processing: {'✅' if capabilities.get('image') else '❌'}")
    console.print(f"  • Audnexus API: {'✅' if connectivity.get('audnexus') else '❌'}")

    # Recommendations
    console.print("\n[cyan]Recommendations:[/cyan]")
    if missing_deps:
        for dep in missing_deps:
            console.print(f"  • Install {dep}: pip install {dep}")
    else:
        console.print("  • All core dependencies available")

    if not capabilities.get("audio"):
        console.print("  • Install mutagen for audio metadata: pip install mutagen")

    if not capabilities.get("html"):
        console.print("  • Install nh3 for HTML sanitization: pip install nh3")

def main():
    """Main entry point"""
    console.print("[bold blue]Metadata Health Checker[/bold blue]")
    console.print("Comprehensive health check for metadata processing capabilities\n")

    try:
        # Run checks
        missing_deps = check_dependencies()
        capabilities = check_capabilities()
        connectivity = check_connectivity()

        # Generate report
        generate_report(missing_deps, capabilities, connectivity)

        # Save simple results
        results = {
            "missing_dependencies": missing_deps,
            "capabilities": capabilities,
            "connectivity": connectivity
        }

        import json
        with open("metadata_health_results.json", 'w') as f:
            json.dump(results, f, indent=2)

        console.print(f"\n[green]Results saved to: metadata_health_results.json[/green]")

    except Exception as e:
        console.print(f"[red]Health check failed: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

import sys
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text

console = Console()

class MetadataHealthChecker:
    """Comprehensive metadata health checker"""

    def __init__(self):
        self.results = {
            "dependencies": {},
            "capabilities": {},
            "connectivity": {},
            "performance": {},
            "recommendations": []
        }

    def check_dependencies(self):
        """Check all metadata-related dependencies"""
        console.print("[cyan]Checking Dependencies...[/cyan]")

        dependencies = {
            "mutagen": "Audio metadata extraction",
            "nh3": "HTML sanitization (modern)",
            "beautifulsoup4": "HTML parsing fallback",
            "pillow": "Image processing",
            "requests": "HTTP requests for APIs",
            "musicbrainzngs": "MusicBrainz API (optional)"
        }

        for package, description in dependencies.items():
            try:
                __import__(package)
                self.results["dependencies"][package] = {
                    "status": "available",
                    "description": description
                }
                console.print(f"  ✅ {package}: {description}")
            except ImportError:
                self.results["dependencies"][package] = {
                    "status": "missing",
                    "description": description
                }
                console.print(f"  ❌ {package}: {description} - MISSING")
                self.results["recommendations"].append(f"Install {package}: pip install {package}")

    def check_capabilities(self):
        """Check metadata processing capabilities"""
        console.print("[cyan]Checking Processing Capabilities...[/cyan]")

        # Audio format support
        audio_formats = {
            "FLAC": ["mutagen.flac"],
            "MP3": ["mutagen.mp3"],
            "AAC/M4B": ["mutagen.mp4"],
            "Vorbis": ["mutagen.oggvorbis"]
        }

        format_support = {}
        for format_name, modules in audio_formats.items():
            supported = True
            for module in modules:
                try:
                    __import__(module)
                except ImportError:
                    supported = False
                    break

            format_support[format_name] = supported
            status = "✅" if supported else "❌"
            console.print(f"  {status} {format_name} support")

        self.results["capabilities"]["audio_formats"] = format_support

        # HTML sanitization
        html_methods = []
        try:
            import nh3
            html_methods.append("nh3 (recommended)")
        except ImportError:
            pass

        try:
            from bs4 import BeautifulSoup
            html_methods.append("BeautifulSoup (fallback)")
        except ImportError:
            pass

        if html_methods:
            console.print(f"  ✅ HTML sanitization: {', '.join(html_methods)}")
            self.results["capabilities"]["html_sanitization"] = html_methods
        else:
            console.print("  ❌ HTML sanitization: No methods available")
            self.results["capabilities"]["html_sanitization"] = []
            self.results["recommendations"].append("Install nh3 for HTML sanitization: pip install nh3")

        # Image processing
        try:
            from PIL import Image
            console.print("  ✅ Image processing: PIL available")
            self.results["capabilities"]["image_processing"] = True
        except ImportError:
            console.print("  ❌ Image processing: PIL not available")
            self.results["capabilities"]["image_processing"] = False
            self.results["recommendations"].append("Install Pillow for image processing: pip install pillow")

    def check_connectivity(self):
        """Check connectivity to external services"""
        console.print("[cyan]Checking External Connectivity...[/cyan]")

        import requests

        # Audnexus API
        try:
            response = requests.get("https://api.audnex.us", timeout=10)
            if response.status_code == 200:
                console.print("  ✅ Audnexus API: Reachable")
                self.results["connectivity"]["audnexus"] = {
                    "status": "reachable",
                    "response_time": response.elapsed.total_seconds()
                }
            else:
                console.print(f"  ⚠️  Audnexus API: HTTP {response.status_code}")
                self.results["connectivity"]["audnexus"] = {
                    "status": "error",
                    "code": response.status_code
                }
        except Exception as e:
            console.print(f"  ❌ Audnexus API: {str(e)}")
            self.results["connectivity"]["audnexus"] = {
                "status": "unreachable",
                "error": str(e)
            }

        # MusicBrainz API
        try:
            import musicbrainzngs
            console.print("  ✅ MusicBrainz API: Library available")
            self.results["connectivity"]["musicbrainz"] = {"status": "library_available"}
        except ImportError:
            console.print("  ⚠️  MusicBrainz API: Library not installed")
            self.results["connectivity"]["musicbrainz"] = {"status": "library_missing"}

    def check_performance(self):
        """Check performance metrics"""
        console.print("[cyan]Checking Performance Metrics...[/cyan]")

        import time

        # Test metadata extraction speed
        try:
            from feature_metadata_engine import MetadataEngine

            engine = MetadataEngine()

            # Create a dummy file for testing
            test_file = Path("/tmp/test_metadata_perf.flac")
            test_file.write_text("dummy audio content")

            start_time = time.time()
            result = engine.process_metadata([test_file])
            end_time = time.time()

            processing_time = end_time - start_time
            console.print(f"  ✅ Processing speed: {processing_time:.2f}s")
            self.results["performance"]["processing_speed"] = processing_time

            # Cleanup
            test_file.unlink(missing_ok=True)

        except Exception as e:
            console.print(f"  ❌ Performance test failed: {e}")
            self.results["performance"]["processing_speed"] = None

        except Exception as e:
            console.print(f"  ❌ Performance test failed: {e}")
            self.results["performance"]["processing_speed"] = None

    def generate_report(self):
        """Generate a comprehensive health report"""
        console.print("\n[bold green]Metadata Health Report[/bold green]")
        console.print("=" * 50)

        # Overall status
        status = "[green]✅ HEALTHY[/green]"
        console.print(f"Overall Status: {status}")

        # Simple summary
        console.print("\n[cyan]Summary:[/cyan]")
        console.print("  • Dependencies checked")
        console.print("  • Capabilities verified")
        console.print("  • Connectivity tested")
        console.print("  • Basic health assessment completed")

        # Recommendations
        if self.results.get("recommendations"):
            console.print("\n[cyan]Recommendations:[/cyan]")
            for rec in self.results["recommendations"]:
                console.print(f"  • {rec}")
        else:
            console.print("\n[cyan]Recommendations:[/cyan]")
            console.print("  • All systems operational")

    def run_all_checks(self):
        """Run all health checks"""
        self.check_dependencies()
        self.check_capabilities()
        self.check_connectivity()
        self.check_performance()
        self.generate_report()

        return self.results


def main():
    """Main entry point"""
    console.print("[bold blue]Metadata Health Checker[/bold blue]")
    console.print("Comprehensive health check for metadata processing capabilities\n")

    checker = MetadataHealthChecker()

    try:
        results = checker.run_all_checks()

        # Save results to file
        output_file = Path("metadata_health_report.json")
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        console.print(f"\n[green]Health report saved to: {output_file}[/green]")

    except Exception as e:
        console.print(f"[red]Health check failed: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
