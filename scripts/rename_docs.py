#!/usr/bin/env python3
"""
Bulk rename documentation files to follow naming conventions:
- Convert spaces and em-dashes to kebab-case
- Extract dates and prefix them as YYYYMMDD--
- Remove underscores and normalize casing

Run from repo root: python scripts/rename_docs.py
Commit first - this is a one-way operation!
"""

import re
from pathlib import Path

DOCS = Path("docs")
DATE = re.compile(r"(20\d{2})[-_](\d{2})[-_](\d{2})")
BAD_CHARS = " —_"  # space, emdash, underscore


def slugify(stem: str) -> str:
    """Convert filename to kebab-case."""
    # Replace bad chars with hyphens
    s = stem
    for char in BAD_CHARS:
        s = s.replace(char, "-")

    # Remove non-alphanumeric except hyphens and dots
    s = re.sub(r"[^a-zA-Z0-9\-\.]+", "-", s)

    # Collapse multiple hyphens
    s = re.sub(r"-{2,}", "-", s)

    # Strip leading/trailing hyphens and lowercase
    return s.strip("-").lower()


def extract_date_prefix(stem: str) -> tuple[str, str]:
    """Extract date and return (date_prefix, cleaned_stem)."""
    m = DATE.search(stem)
    if m:
        date_prefix = f"{m.group(1)}{m.group(2)}{m.group(3)}"
        cleaned_stem = DATE.sub("", stem).strip("-_ ")
        return date_prefix, cleaned_stem
    return None, stem


def preview_renames():
    """Show what files would be renamed."""
    changes = []

    for p in DOCS.rglob("*.md"):
        # Skip files already in _summaries directory
        if "_summaries" in str(p):
            continue

        stem = p.stem
        date_prefix, cleaned_stem = extract_date_prefix(stem)
        new_stem = slugify(cleaned_stem)

        # Special handling for summary documents
        if "summary" in new_stem.lower():
            if date_prefix:
                # Use existing date from filename
                year = date_prefix[:4]
                month = date_prefix[4:6]
                summaries_dir = DOCS / "_summaries" / year / f"{year}-{month}"
                # Extract time if present, otherwise use 0000
                if len(date_prefix) >= 8:
                    time_part = date_prefix[8:] if len(date_prefix) > 8 else "0000"
                    new_name = f"{date_prefix[:8]}T{time_part.zfill(4)}--{new_stem}.md"
                else:
                    new_name = f"{date_prefix}T0000--{new_stem}.md"
                target_path = summaries_dir / new_name
                changes.append((p, target_path))
                continue
            else:
                # Check if filename already has a date pattern like "20250902--session-summary"
                filename_date_match = re.search(r"(\d{8})", p.name)
                if filename_date_match:
                    existing_date = filename_date_match.group(1)
                    year = existing_date[:4]
                    month = existing_date[4:6]
                    summaries_dir = DOCS / "_summaries" / year / f"{year}-{month}"
                    new_name = f"{existing_date}T0000--{new_stem}.md"
                    target_path = summaries_dir / new_name
                    changes.append((p, target_path))
                    continue

                # Add current date for truly undated summaries
                from datetime import datetime

                now = datetime.now()
                date_prefix = now.strftime("%Y%m%d")
                summaries_dir = (
                    DOCS / "_summaries" / str(now.year) / f"{now.year}-{now.month:02d}"
                )
                new_name = f"{date_prefix}T0000--{new_stem}.md"
                target_path = summaries_dir / new_name
                changes.append((p, target_path))
                continue

        # Regular document renaming
        if date_prefix:
            new_name = f"{date_prefix}--{new_stem}.md"
        else:
            new_name = f"{new_stem}.md"

        if new_name != p.name:
            changes.append((p, p.parent / new_name))

    return changes


def apply_renames(changes, dry_run=True):
    """Apply the renames."""
    if not changes:
        print("✅ No files need renaming!")
        return

    print(f"{'🔍 PREVIEW' if dry_run else '🔄 APPLYING'} {len(changes)} file renames:")
    print()

    for p, target in changes:
        rel_path = p.relative_to(DOCS)

        if isinstance(target, str):
            # Handle legacy case where target was just a filename
            target_path = p.parent / target
            target_rel = target_path.relative_to(DOCS)
        else:
            # New case where target is a full Path
            target_path = target
            target_rel = (
                target_path.relative_to(DOCS)
                if target_path.is_relative_to(DOCS)
                else target_path
            )

        if dry_run:
            print(f"  {rel_path} -> {target_rel}")
        else:
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            if target_path.exists():
                print(f"⚠️  SKIP: {target_path.name} already exists")
                continue
            p.rename(target_path)
            print(f"✅ {p.name} -> {target_rel}")


def main():
    """Main entry point."""
    import sys

    if not DOCS.exists():
        print("❌ docs/ directory not found. Run from repository root.")
        sys.exit(1)

    changes = preview_renames()

    if len(sys.argv) > 1 and sys.argv[1] == "--apply":
        apply_renames(changes, dry_run=False)
    else:
        apply_renames(changes, dry_run=True)
        print()
        print("👆 This is a preview. To apply changes, run:")
        print("   python scripts/rename_docs.py --apply")
        print()
        print("⚠️  Commit your changes first - this operation cannot be undone!")


if __name__ == "__main__":
    main()
