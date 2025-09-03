# 4) Canonical Data Model (Revised)

## 4.1 Scope & Principles

* **Scope:** Canonical representation of an audiobook compiled from:

  1. Embedded file metadata * `description_text`: HTMLSource data is transformed to the canonical model through service-specific mappings:

* **Path Info Source** (07.4): Extracts metadata from directory/file structures and naming conventions
* **Audnexus Source** (07.3): Transforms Audnexus API responses to canonical format with comprehensive field mapping and validation

Detailed mapping tables and transformation logic are specified in their respective service documents. All source adapters must append a `Provenance` entry with the unmodified payload to support troubleshooting and data lineage tracking.sanitization via HTML Cleaner service ([See 07.1 — HTML Cleaner Service](./07.1%20—%20HTML%20Cleaner%20Service.md))
* Audio format detection via Format Detector service ([See 07.2 — Format Detector Service](./07.2%20—%20Format%20Detector%20Service.md))
* `rating`: string → float, clamp 0..5
* `language`: map common names → ISO-639-1 (e.g., "english" → `en`)
* `genres`: dedupe case-insensitively; track source `type` ("genre" vs "tag")Info/Mutagen),
  2. Remote metadata (Audnexus).
* **Goals:** One stable DTO for downstream tasks (pathing, slugs, chapter exports, tracker templates, UI), explicit **provenance**, and clear **normalization**.

## 4.2 Entities (Dataclasses)

