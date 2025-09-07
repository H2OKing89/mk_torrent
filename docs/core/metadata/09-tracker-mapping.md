# 9) Tracker Mapping (RED)

## Mapping Architecture

`mappers/red.py` converts `AudiobookMeta` → RED upload fields (no parsing here):

* Handles field renames, serialization (tags/genres → comma string), and HTML-free descriptions.
* Keeps RED-specific quirks isolated from core.

## Mapping Responsibilities

### Field Transformation

* Rename fields to match tracker expectations
* Convert data types (lists to comma-separated strings)
* Apply tracker-specific formatting rules
* Handle field combinations and derivations

### Data Sanitization

* Ensure HTML-free descriptions
* Apply character encoding requirements
* Remove or escape problematic characters
* Validate field length constraints

### RED-Specific Logic

* Map internal model to RED form fields
* Apply RED naming conventions
* Handle RED-specific requirements
* Validate against RED rules

## Mapping Benefits

### Separation of Concerns

* Keeps tracker APIs clean and focused
* Isolates tracker-specific logic
* Maintains clean internal data model
* Simplifies tracker API maintenance

### Extensibility

* Easy to add new trackers
* Reusable mapping patterns
* Configurable mapping rules
* Version-specific mapping support

### Testability

* Pure transformation functions
* Predictable input/output
* Easy mocking and validation
* Comprehensive test coverage

## Implementation Pattern

```python
class REDMapper:
    def map_audiobook(self, meta: AudiobookMeta) -> Dict[str, Any]:
        """Convert AudiobookMeta to RED upload fields."""
        return {
            'title': meta.title,
            'author': meta.author,
            'tags': ','.join(meta.genres + meta.tags),
            'description': self._strip_html(meta.description),
            'year': str(meta.year) if meta.year else '',
            # ... more mappings
        }
```

## Future Tracker Support

The mapping pattern easily extends to new trackers:

* `mappers/orpheus.py`
* `mappers/bibliotik.py`
* `mappers/myanonamouse.py`

Each mapper handles its tracker's specific requirements while consuming the same clean internal model.
