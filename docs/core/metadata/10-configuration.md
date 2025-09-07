# 10) Configuration

## Configuration Architecture

Add metadata config under `config.py` or a `metadata.yaml`:

## Configuration Categories

### Source Precedence

* `source_precedence` (per field).
* Configurable priority ordering for different metadata sources
* Field-specific precedence rules
* Runtime precedence override support

### Sanitization Settings

* `sanitization` level (strict/relaxed).
* HTML cleaning configuration
* Text normalization rules
* Character encoding preferences

### Validation Rules

* `year_bounds` or `year_drift_warn`.
* Required vs recommended field configuration
* Completeness scoring weights
* Tracker-specific validation profiles

### External Service Configuration

* `audnexus` timeouts/retries, rate limits.
* API endpoint configuration
* Authentication settings
* Caching preferences

### Format Detection

* `format_detector` strictness (require mutagen or degrade gracefully).
* Fallback behavior configuration
* Quality assessment thresholds
* Format priority rules

## Configuration Examples

### YAML Configuration

```yaml
metadata:
  source_precedence:
    title: [api, embedded, path]
    author: [api, embedded, path]
    series: [path, api, embedded]

  sanitization:
    level: strict
    preserve_formatting: false

  validation:
    year_bounds: [1900, 2030]
    required_fields: [title, author]

  audnexus:
    timeout: 10.0
    retries: 3
    rate_limit: 5.0
```

### Python Configuration

```python
CONFIG = {
    'source_precedence': {
        'title': ['api', 'embedded', 'path'],
        'author': ['api', 'embedded', 'path'],
    },
    'sanitization': {
        'level': 'strict',
    },
    'validation': {
        'year_bounds': (1900, 2030),
    }
}
```

## Configuration Benefits

### Flexibility

* Runtime behavior modification
* Environment-specific settings
* User preference support
* A/B testing capability

### Maintainability

* Centralized configuration
* Clear documentation
* Version control friendly
* Easy deployment updates

### Extensibility

* Plugin configuration support
* Custom rule definitions
* Profile-based configurations
* Dynamic configuration loading
