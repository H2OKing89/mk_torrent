#!/usr/bin/env python3
"""
Generate docs/readme.md with auto-indexed dashboard of all documentation files.
Includes recent changes, status breakdown, and tag clustering.

Run from repo root: python scripts/gen_docs_index.py
"""

import re
import datetime
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]  # repo root
DOCS = ROOT / "docs"
INDEX = DOCS / "readme.md"

FRONT = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str):
    """Parse YAML front-matter from markdown text."""
    m = FRONT.match(text)
    if not m:
        return {}

    data = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")

            # Handle special cases
            if k == "tags":
                # Parse tags list: [tag1, tag2] or [tag1,tag2]
                tags_match = re.search(r"\[(.*?)\]", v)
                if tags_match:
                    data[k] = [
                        t.strip().strip('"').strip("'")
                        for t in tags_match.group(1).split(",")
                        if t.strip()
                    ]
                else:
                    data[k] = []
            elif k == "related":
                # Skip related for now, it's complex YAML
                data[k] = []
            else:
                data[k] = v

    return data


def generate_dashboard():
    """Generate the enhanced documentation dashboard."""
    items = []
    now = datetime.datetime.now()

    for p in DOCS.rglob("*.md"):
        if p.name.lower() == "readme.md" and p.parent == DOCS:  # skip top index
            continue

        rel = p.relative_to(DOCS)
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        fm = parse_frontmatter(text)
        title = fm.get("title") or p.stem.replace("-", " ").replace("_", " ").title()
        status = fm.get("status", "")
        updated = fm.get("updated")
        tags = fm.get("tags", [])

        if not updated:
            # Fallback to file mtime
            mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime)
            updated = mtime.strftime("%Y-%m-%d")

        # Parse updated timestamp to calculate recency
        try:
            if "T" in updated:
                # ISO format with time - handle timezone offset
                updated_str = updated.replace("Z", "+00:00")
                # Remove timezone colon if present for parsing
                if updated_str.endswith("+00:00") or updated_str.endswith("-00:00"):
                    updated_dt = datetime.datetime.fromisoformat(updated_str)
                else:
                    # Handle formats like 2025-09-06T17:30:00-0500
                    if updated_str[-5:].count(":") == 0 and (
                        "+" in updated_str[-5:] or "-" in updated_str[-5:]
                    ):
                        updated_str = updated_str[:-2] + ":" + updated_str[-2:]
                    updated_dt = datetime.datetime.fromisoformat(updated_str)
                # Convert to naive datetime for comparison
                updated_dt = updated_dt.replace(tzinfo=None)
            else:
                # Date only
                updated_dt = datetime.datetime.strptime(updated, "%Y-%m-%d")
            days_ago = (now - updated_dt).days
        except Exception:
            # Fallback for any parsing errors
            updated_dt = now - datetime.timedelta(days=999)
            days_ago = 999

        items.append(
            {
                "title": title,
                "status": status,
                "updated": updated,
                "updated_dt": updated_dt,
                "days_ago": days_ago,
                "tags": tags,
                "path": str(rel),
                "folder": str(rel.parent) if rel.parent != Path(".") else "root",
            }
        )

    # Sort by update time (newest first)
    items.sort(key=lambda x: x["updated_dt"], reverse=True)

    def status_badge(status):
        """Generate status badge."""
        if not status:
            return ""
        colors = {
            "draft": "yellow",
            "active": "blue",
            "approved": "green",
            "deprecated": "red",
        }
        color = colors.get(status, "gray")
        return f"![{status}](https://img.shields.io/badge/-{status}-{color})"

    def table_section(title, rows, show_folder=False):
        """Generate markdown table section."""
        if not rows:
            return ""

        out = [f"### {title}\n"]

        if show_folder:
            out.extend(
                [
                    "| Title | Status | Updated | Folder | Tags |",
                    "|---|---|---|---|---|",
                ]
            )
            for item in rows:
                tags_str = ", ".join(
                    item["tags"][:3]
                )  # Max 3 tags to keep table readable
                if len(item["tags"]) > 3:
                    tags_str += "..."
                out.append(
                    f"| [{item['title']}]({item['path']}) | {status_badge(item['status'])} | {item['updated'][:10]} | {item['folder']} | {tags_str} |"
                )
        else:
            out.extend(["| Title | Status | Updated | Tags |", "|---|---|---|---|"])
            for item in rows:
                tags_str = ", ".join(item["tags"][:3])
                if len(item["tags"]) > 3:
                    tags_str += "..."
                out.append(
                    f"| [{item['title']}]({item['path']}) | {status_badge(item['status'])} | {item['updated'][:10]} | {tags_str} |"
                )

        out.append("")
        return "\n".join(out)

    # Recent items (last 14 days)
    recent_items = [item for item in items if item["days_ago"] <= 14][:15]

    # Group by status
    by_status = defaultdict(list)
    for item in items:
        status = item["status"] or "unknown"
        by_status[status].append(item)

    # Group by tags (most common tags)
    tag_counts = defaultdict(int)
    by_tag = defaultdict(list)

    for item in items:
        for tag in item["tags"]:
            tag_counts[tag] += 1
            by_tag[tag].append(item)

    # Get top 8 most common tags
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    content = [
        "# mk_torrent Documentation",
        "",
        "_Auto-generated dashboard. Run `python scripts/gen_docs_index.py` to update._",
        "",
        "## Quick Navigation",
        "",
        "- **[Active Work](active/)** - Current development and planning",
        "- **[Summaries](_summaries/)** - Copilot sessions and meeting notes",
        "- **[Core Design](core/)** - Architecture and design documentation",
        "- **[Reference](reference/)** - API docs and external references",
        "- **[ADRs](adr/)** - Architecture Decision Records",
        "- **[RFCs](rfc/)** - Request for Comments / Design Proposals",
        "",
        f"**Total Documents:** {len(items)} • **Updated Today:** {len([i for i in items if i['days_ago'] == 0])} • **This Week:** {len([i for i in items if i['days_ago'] <= 7])}",
        "",
        "---",
        "",
    ]

    # Recent changes section
    if recent_items:
        content.append(
            table_section(
                "📈 Recent Changes (≤14 days)", recent_items, show_folder=True
            )
        )
        content.append("---\n")

    # Status breakdown
    content.append("## 📊 By Status\n")
    status_order = ["active", "draft", "approved", "deprecated", "unknown"]
    for status in status_order:
        if status in by_status:
            status_items = sorted(
                by_status[status], key=lambda x: x["updated_dt"], reverse=True
            )[:10]
            content.append(
                table_section(
                    f"{status.title()} ({len(by_status[status])})", status_items
                )
            )

    content.append("---\n")

    # Top tags
    if top_tags:
        content.append("## 🏷️ By Topic\n")
        for tag, count in top_tags:
            tag_items = sorted(
                by_tag[tag], key=lambda x: x["updated_dt"], reverse=True
            )[:8]
            content.append(table_section(f"{tag} ({count})", tag_items))

    # Footer
    content.extend(
        [
            "---",
            f"_Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by `scripts/gen_docs_index.py`_",
        ]
    )

    INDEX.write_text("\n".join(content), encoding="utf-8")
    print(f"✅ Generated documentation dashboard: {INDEX}")
    print(f"📊 Indexed {len(items)} documents")
    print(f"📈 {len(recent_items)} documents updated in last 14 days")
    print(f"🏷️ {len(top_tags)} most common tags")


if __name__ == "__main__":
    generate_dashboard()