```python
# core/metadata/entities.py
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import date, datetime

# ---- Small value objects ----

@dataclass
class PersonRef:
    name: str
    asin: Optional[str] = None  # Audnexus author ASIN when present
    role: str = ""              # "author", "narrator"

@dataclass
class GenreTag:
    name: str
    type: str = "genre"         # "genre" | "tag" (Audnexus); others allowed
    asin: Optional[str] = None

@dataclass
class SeriesRef:
    name: str = ""
    position_str: str = ""      # e.g. "3"
    position_num: Optional[float] = None  # 3.0, 3.5 if needed
    asin: Optional[str] = None

@dataclass
class Chapter:
    index: int
    title: str
    start_ms: int               # milliseconds from 00:00:00.000
    kind: str = "chapter"       # "chapter" | "intermission" | "credits" | "extra"

@dataclass
class ImageAsset:
    url: str = ""               # remote art (Audnexus)
    embedded: bool = False
    width: Optional[int] = None
    height: Optional[int] = None
    format: str = ""            # "JPEG" etc.
    bytes: Optional[int] = None

@dataclass
class AudioStream:
    codec: str = ""             # "AAC", "FLAC", "MP3"
    profile: str = ""           # "LC" etc.
    bitrate_bps: Optional[int] = None
    bitrate_mode: str = ""      # "CBR" | "VBR"
    channels: Optional[int] = None
    layout: str = ""            # "L R"
    sample_rate_hz: Optional[int] = None
    duration_sec: Optional[float] = None
    compression: str = ""       # "Lossy" | "Lossless"

@dataclass
class FileRef:
    path: Path
    size_bytes: Optional[int] = None
    container: str = ""         # "MPEG-4"
    extension: str = ""         # "m4b"

@dataclass
class Provenance:
    source: str                 # "mediainfo" | "audnexus"
    fetched_at: Optional[datetime] = None
    version: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

# ---- Canonical audiobook DTO ----

@dataclass
class AudiobookMeta:
    # Identity & naming
    title: str = ""                 # canonical title
    subtitle: str = ""              # when present
    series: SeriesRef = field(default_factory=SeriesRef)
    volume: str = ""                # zero-padded (e.g., "03") when applicable

    # People
    author_primary: str = ""        # convenience
    narrator_primary: str = ""      # convenience
    authors: List[PersonRef] = field(default_factory=list)
    narrators: List[PersonRef] = field(default_factory=list)

    # Publishing & classification
    asin: str = ""
    isbn: str = ""
    publisher: str = ""
    language: str = "en"            # ISO-639-1 where possible
    region: str = ""                # "us" etc.
    literature_type: str = ""       # "fiction"|"nonfiction"|...
    format_type: str = ""           # "unabridged"|"abridged"
    is_adult: Optional[bool] = None
    rating: Optional[float] = None  # 4.8 => 4.8

    # Time & runtime
    release_date: Optional[date] = None
    year: Optional[int] = None
    runtime_min: Optional[int] = None     # remote (Audnexus)
    duration_sec: Optional[int] = None    # embedded (file trumps remote)

    # Description & topics
    description_html: str = ""      # raw
    description_text: str = ""      # sanitized/plain
    genres: List[GenreTag] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Media & structure
    cover: ImageAsset = field(default_factory=ImageAsset)
    images: List[ImageAsset] = field(default_factory=list)
    chapters: List[Chapter] = field(default_factory=list)
    audio: AudioStream = field(default_factory=AudioStream)

    # Files & paths
    files: List[FileRef] = field(default_factory=list)
    source_path: Optional[Path] = None     # the “main” file’s path

    # Derived for pipeline consumers (slugging, compliance, UI)
    display_title: str = ""           # e.g., "How a Realist Hero… — vol_03"
    safe_slug: str = ""               # ASCII safe; tracker/FS compliant
    artwork_url: str = ""             # kept for convenience

    # Provenance (keep originals for troubleshooting)
    provenance: List[Provenance] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

### Optional strict mirror (Pydantic)

Put this under `schemas/audiobook.py`. Keep fields 1:1 with the dataclass, mostly `Optional[...]` with basic validators (e.g., clamp rating 0–5, coerce language to lower, parse release\_date).

> Rule of thumb: **use the dataclass everywhere**, import the pydantic model only for boundary checks (API ingress/egress, CLI `--validate`).

---

## 4.3 Normalization Rules

**Conflicts & precedence**

* Merge rules are handled by the Field Merger service ([See 07.5 — Audiobook Metadata Field Merger](./07.5%20—%20Audiobook%20Metadata%20Field%20Merger.md))
* Precedence follows: embedded (precise) > API (authoritative) > path (reliable extraction) per field type
* Smart list unions for genres, tags, and other collections with de-duplication

**Coercions**

* `rating`: string → float, clamp 0..5.
* `language`: map common names → ISO-639-1 (e.g., “english” → `en`).
* `bitrate`: strings to `int` bps; `OverallBitRate_Mode`/`BitRate_Mode` → `"CBR"|"VBR"`.
* `genres`: dedupe case-insensitively; track source `type` (“genre” vs “tag”).
* `description_text`: HTML stripped & unescaped from either source.
* `chapters`: parse MediaInfo Menu keys `_HH_MM_SS_mmm` → milliseconds; infer `kind` by title prefixes (“Intermission”, “End Credits”, etc.).

**Derived Fields**

* `display_title`: configurable template (e.g., `"{title} - vol_{volume} ({year}) ({author_primary})")
* `safe_slug`: ASCII, filesystem-safe, and tracker-safe (length caps configurable per tracker)
* `volume`: zero-pad to 2+ digits (configurable)

---

## 4.4 Source → Canonical Mapping

### MediaInfo (selected keys)

| MediaInfo path                            | Canonical field                                  | Notes                                    |
| ----------------------------------------- | ------------------------------------------------ | ---------------------------------------- |
| General.Title                             | `title` (fallback)                               | Prefer Audnexus first.                   |
| General.Album                             | `subtitle` or alt title                          | Often “Title: Subtitle”.                 |
| General.Album\_Performer, Performer       | `authors[0].name`, `author_primary`              | If Audnexus missing.                     |
| General.Composer                          | `narrators[]` candidate                          | Your sample uses narrator here.          |
| General.Genre                             | `genres[]` (split `;`)                           | Type=`genre` unless mapped.              |
| General.Description / Comment             | `description_html` (then sanitize to `..._text`) | HTML present.                            |
| General.Recorded\_Date                    | `year`                                           | Int coercion.                            |
| General.FileSize                          | `files[].size_bytes`                             | With `FileRef`.                          |
| General.OverallBitRate(\_Mode)            | `audio.bitrate_bps`, `audio.bitrate_mode`        | Prefer audio stream values when present. |
| Audio.Format / Format\_AdditionalFeatures | `audio.codec`, `audio.profile`                   | AAC / LC, etc.                           |
| Audio.BitRate / BitRate\_Mode             | `audio.bitrate_bps`, `audio.bitrate_mode`        | —                                        |
| Audio.Channels / ChannelLayout            | `audio.channels`, `audio.layout`                 | —                                        |
| Audio.SamplingRate                        | `audio.sample_rate_hz`                           | —                                        |
| Audio.Duration                            | `audio.duration_sec`, `duration_sec`             | Canonical duration.                      |
| Image.Type=Cover + Width/Height/Format    | `cover` + `images[]`, `cover.embedded=True`      | —                                        |
| Menu(extra.\_HH\_MM\_SS\_mmm)             | `chapters[]`                                     | Key→ms, value→title.                     |

