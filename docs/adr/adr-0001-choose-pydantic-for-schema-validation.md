---
title: "ADR-0001: Choose Pydantic for schema validation"
status: accepted
deciders: [H2OKing89]
date: 2025-09-06
tags: [ADR, architecture, validation, pydantic]
updated: 2025-09-06T19:14:05-05:00
---

## Status

Accepted

## Context

The mk_torrent project needs robust data validation for:

- Metadata structures from various sources (Audnexus, file paths, embedded tags)
- Configuration validation
- API request/response validation
- Cross-tracker field mapping validation

We need a solution that provides:

- Type safety with Python type hints
- Automatic validation with clear error messages
- Serialization/deserialization support
- Integration with modern Python tooling

## Decision

We will use **Pydantic v2** as our primary schema validation library.

Pydantic will be used for:

- All data models in the metadata engine
- Configuration schema validation
- API request/response models
- Tracker-specific field mapping schemas

## Consequences

### Positive

- **Type Safety**: Full integration with mypy and modern type checking
- **Performance**: Pydantic v2 is built on Rust for speed
- **Developer Experience**: Clear validation errors with field-level detail
- **Ecosystem**: Excellent integration with FastAPI, pytest, and other tools
- **Maintainability**: Self-documenting schemas with automatic docs generation

### Negative

- **Learning Curve**: Team needs to learn Pydantic patterns and validators
- **Dependency**: Adds external dependency (though widely adopted)
- **Migration Effort**: Existing validation code needs refactoring

## Alternatives Considered

### attrs + validators

- **Pros**: Lightweight, minimal dependencies
- **Cons**: More manual validation code, less ecosystem integration

### dataclasses + custom validation

- **Pros**: Built-in to Python, no dependencies
- **Cons**: Requires significant custom validation infrastructure

### cerberus

- **Pros**: Flexible validation rules
- **Cons**: Schema-based rather than type-based, less IDE support

### marshmallow

- **Pros**: Mature serialization library
- **Cons**: More complex API, less type safety integration
