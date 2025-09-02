#!/usr/bin/env python3
"""
Test runner script with organized output to test_results directory.
This script provides convenient commands for running tests and managing test results.
Updated for src layout.
"""

import subprocess
import sys
from pathlib import Path
import argparse
import shutil

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def run_tests(test_path=None, verbose=True, coverage=True):
    """Run pytest with organized output to test_results directory."""
    cmd = ["python", "-m", "pytest"]

    if test_path:
        cmd.append(test_path)

    if verbose:
        cmd.extend(["-v", "--tb=short"])

    # Add src to Python path for testing
    env = {"PYTHONPATH": str(Path(__file__).parent / "src")}
    
    # The pytest configuration in pyproject.toml will handle the output directories
    console.print("[cyan]Running tests with output to test_results/ directory...[/cyan]")
    result = subprocess.run(cmd, cwd=Path(__file__).parent, env=env)
    return result.returncode

def clean_results():
    """Clean up test results directory."""
    results_dir = Path("test_results")
    if results_dir.exists():
        console.print("[yellow]Cleaning test results directory...[/yellow]")
        shutil.rmtree(results_dir)
        results_dir.mkdir()
        console.print("[green]✅ Test results directory cleaned[/green]")
    else:
        console.print("[dim]Test results directory doesn't exist[/dim]")

def show_results():
    """Show available test result files."""
    results_dir = Path("test_results")
    if results_dir.exists():
        files = list(results_dir.glob("*"))
        if files:
            table = Table(title="📊 Test Result Files", show_header=True, header_style="bold cyan")
            table.add_column("Type", style="cyan", no_wrap=True)
            table.add_column("Name", style="white")
            table.add_column("Size/Details", style="dim")
            
            for file in sorted(files):
                if file.is_file():
                    size = file.stat().st_size
                    table.add_row("📄", file.name, f"{size} bytes")
                elif file.is_dir():
                    items = list(file.glob("*"))
                    table.add_row("📁", f"{file.name}/", f"{len(items)} items")
            
            console.print(table)
        else:
            console.print("[yellow]No test result files found[/yellow]")
    else:
        console.print("[red]Test results directory doesn't exist[/red]")

def main():
    parser = argparse.ArgumentParser(description="Test runner with organized output")
    parser.add_argument("command", choices=["run", "clean", "show", "all"],
                       help="Command to execute")
    parser.add_argument("test_path", nargs="?", help="Specific test path to run")
    parser.add_argument("--no-coverage", action="store_true",
                       help="Skip coverage reporting")

    args = parser.parse_args()

    if args.command == "run":
        coverage = not args.no_coverage
        exit_code = run_tests(args.test_path, coverage=coverage)
        if exit_code == 0:
            console.print("\n[green]✅ All tests passed![/green]")
            show_results()
        else:
            console.print(f"\n[red]❌ Tests failed with exit code {exit_code}[/red]")
        sys.exit(exit_code)

    elif args.command == "clean":
        clean_results()

    elif args.command == "show":
        show_results()

    elif args.command == "all":
        console.print("[bold cyan]Running full test suite...[/bold cyan]")
        clean_results()
        exit_code = run_tests(coverage=True)
        if exit_code == 0:
            console.print("\n[green]✅ All tests passed![/green]")
        show_results()
        sys.exit(exit_code)

if __name__ == "__main__":
    main()
