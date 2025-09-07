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
        stem = p.stem
        date_prefix, cleaned_stem = extract_date_prefix(stem)
        new_stem = slugify(cleaned_stem)

        if date_prefix:
            new_name = f"{date_prefix}--{new_stem}.md"
        else:
            new_name = f"{new_stem}.md"

        if new_name != p.name:
            changes.append((p, new_name))

    return changes


def apply_renames(changes, dry_run=True):
    """Apply the renames."""
    if not changes:
        print("✅ No files need renaming!")
        return

    print(f"{'🔍 PREVIEW' if dry_run else '🔄 APPLYING'} {len(changes)} file renames:")
    print()

    for p, new_name in changes:
        rel_path = p.relative_to(DOCS)
        if dry_run:
            print(f"  {rel_path} -> {rel_path.parent / new_name}")
        else:
            target = p.with_name(new_name)
            if target.exists():
                print(f"⚠️  SKIP: {target.name} already exists")
                continue
            p.rename(target)
            print(f"✅ {p.name} -> {target.name}")


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
