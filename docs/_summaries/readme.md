# Summary Documentation System

This directory contains organized summaries from Copilot sessions, code reviews, and project discussions.

## Structure

```
docs/_summaries/
├── YYYY/                    # Year folders
│   └── YYYY-MM/            # Month folders
│       └── YYYYMMDDThhmm--summary-title.md
├── readme.md               # This file
└── template.md            # Template for new summaries
```

## File Naming Convention

Use **ISO-8601 basic format** for automatic chronological sorting:

- Format: `YYYYMMDDThhmm--descriptive-title.md`
- Example: `20250906T1730--metadata-core-modularization-summary.md`

## Quick Start

1. **Create new summary**: Type `sumdoc` + Tab in any `.md` file
2. **Quick note**: Type `qsum` + Tab for brief summaries
3. **Find summaries**: Explorer sorts by modified date (newest first)

## VS Code Snippets Available

- **`sumdoc`** - Full summary template with front-matter
- **`qsum`** - Quick summary for brief notes

## Front-matter Fields

- **title**: Short, searchable title
- **project**: Always `mk_torrent` for this repo
- **source**: Where this came from (Copilot Chat, PR Review, etc.)
- **created/updated**: ISO timestamps
- **tags**: Categories for filtering
- **links**: Related URLs, PRs, issues

## Tips

- Use descriptive titles that you'll remember
- Tag consistently: `backend`, `infra`, `docs`, `tests`, `bug`, `design`, `metadata`, `torrent`, `validation`
- Update the `updated` field when making changes
- Reference specific files/functions in Artifacts section
