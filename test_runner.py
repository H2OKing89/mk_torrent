#!/usr/bin/env python3
"""
Test runner script with organized output to test_results directory.
This script provides convenient commands for running tests and managing test results.
"""

import subprocess
import sys
from pathlib import Path
import argparse
import shutil

def run_tests(test_path=None, verbose=True, coverage=True):
    """Run pytest with organized output to test_results directory."""
    cmd = ["python", "-m", "pytest"]

    if test_path:
        cmd.append(test_path)

    if verbose:
        cmd.extend(["-v", "--tb=short"])

    # The pytest configuration in pyproject.toml will handle the output directories
    print("Running tests with output to test_results/ directory...")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode

def clean_results():
    """Clean up test results directory."""
    results_dir = Path("test_results")
    if results_dir.exists():
        print("Cleaning test results directory...")
        shutil.rmtree(results_dir)
        results_dir.mkdir()
        print("✅ Test results directory cleaned")
    else:
        print("Test results directory doesn't exist")

def show_results():
    """Show available test result files."""
    results_dir = Path("test_results")
    if results_dir.exists():
        files = list(results_dir.glob("*"))
        if files:
            print("Available test result files:")
            for file in sorted(files):
                if file.is_file():
                    size = file.stat().st_size
                    print(f"  📄 {file.name} ({size} bytes)")
                elif file.is_dir():
                    items = list(file.glob("*"))
                    print(f"  📁 {file.name}/ ({len(items)} items)")
        else:
            print("No test result files found")
    else:
        print("Test results directory doesn't exist")

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
            print("\n✅ All tests passed!")
            show_results()
        else:
            print(f"\n❌ Tests failed with exit code {exit_code}")
        sys.exit(exit_code)

    elif args.command == "clean":
        clean_results()

    elif args.command == "show":
        show_results()

    elif args.command == "all":
        print("Running full test suite...")
        clean_results()
        exit_code = run_tests(coverage=True)
        if exit_code == 0:
            print("\n✅ All tests passed!")
        show_results()
        sys.exit(exit_code)

if __name__ == "__main__":
    main()
