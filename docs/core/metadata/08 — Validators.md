# 8) Validators

## Validation Architecture

Validators provide quality assurance and completeness scoring for metadata. They operate in two layers: common validation primitives and content-specific checks.

## Validator Modules

### Common Validators (`validators/common.py`)
Primitives for basic validation:
- `is_year` - Year range validation
- `is_language_iso` - ISO language code validation
- Duration sanity checks
- Non-empty field validation
- String length constraints

### Content-Specific Validators (`validators/audiobook_validator.py`)
Content-specific checks + tracker hints:
- Required field validation
- Field format validation
- Tracker-specific requirements (e.g., RED wants `album` present → we default to `title`)
- Cross-field validation logic

## Validation Output Format

Return shape:

```json
{
  "valid": true,
  "errors": ["Missing author"],
  "warnings": ["Unusual year: 2099"],
  "completeness": 0.78
}
```

### Field Descriptions

- **valid**: Boolean indicating if metadata meets minimum requirements
- **errors**: Array of critical issues that prevent use
- **warnings**: Array of non-critical issues that should be addressed
- **completeness**: Float 0.0-1.0 indicating how complete the metadata is

## Validation Principles

### Strict but Friendly
- Clear, actionable error messages
- Warnings for non-critical issues
- Helpful suggestions for fixes

### Tracker-Aware
- Hint at tracker-specific requirements
- But remain tracker-agnostic at core
- Extensible for new tracker requirements

### Graduated Response
- Distinguish between errors and warnings
- Provide completeness scoring
- Allow partial success scenarios

## Validation Workflow

1. **Basic Validation**: Check required fields and formats
2. **Content Validation**: Apply content-type specific rules
3. **Tracker Hints**: Add tracker-specific guidance
4. **Completeness Scoring**: Calculate overall quality score
5. **Result Assembly**: Package errors, warnings, and score

## Future Extensions

- Custom validation rules via configuration
- Plugin-based validator extensions
- Validation rule versioning
- Validation performance metrics
