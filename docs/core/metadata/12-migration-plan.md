# 12) Migration Plan (Low-Risk, Incremental)

## Migration Steps

### 1. Foundation Setup

**Introduce `core/metadata/base.py`** and switch both `engine.py` & `audiobook.py` to import the single Protocol/dataclass.

- Create canonical data models
- Establish protocol interfaces
- Update existing imports
- Maintain backward compatibility

### 2. Service Extraction

**Extract services & sources** from `features/metadata_engine.py` into `core/metadata/services/*` and `sources/*`.

- Move HTML cleaning logic
- Extract format detection
- Separate path parsing
- Isolate Audnexus client

### 3. Dependency Injection

**Wire DI** in `core/metadata/engine.py` and register `audiobook` with these services.

- Implement service container
- Configure dependency injection
- Register service instances
- Update processor constructors

### 4. Merge Implementation

~~**Implement `services/merge_audiobook.py`** and move any hard-coded precedence to config~~ **COMPLETE**

- Create declarative merger
- Implement precedence rules
- Add configuration support
- Test merge scenarios

### 5. Mapper Addition

**Add mappers/red.py**; update `api/trackers/red.py` to consume mapped payloads.

- Implement RED mapper
- Update tracker API
- Test mapping logic
- Validate output format

### 6. Test Refactoring

**Refactor tests**: split current monolithic test into unit suites; keep integration test for e2e sanity.

- Split into unit tests
- Create integration tests
- Add test fixtures
- Maintain test coverage

### 7. Compatibility Layer

**Compatibility shim**: if needed, re-export `MetadataEngine` from `features/__init__.py` for one release.

- Create re-export layer
- Maintain API compatibility
- Add deprecation warnings
- Document migration path

### 8. Cleanup

**Delete old monolith** once downstream imports are migrated.

- Remove old code
- Clean up imports
- Update documentation
- Celebrate success

## Risk Mitigation

### Incremental Approach

- Each step is independently deployable
- Rollback capability at each stage
- Minimal breaking changes
- Gradual feature migration

### Testing Strategy

- Comprehensive test suite
- Integration test coverage
- Regression test prevention
- Performance validation

### Compatibility Maintenance

- Backward compatibility shims
- Gradual deprecation warnings
- Clear migration documentation
- User communication plan

## Success Criteria

### Functional Requirements

- All existing functionality preserved
- Performance maintained or improved
- New features easily addable
- Clean separation of concerns

### Quality Metrics

- Test coverage maintained
- Code quality improved
- Documentation complete
- Developer experience enhanced
