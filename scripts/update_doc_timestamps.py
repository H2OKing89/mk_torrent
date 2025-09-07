#!/usr/bin/env python3
"""
Update the 'updated:' field in document front-matter to current timestamp.
This ensures metadata stays accurate without manual effort.

Run from repo root: python scripts/update_doc_timestamps.py
"""

import re
import datetime
from pathlib import Path

DOCS = Path("docs")
FM = re.compile(r"^---\n(.*?)\n---", re.DOTALL | re.MULTILINE)
UP = re.compile(r"^updated:\s*.*$", re.MULTILINE)


def get_current_timestamp():
    """Get current timestamp in ISO format with timezone."""
    now = datetime.datetime.now().astimezone()
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S%z")
    # Format timezone offset properly (e.g., -05:00 instead of -0500)
    return f"{timestamp[:-2]}:{timestamp[-2:]}"


def update_doc_timestamps():
    """Update timestamps in all docs with front-matter."""
    updated_count = 0
    now = get_current_timestamp()

    for p in DOCS.rglob("*.md"):
        try:
            txt = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        m = FM.search(txt)
        if not m:
            continue

        fm = m.group(1)

        if "updated:" in fm:
            # Update existing timestamp
            new_fm = UP.sub(f"updated: {now}", fm)
        else:
            # Add timestamp if missing
            new_fm = fm + f"\nupdated: {now}"

        if new_fm != fm:
            new_txt = txt[: m.start()] + f"---\n{new_fm}\n---" + txt[m.end() :]
            p.write_text(new_txt, encoding="utf-8")
            print(f"✅ Updated timestamp in {p.relative_to(DOCS)}")
            updated_count += 1

    if updated_count == 0:
        print("✅ All document timestamps are current!")
    else:
        print(f"✅ Updated {updated_count} document timestamps")


if __name__ == "__main__":
    update_doc_timestamps()
