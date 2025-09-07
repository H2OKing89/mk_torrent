#!/usr/bin/env python3
"""
Archive stale documents from docs/active/ to keep the active folder lean and focused.
Documents untouched for more than MAX_DAYS are moved to archive/completed/.

Usage: python scripts/auto_archive_active.py [--max-days N] [--dry-run]
"""

import datetime
import shutil
import argparse
from pathlib import Path


def auto_archive_active(max_days: int = 30, dry_run: bool = False):
    """Archive stale documents from active/ folder."""
    active_dir = Path("docs/active")
    archive_dir = Path("docs/archive/completed")

    if not active_dir.exists():
        print("❌ docs/active/ directory not found")
        return

    # Ensure archive directory exists
    archive_dir.mkdir(parents=True, exist_ok=True)

    cutoff_timestamp = datetime.datetime.now().timestamp() - (max_days * 24 * 3600)
    moved_count = 0

    print(f"🔍 Checking docs/active/ for files older than {max_days} days...")

    for doc_file in active_dir.glob("*.md"):
        file_mtime = doc_file.stat().st_mtime
        days_old = (datetime.datetime.now().timestamp() - file_mtime) / (24 * 3600)

        if file_mtime < cutoff_timestamp:
            target_file = archive_dir / doc_file.name

            if dry_run:
                print(f"📁 Would archive: {doc_file.name} ({days_old:.1f} days old)")
            else:
                # Check if target already exists
                if target_file.exists():
                    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    target_file = archive_dir / f"{doc_file.stem}-{timestamp}.md"

                shutil.move(str(doc_file), str(target_file))
                print(
                    f"✅ Archived: {doc_file.name} -> archive/completed/{target_file.name}"
                )

            moved_count += 1

    if moved_count == 0:
        print("✅ No stale documents found in docs/active/")
    else:
        action = "Would archive" if dry_run else "Archived"
        print(f"📊 {action} {moved_count} documents")

        if not dry_run:
            print(
                "💡 Run 'python scripts/gen_docs_index.py' to update the documentation index"
            )


def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Archive stale documents from docs/active/"
    )
    parser.add_argument(
        "--max-days",
        type=int,
        default=30,
        help="Archive docs older than N days (default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be archived without actually moving files",
    )

    args = parser.parse_args()

    auto_archive_active(max_days=args.max_days, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
