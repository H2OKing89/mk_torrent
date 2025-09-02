#!/usr/bin/env python3
"""Metadata Health Check Script

This script performs comprehensive health checks for metadata processing
capabilities in the torrent creator system.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text

console = Console()

class MetadataHealthChecker:
    """Comprehensive metadata health checker"""

    def __init__(self):
        self.results: Dict[str, Any] = {
            "dependencies": {},
            "capabilities": {},
            "connectivity": {},
            "performance": {},
            "recommendations": []
        }

    def check_dependencies(self):
        """Check all metadata-related dependencies"""
        console.print("[cyan]Checking Dependencies...[/cyan]")

        # Map package names to their import names
        dependencies = {
            "mutagen": ("mutagen", "Audio metadata extraction"),
            "nh3": ("nh3", "HTML sanitization (modern)"),
            "beautifulsoup4": ("bs4", "HTML parsing fallback"),
            "pillow": ("PIL", "Image processing"),
            "requests": ("requests", "HTTP requests for APIs"),
            "musicbrainzngs": ("musicbrainzngs", "MusicBrainz API (optional)")
        }

        for package, (import_name, description) in dependencies.items():
            try:
                __import__(import_name)
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

        # Audnexus API - check if service is available (may return 404 for root endpoint)
        try:
            # Try the base URL first
            response = requests.get("https://api.audnex.us", timeout=10)
            if response.status_code == 200:
                console.print("  ✅ Audnexus API: Reachable")
                self.results["connectivity"]["audnexus"] = {
                    "status": "reachable",
                    "response_time": response.elapsed.total_seconds()
                }
            elif response.status_code == 404:
                # 404 is expected for root endpoint, try a sample book endpoint
                sample_response = requests.get("https://api.audnex.us/books/B0F2B3RZ32?update=1", timeout=10)
                if sample_response.status_code == 200:
                    console.print("  ✅ Audnexus API: Available (sample endpoint)")
                    self.results["connectivity"]["audnexus"] = {
                        "status": "available",
                        "note": "Root endpoint returns 404 but API is functional"
                    }
                else:
                    console.print("  ⚠️  Audnexus API: Limited availability")
                    self.results["connectivity"]["audnexus"] = {
                        "status": "limited",
                        "note": "API may be experiencing issues"
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
            console.print(f"  ⚠️  Performance test failed: {str(e)}")
            self.results["performance"]["processing_speed"] = None
            self.results["recommendations"].append("Performance testing requires working metadata engine")

    def generate_report(self):
        """Generate comprehensive health report"""
        console.print("\n[bold green]Metadata Health Report[/bold green]")
        console.print("=" * 50)

        # Overall status
        critical_issues = 0
        for dep, info in self.results["dependencies"].items():
            if info["status"] == "missing":
                critical_issues += 1

        if critical_issues == 0:
            status = "[green]✅ HEALTHY[/green]"
        elif critical_issues <= 2:
            status = "[yellow]⚠️  WARNING[/yellow]"
        else:
            status = "[red]❌ CRITICAL[/red]"

        console.print(f"Overall Status: {status}")
        console.print(f"Critical Issues: {critical_issues}")

        # Recommendations
        if self.results["recommendations"]:
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
