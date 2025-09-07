# Request for Comments (RFCs)

This directory contains Request for Comments documents - detailed design proposals for significant features or architectural changes.

## Purpose

RFCs are used for:

- Major feature designs that affect multiple components
- API design proposals
- Significant architectural changes
- Cross-cutting concerns that need team input
- External integrations requiring design review

## Format

Each RFC follows this template:

```yaml
---
title: "RFC-NNNN: Brief proposal title"
status: draft | under-review | accepted | rejected | implemented
author: [author-name]
reviewers: [list, of, reviewers]
created: YYYY-MM-DD
updated: 2025-09-06T19:09:40-05:00
tags: [RFC, design, relevant-tags]
related:
  - ../adr/ADR-NNNN-related-decision.md
---

## Summary
Brief explanation of the feature/change.

## Motivation
Why are we doing this? What use cases does it support? What problems does it solve?

## Detailed Design
This is the bulk of the RFC. Explain the design in enough detail for somebody familiar with the project to understand.

## Drawbacks
Why should we *not* do this?

## Rationale and Alternatives
- Why is this design the best in the space of possible designs?
- What other designs have been considered and what is the rationale for not choosing them?
- What is the impact of not doing this?

## Unresolved Questions
- What parts of the design do you expect to resolve through the RFC process before this gets merged?
- What parts of the design do you expect to resolve through the implementation of this feature before stabilization?
- What related issues do you consider out of scope for this RFC that could be addressed in the future independently of the solution that comes out of this RFC?
```

## Naming Convention

- `RFC-0001-metadata-caching-strategy.md`
- `RFC-0002-plugin-architecture-design.md`
- etc.

## Process

1. **Draft**: Author creates RFC in draft status
2. **Review**: Team reviews and provides feedback
3. **Decision**: RFC is accepted/rejected
4. **Implementation**: If accepted, implementation begins
5. **Archive**: Move to implemented status when complete

## Quick Start

Use the VS Code snippet `rfc` + Tab to create a new RFC with the template.
