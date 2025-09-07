#!/usr/bin/env python3
"""
Convenience script to run all documentation organization tasks.
Run this when you want to clean up and organize documentation.

Usage: python scripts/organize_docs.py
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and report success/failure."""
    print(f"🔄 {description}...")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   {e.stderr}")
        return False


def main():
    """Run all documentation organization tasks."""
    if not Path("docs").exists():
        print("❌ docs/ directory not found. Run from repository root.")
        sys.exit(1)

    print("📚 Organizing documentation...")
    print()

    tasks = [
        (["python", "scripts/rename_docs.py", "--apply"], "Organizing document files"),
        (["python", "scripts/update_doc_timestamps.py"], "Updating timestamps"),
        (["python", "scripts/gen_docs_index.py"], "Regenerating documentation index"),
    ]

    success_count = 0
    for cmd, desc in tasks:
        if run_command(cmd, desc):
            success_count += 1
        print()

    if success_count == len(tasks):
        print("🎉 All documentation tasks completed successfully!")
        print("💡 Review the changes and commit when ready.")
    else:
        print(
            f"⚠️  {len(tasks) - success_count} task(s) failed. Check the errors above."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
