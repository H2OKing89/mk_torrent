# 1) Goals

**Single, canonical metadata engine** that is easy to extend.

## Core Objectives

* **Single, canonical metadata engine** that is easy to extend.
* Clean separation of **content processors** (audiobook/music/video), **sources** (embedded tags, Audnexus API), and **services** (HTML cleaning, format detection, image discovery, tag normalization).
* **Deterministic merging** of multiple sources with precedence rules.
* **Strict-but-friendly validation** with actionable error/warning output for tracker requirements (starting with RED).
* A **stable internal model** (dataclass / pydantic) that downstreams (trackers, CLI, workflows) can rely on.
* **Unit-testable modules** with fast, IO-light tests; integration tests for end-to-end sanity.

## Design Principles

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Extensibility**: New content types, sources, and trackers can be added without modifying existing code
3. **Testability**: All components are designed for isolated unit testing
4. **Determinism**: Same input always produces same output
5. **User-Friendly**: Clear error messages and actionable feedback
6. **Performance**: Fast execution with minimal I/O and network calls