### Audnexus (selected keys)

| Audnexus key                       | Canonical field                        |
| ---------------------------------- | -------------------------------------- |
| asin                               | `asin`                                 |
| title                              | `title`                                |
| subtitle                           | `subtitle`                             |
| description/summary                | `description_html` → sanitize          |
| publisherName                      | `publisher`                            |
| language                           | `language` (→ ISO-639-1)               |
| rating                             | `rating` (float)                       |
| region                             | `region`                               |
| releaseDate                        | `release_date` (date), `year` fallback |
| runtimeLengthMin                   | `runtime_min`                          |
| formatType                         | `format_type`                          |
| literatureType                     | `literature_type`                      |
| isAdult                            | `is_adult`                             |
| image                              | `cover.url` (primary remote art)       |
| authors\[].{asin,name}             | `authors[]` (role="author")            |
| narrators\[].name                  | `narrators[]` (role="narrator")        |
| genres\[].{name,type,asin}         | `genres[]`                             |
| seriesPrimary.{asin,name,position} | `series`, `volume` (padded)            |

All adapters should append a `Provenance` entry with the unmodified payload.

---

## 4.5 Example (abridged) — from your sample

```json
{
  "title": "How a Realist Hero Rebuilt the Kingdom: Volume 3",
  "subtitle": "How a Realist Hero Rebuilt the Kingdom, Book 3",
  "series": {"name": "How a Realist Hero Rebuilt the Kingdom", "position_str": "3", "position_num": 3.0, "asin": "B0C37XK8SV"},
  "volume": "03",

  "authors": [{"name": "Dojyomaru", "asin": "B06W5GKCZW", "role": "author"}],
  "author_primary": "Dojyomaru",
  "narrators": [{"name": "BJ Harrison", "role": "narrator"}],
  "narrator_primary": "BJ Harrison",

  "asin": "B0C8ZW5N6Y",
  "isbn": "9798765080221",
  "publisher": "Tantor Audio",
  "language": "en",
  "region": "us",
  "literature_type": "fiction",
  "format_type": "unabridged",
  "is_adult": false,
  "rating": 4.8,

  "release_date": "2023-07-11",
  "year": 2023,
  "runtime_min": 524,
  "duration_sec": 31509,

  "description_html": "<p>The Battle Continues!...",
  "description_text": "The Battle Continues! Souma presses Elfrieden's siege ...",
  "genres": [
    {"name": "Science Fiction & Fantasy", "type": "genre", "asin": "18580606011"},
    {"name": "Fantasy", "type": "tag", "asin": "18580607011"},
    {"name": "Epic", "type": "tag", "asin": "18580615011"},
    {"name": "Historical", "type": "tag", "asin": "18580618011"}
  ],

  "cover": {"url": "https://m.media-amazon.com/images/I/81IpsoA4EqL.jpg", "embedded": true, "width": 2400, "height": 2400, "format": "JPEG"},
  "audio": {"codec": "AAC", "profile": "LC", "bitrate_bps": 125588, "bitrate_mode": "CBR", "channels": 2, "layout": "L R", "sample_rate_hz": 44100, "duration_sec": 31509, "compression": "Lossy"},

  "chapters": [
    {"index": 1, "title": "Opening Credits", "start_ms": 0, "kind": "credits"},
    {"index": 2, "title": "Prologue: On a Moonlit Terrace", "start_ms": 23243, "kind": "chapter"},
    {"index": 3, "title": "Chapter 1: Project Lorelei", "start_ms": 424901, "kind": "chapter"}
    // ... (rest omitted)
  ],

  "files": [{
    "path": "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.m4b",
    "size_bytes": 500534610,
    "container": "MPEG-4",
    "extension": "m4b"
  }],

  "source_path": "…/…/…/…/Volume 3}.m4b",
  "artwork_url": "https://m.media-amazon.com/images/I/81IpsoA4EqL.jpg",
  "display_title": "How a Realist Hero Rebuilt the Kingdom — vol_03 (2023) (Dojyomaru)",
  "safe_slug": "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}",

  "provenance": [
    {"source": "mediainfo", "version": "25.07"},
    {"source": "audnexus", "version": "1.8.0"}
  ]
}
```

