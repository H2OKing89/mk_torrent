# 6) Engine Pipeline (Audiobook Example)

## Processing Steps

1. **Detect type** if omitted: look at suffix or dir contents.
2. **Collect candidates** (parallel or serial):

   * `embedded` (Mutagen): title/author/album/narrator/duration/chapters/cover.
   * `api` (Audnexus): authoritative fields (asin, subtitle, publisher, release date, summary, genres, narrator list), given an ASIN from path or tags.
   * `path` (PathInfo): title/series/vol/year/author/uploader/asin from your naming standard.

3. **Merge** using declarative precedence:

   ```yaml
   precedence:
     title: [api, embedded, path]
     author: [api, embedded, path]
     series: [path, api, embedded]
     volume: [path, api]
     year: [api, embedded, path]
     description: [api, embedded]
     genres: [api, embedded]
     narrator: [api, embedded]
     asin: [path, api, embedded]
   ```

4. **Normalize** (HTML cleaner, tag normalizer, volume zero-pad, album fallback).

5. **Validate** (tracker-agnostic checks + RED hints):

   * `required`: title, author
   * `recommended`: year, narrator, duration, asin
   * results: `{ valid: bool, errors: [], warnings: [], completeness: 0.0..1.0 }`

6. **(Optional) Map** to tracker payload via `mappers/red.py` (so `api/trackers/red.py` just consumes a clean dict ready for upload).

## Pipeline Characteristics

### Deterministic

* Same input always produces same output
* Reproducible results
* Debuggable behavior

### Configurable

* Precedence rules can be adjusted
* Sources can be enabled/disabled
* Validation rules can be customized

### Extensible

* New sources integrate seamlessly
* Additional processing steps can be added
* Custom mappers for new trackers

### Error-Tolerant

* Continues processing even if some sources fail
* Graceful degradation
* Comprehensive error reporting

## Source Integration

### Parallel vs Serial

* Sources can be processed in parallel for speed
* Or serially for simpler debugging
* Configurable execution model

### Source Discovery

* ASIN extraction drives API lookups
* Path parsing provides fallback values
* Embedded tags offer high-precision data

### Data Flow Control

* Each source provides structured data
* Merger handles conflicts intelligently
* Services clean and normalize results
