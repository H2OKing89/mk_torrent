# 2) High-level Architecture

## System Overview

```
+------------------------+        +----------------------+         +--------------------+
|        Workflows       |        |       Trackers       |         |   qbittorrent API  |
|  wizard.py / uploads   |        |  api/trackers/red.py |         |   api/qbittorrent  |
+-----------+------------+        +------------+---------+         +----------+---------+
            |                                  |                              |
            |                                  |                              |
            v                                  |                              |
   +--------+---------------------------+      |                              |
   |         Metadata Engine            |      |                              |
   |  core/metadata/engine.py          |      |                              |
   +--------+---------------------------+      |                              |
            |         ^                        |                              |
            |         |                        |                              |
            v         |                        v                              v
   +--------+---------+-----+      +----------+-----------+         +--------+--------+
   |   Processors (by type) |      |  Mappers (tracker)   |         |  Torrent Creator |
   |  processors/audiobook  |----->|  mappers/red.py      |-------->|  core/torrent_.. |
   +------------------------+      +----------------------+         +------------------+
            |
            v
   +-------------------+   +------------------+   +-------------------+
   | Sources/Extractors|   |  Services/Utils  |   |   Validators      |
   | embedded.py       |   | html_cleaner.py  |   | audiobook_validator|
   | audnexus.py       |   | format_detector.py|  | common.py          |
   +-------------------+   +------------------+   +-------------------+
```

## Component Responsibilities

* **Engine** orchestrates processors → sources → merge → services → validate → (optionally) map to tracker shape.
* **Processor** encapsulates content-type knowledge (path patterns, field expectations, defaults).
* **Sources** pull raw metadata (file tags via Mutagen, Audnexus API, folder names).
* **Services** provide generic utilities (sanitization, format sniffing, image URL detection, tag normalization).
* **Validators** return `valid/errors/warnings/completeness` for precise UX.
* **Mappers** translate from internal model to tracker-specific payloads (e.g., RED form fields), keeping trackers free of raw parsing.

## Data Flow

1. **Input**: Content path (audiobook, music, video)
2. **Detection**: Engine determines content type
3. **Processing**: Type-specific processor coordinates extraction
4. **Sources**: Multiple sources provide raw metadata
5. **Merging**: Declarative precedence rules combine sources
6. **Services**: Normalization and cleanup
7. **Validation**: Quality checks and completeness scoring
8. **Mapping**: (Optional) Transform to tracker format
9. **Output**: Clean, validated metadata ready for use
