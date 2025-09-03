# 13) Error Handling & Logging

## Exception Hierarchy

Use `exceptions.py` for typed failures:

```python
class MetadataError(Exception):
    """Base exception for metadata operations."""
    pass

class SourceUnavailable(MetadataError):
    """Raised when a metadata source is unavailable."""
    pass

class MetadataConflict(MetadataError):
    """Raised when metadata sources provide conflicting information."""
    pass

class ValidationError(MetadataError):
    """Raised when metadata validation fails."""
    pass
```

## Logging Strategy

### Structured Logging
JSON-friendly logging for production environments:

- Engine stages and progress
- Chosen source for each field
- Validation summary results
- Mapper output size and timing

### Log Levels

#### DEBUG
- Detailed processing steps
- Source selection rationale
- Field-level merge decisions
- Service call timings

#### INFO
- Pipeline stage completion
- Source availability status
- Validation results summary
- Performance metrics

#### WARNING
- Non-critical validation issues
- Source timeout recoveries
- Fallback mechanism usage
- Data quality concerns

#### ERROR
- Critical validation failures
- Source connection failures
- Processing exceptions
- Configuration errors

## Error Recovery

### Graceful Degradation
- Continue processing when individual sources fail
- Use fallback values when primary sources unavailable
- Provide partial results with quality indicators
- Maintain operation even with incomplete data

### Error Context
- Preserve error context for debugging
- Include source information in errors
- Provide actionable error messages
- Support error aggregation and reporting

## Implementation Examples

### Exception Usage
```python
try:
    metadata = audnexus_source.lookup(asin)
except SourceUnavailable as e:
    logger.warning(f"Audnexus unavailable: {e}")
    metadata = {}  # Continue with empty metadata
```

### Structured Logging
```python
logger.info(
    "Metadata extraction completed",
    extra={
        "stage": "extraction",
        "sources_used": ["embedded", "api"],
        "fields_extracted": 12,
        "validation_score": 0.85,
        "duration_ms": 150
    }
)
```

### Rich Logging Setup (Recommended)
```python
import logging
from rich.logging import RichHandler

# Configure Rich logging handler (from 00 — Packages)
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)],
)

logger = logging.getLogger("mk_torrent.metadata")

# Usage with Rich markup
logger.info("[bold green]Metadata extraction[/bold green] completed successfully")
logger.warning("[yellow]Missing[/yellow] optional field: [bold]narrator[/bold]")
logger.error("[bold red]Validation failed[/bold red]: Missing required field 'title'")
```

## Monitoring and Observability

### Metrics Collection
- Success/failure rates by source
- Processing time distributions
- Validation score distributions
- Error frequency by type

### Health Checks
- Source availability monitoring
- API response time tracking
- Service dependency status
- Configuration validation
