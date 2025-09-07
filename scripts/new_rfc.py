#!/usr/bin/env python3
"""
Create a new Request for Comments (RFC) with proper numbering and template.

Usage: python scripts/new_rfc.py "Proposal Title"
Example: python scripts/new_rfc.py "Metadata Caching Strategy"
"""

import sys
import re
import datetime
import textwrap
from pathlib import Path


def create_rfc(title: str):
    """Create a new RFC with auto-incremented number."""
    if not title:
        print("❌ Please provide a title for the RFC")
        print('Usage: python scripts/new_rfc.py "Proposal Title"')
        sys.exit(1)

    # Create RFC directory if it doesn't exist
    rfc_dir = Path("docs/rfc")
    rfc_dir.mkdir(parents=True, exist_ok=True)

    # Find next RFC number
    existing_rfcs = list(rfc_dir.glob("rfc-*-*.md"))
    numbers = []

    for rfc_file in existing_rfcs:
        match = re.match(r"rfc-(\d{4})-", rfc_file.name)
        if match:
            numbers.append(int(match.group(1)))

    next_number = (max(numbers) + 1) if numbers else 1
    rfc_number = f"{next_number:04d}"

    # Create slug from title
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

    # Generate filename and content
    filename = f"rfc-{rfc_number}-{slug}.md"
    filepath = rfc_dir / filename

    today = datetime.date.today().isoformat()

    content = textwrap.dedent(f"""\
        ---
        title: "RFC-{rfc_number}: {title}"
        status: draft
        author: [H2OKing89]
        reviewers: []
        created: {today}
        updated: {today}
        tags: [RFC, design]
        related: []
        summary: Design proposal for {title.lower()}.
        ---

        ## Summary
        Brief explanation of the feature/change.

        ## Motivation

        ### Problem Statement
        What problem are we solving? What use cases does this support?

        ### Current State
        What is the current approach and why is it insufficient?

        ### Success Criteria
        How will we know this proposal is successful?

        ## Detailed Design

        This is the bulk of the RFC. Explain the design in enough detail for somebody
        familiar with the project to understand and implement.

        ### Architecture Overview
        High-level design and components.

        ### Implementation Details
        Specific implementation approaches and considerations.

        ### API/Interface Changes
        Any changes to existing APIs or new interfaces.

        ## Drawbacks
        Why should we *not* do this? What are the costs?

        ## Rationale and Alternatives

        ### Why This Design
        - Why is this design the best in the space of possible designs?
        - What are the key benefits of this approach?

        ### Alternatives Considered
        - What other designs have been considered?
        - What is the rationale for not choosing them?

        ### Impact of Not Doing This
        What happens if we don't implement this proposal?

        ## Implementation Plan

        ### Phase 1: Foundation
        - [ ] Task 1
        - [ ] Task 2

        ### Phase 2: Core Features
        - [ ] Task 3
        - [ ] Task 4

        ### Phase 3: Polish & Documentation
        - [ ] Task 5
        - [ ] Task 6

        ## Unresolved Questions

        - What parts of the design need to be resolved during RFC review?
        - What parts can be resolved during implementation?
        - What related issues are out of scope but could be addressed later?
        """)

    filepath.write_text(content, encoding="utf-8")

    print(f"✅ Created new RFC: {filepath}")
    print("📝 Edit the file to complete the proposal")

    return filepath


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("❌ Missing RFC title")
        print('Usage: python scripts/new_rfc.py "Proposal Title"')
        print('Example: python scripts/new_rfc.py "Metadata Caching Strategy"')
        sys.exit(1)

    title = " ".join(sys.argv[1:])
    create_rfc(title)


if __name__ == "__main__":
    main()
