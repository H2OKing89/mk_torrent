#!/usr/bin/env python3
"""
Fix timestamp casing in documentation filenames.
Ensures timestamps use uppercase 'T': 20250906T1730 (not 20250906t1730)

Run from repo root: python scripts/fix_timestamp_T.py
"""

import re
from pathlib import Path

DOCS = Path("docs")
PAT = re.compile(r"(\d{8})t(\d{4,6})(-)")  # YYYYMMDDtHHMM-...


def fix_timestamp_casing():
    """Fix lowercase 't' to uppercase 'T' in timestamp filenames."""
    fixed = 0

    for p in DOCS.rglob("*.md"):
        path_str = str(p)
        new_path_str = PAT.sub(
            lambda m: f"{m.group(1)}T{m.group(2)}{m.group(3)}", path_str
        )

        if new_path_str != path_str:
            target = Path(new_path_str)
            print(f"✅ {p.name} -> {target.name}")
            p.rename(target)
            fixed += 1

    if fixed == 0:
        print("✅ No timestamp casing issues found!")
    else:
        print(f"✅ Fixed {fixed} timestamp casing issues")


if __name__ == "__main__":
    fix_timestamp_casing()
