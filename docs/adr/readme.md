# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records - lightweight documents that capture important architectural decisions along with their context and consequences.

## Format

Each ADR follows this template:

```yaml
---
title: "ADR-NNNN: Brief decision title"
status: proposed | accepted | deprecated | superseded
deciders: [list, of, people]
date: YYYY-MM-DD
tags: [ADR, architecture, relevant-tags]
supersedes: ADR-NNNN (if applicable)
superseded-by: ADR-NNNN (if applicable)
updated: 2025-09-06T19:14:05-05:00
---

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-NNNN]

## Context
What is the issue that we're seeing that is motivating this decision or change?

## Decision
What is the change that we're proposing and/or doing?

## Consequences
What becomes easier or more difficult to do because of this change?

## Alternatives Considered
What other options did we look at?
```

## Naming Convention

- `ADR-0001-choose-metadata-validation-library.md`
- `ADR-0002-tracker-upload-authentication.md`
- etc.

## Quick Start

Use the VS Code snippet `adr` + Tab to create a new ADR with the template.
