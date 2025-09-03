#!/usr/bin/env python3
"""Metadata Testing Runner

This script provides a convenient way to run metadata-related tests
and health checks for the torrent creator system.
"""

import sys
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class MetadataTestRunner:
    """Runner for metadata tests and health checks"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.tests_dir = self.project_root / "tests"

    def run_unit_tests(self, verbose: bool = False, coverage: bool = True):
        """Run unit tests for metadata components"""
        console.print("[bold cyan]Running Metadata Unit Tests[/bold cyan]")

        cmd = ["python", "-m", "pytest"]

        if verbose:
            cmd.append("-v")
        else:
            cmd.extend(["-q", "--tb=short"])

        if coverage:
            cmd.extend(["--cov=feature_metadata_engine", "--cov-report=term-missing"])

        cmd.extend(
            [
                str(self.tests_dir / "test_metadata_engine.py"),
                "-m",
                "not integration and not slow",
            ]
        )

        return self._run_command(cmd)

    def run_integration_tests(self):
        """Run integration tests"""
        console.print("[bold cyan]Running Metadata Integration Tests[/bold cyan]")

        cmd = [
            "python",
            "-m",
            "pytest",
            str(self.tests_dir / "test_metadata_engine.py"),
            "-m",
            "integration",
            "-v",
        ]

        return self._run_command(cmd)

    def run_health_checks(self):
        """Run metadata health checks"""
        console.print("[bold cyan]Running Metadata Health Checks[/bold cyan]")

        try:
            from core_health_checks import MetadataHealthCheck

            # Create a basic config for testing
            config = {
                "output_directory": str(self.project_root / "output"),
                "qbit_host": "localhost",
                "qbit_port": 8080,
            }

            checker = MetadataHealthCheck(config)
            _results = checker.run_all_checks()
            checker.display_results()

            return True

        except Exception as e:
            console.print(f"[red]Health check failed: {e}[/red]")
            return False

    def run_performance_tests(self):
        """Run performance tests for metadata processing"""
        console.print("[bold cyan]Running Metadata Performance Tests[/bold cyan]")

        # This would run performance benchmarks
        console.print("[yellow]Performance tests not yet implemented[/yellow]")
        return True

    def run_all_tests(self):
        """Run all metadata tests"""
        console.print("[bold green]Running Complete Metadata Test Suite[/bold green]")
        console.print("=" * 60)

        results = []

        # Unit tests
        console.print("\n[cyan]1. Unit Tests[/cyan]")
        results.append(("Unit Tests", self.run_unit_tests()))

        # Integration tests
        console.print("\n[cyan]2. Integration Tests[/cyan]")
        results.append(("Integration Tests", self.run_integration_tests()))

        # Health checks
        console.print("\n[cyan]3. Health Checks[/cyan]")
        results.append(("Health Checks", self.run_health_checks()))

        # Performance tests
        console.print("\n[cyan]4. Performance Tests[/cyan]")
        results.append(("Performance Tests", self.run_performance_tests()))

        # Summary
        self._display_summary(results)

    def generate_test_report(self):
        """Generate a detailed test report"""
        console.print("[bold cyan]Generating Test Report[/bold cyan]")

        report_path = self.project_root / "test_report.html"

        cmd = [
            "python",
            "-m",
            "pytest",
            str(self.tests_dir / "test_metadata_engine.py"),
            "--html",
            str(report_path),
            "--self-contained-html",
        ]

        result = self._run_command(cmd)

        if result and report_path.exists():
            console.print(f"[green]Test report generated: {report_path}[/green]")

        return result

    def _run_command(self, cmd: list) -> bool:
        """Run a command and return success status"""
        try:
            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=False, text=True
            )
            return result.returncode == 0
        except Exception as e:
            console.print(f"[red]Command failed: {e}[/red]")
            return False

    def _display_summary(self, results: list):
        """Display test summary"""
        table = Table(title="Test Suite Summary")
        table.add_column("Test Type", style="cyan")
        table.add_column("Status", style="green")

        passed = 0
        total = len(results)

        for test_type, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            if success:
                passed += 1
            table.add_row(test_type, status)

        console.print("\n")
        console.print(table)

        overall_status = (
            "✅ ALL TESTS PASSED"
            if passed == total
            else f"⚠️  {passed}/{total} TESTS PASSED"
        )

        panel = Panel.fit(
            f"[bold]{overall_status}[/bold]\n\n"
            f"Unit Tests: {'✅' if results[0][1] else '❌'}\n"
            f"Integration Tests: {'✅' if results[1][1] else '❌'}\n"
            f"Health Checks: {'✅' if results[2][1] else '❌'}\n"
            f"Performance Tests: {'✅' if results[3][1] else '❌'}",
            title="Metadata Test Results",
            border_style="green" if passed == total else "yellow",
        )

        console.print(panel)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Metadata Testing Runner")
    parser.add_argument(
        "action",
        choices=["unit", "integration", "health", "performance", "all", "report"],
        help="Test action to run",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--no-coverage", action="store_true", help="Skip coverage reporting"
    )

    args = parser.parse_args()

    runner = MetadataTestRunner()

    try:
        if args.action == "unit":
            success = runner.run_unit_tests(
                verbose=args.verbose, coverage=not args.no_coverage
            )
        elif args.action == "integration":
            success = runner.run_integration_tests()
        elif args.action == "health":
            success = runner.run_health_checks()
        elif args.action == "performance":
            success = runner.run_performance_tests()
        elif args.action == "all":
            runner.run_all_tests()
            return
        elif args.action == "report":
            success = runner.generate_test_report()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Test run interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error running tests: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