*(Times converted to ms; volume zero-padded; language normalized.)*

---

## 4.6 Adapter Responsibilities

Adapters are lightweight wrappers that invoke the appropriate services and handle provenance tracking:

* **MediaInfo Adapter**: Uses Format Detector Service (07.2) to transform MediaInfo JSON output
* **Audnexus Adapter**: Uses Audnexus Source Service (07.3) for API response transformation
* **Path Info Adapter**: Uses Path Info Source Service (07.4) for directory/filename metadata extraction

All adapters use the Field Merger Service (07.5) for conflict resolution and must preserve raw payloads in `provenance` entries. Detailed adapter implementation patterns and service integration are specified in their respective 07.x service documents.

---

## 4.7 “Source Notes & Utilization” (each gets its own doc)

Create short, focused docs in `docs/sources/`:

* `audnexus.md` — fields we consume, rate-limit behavior, when we trust it over embedded, HTML quirks, language mapping table, series position logic, image usage (prefer remote if embedded is missing or tiny).
* `mediainfo.md` — JSON schema cheatsheet, reliable vs flaky fields, how we derive chapters and audio properties, pitfalls (e.g., Composer used for narrator in some libraries).
* `normalization.md` — the exact transforms (HTML → text, volume padding, language mapping, rating clamp), plus tracker-compliance considerations for `safe_slug`.
* `conflicts.md` — examples of conflict resolution with before/after snapshots.

Each doc ends with **“How We Use It”**: renamer templates, BBCode generation, torrent metadata, folder art, UI badges (lossy/lossless, runtime, rating, tags).

---

## 4.8 Pydantic Mirror (strict mode)

* Mirrors `AudiobookMeta` 1:1.
* Validators:

  * `rating` in 0..5
  * `language` normalized to lower
  * `release_date` parsed to `date`
  * `volume` zero-padded if numeric
  * `duration_sec` >= 0, `runtime_min` >= 0
* Config flag: `STRICT_METADATA=1` to enable in pipelines / CI.

---

## 4.9 Package Dependencies & Compliance

This canonical data model is designed to work with the packages specified in **00 — Recommended Packages**:

* **Pydantic v2**: Core model validation and serialization
* **python-dateutil**: Date parsing and normalization in source adapters
* **Pillow (PIL)**: Image processing for cover art validation and metadata
* **Additional packages**: As referenced in the 07.x service specifications

All model implementations should follow the package selection guidelines to ensure consistency across the metadata processing pipeline.

---

## 4.10 Backward-Compatibility & Incremental Adoption

* Keep your current fields; the new ones are additive.
* Downstream consumers can keep using `title/author/asin/volume/year/duration_sec` with **no change**.
* Start writing the raw payloads into `provenance[]` immediately—future-you will thank present-you during weird edge cases. 😉

---

## 4.11 Quick sanity on your sample

* **CBR or VBR?** Embedded `OverallBitRate_Mode=CBR` and `Audio.BitRate_Mode=CBR` → treat as **CBR**.
* **Chapters present?** Yes—use the `Menu` entries; you’ll get 15 named items including “Intermission” and credits.
* **Narrator**: appears under **Composer** in embedded; Audnexus fixes it. Our precedence handles that cleanly.
