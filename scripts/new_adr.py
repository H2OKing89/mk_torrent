#!/usr/bin/env python3
"""
Create a new Architecture Decision Record (ADR) with proper numbering and template.

Usage: python scripts/new_adr.py "Decision Title"
Example: python scripts/new_adr.py "Adopt Redis for caching"
"""

import sys
import re
import datetime
import textwrap
from pathlib import Path


def create_adr(title: str):
    """Create a new ADR with auto-incremented number."""
    if not title:
        print("❌ Please provide a title for the ADR")
        print('Usage: python scripts/new_adr.py "Decision Title"')
        sys.exit(1)

    # Create ADR directory if it doesn't exist
    adr_dir = Path("docs/adr")
    adr_dir.mkdir(parents=True, exist_ok=True)

    # Find next ADR number
    existing_adrs = list(adr_dir.glob("adr-*-*.md"))
    numbers = []

    for adr_file in existing_adrs:
        match = re.match(r"adr-(\d{4})-", adr_file.name)
        if match:
            numbers.append(int(match.group(1)))

    next_number = (max(numbers) + 1) if numbers else 1
    adr_number = f"{next_number:04d}"

    # Create slug from title
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

    # Generate filename and content
    filename = f"adr-{adr_number}-{slug}.md"
    filepath = adr_dir / filename

    today = datetime.date.today().isoformat()

    content = textwrap.dedent(f"""\
        ---
        title: "ADR-{adr_number}: {title}"
        status: draft
        deciders: [H2OKing89]
        date: {today}
        tags: [ADR, architecture]
        related: []
        summary: Architecture decision for {title.lower()}.
        ---

        ## Status
        Draft

        ## Context
        What is the issue that we're seeing that is motivating this decision or change?

        ## Decision
        What is the change that we're proposing and/or doing?

        ## Consequences

        ### Positive
        - What becomes easier or more effective?

        ### Negative
        - What becomes more difficult or complex?

        ## Alternatives Considered

        ### Alternative 1
        - **Pros**: Benefits of this approach
        - **Cons**: Drawbacks of this approach

        ### Alternative 2
        - **Pros**: Benefits of this approach
        - **Cons**: Drawbacks of this approach
        """)

    filepath.write_text(content, encoding="utf-8")

    print(f"✅ Created new ADR: {filepath}")
    print("📝 Edit the file to complete the decision record")

    return filepath


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("❌ Missing ADR title")
        print('Usage: python scripts/new_adr.py "Decision Title"')
        print('Example: python scripts/new_adr.py "Adopt Redis for caching"')
        sys.exit(1)

    title = " ".join(sys.argv[1:])
    create_adr(title)


if __name__ == "__main__":
    main()
