# Audnexus API — Unofficial Markdown Guide (v1.8.0)

> Aggregate audiobook data the easy way. This guide focuses on **read-only** endpoints you’ll actually use in scripts and apps.

---

## Overview

* **Base URL:** `https://api.audnex.us`
* **Version:** `1.8.0`
* **Docs/Repo:** [https://github.com/laxamentumtech/audnexus](https://github.com/laxamentumtech/audnexus) (project)
  Alt docs link in spec: [https://github.com/djdembeck/audnexus](https://github.com/djdembeck/audnexus)
* **Auth:** Public, no token needed (as of the spec provided)
* **Formats:** JSON by default. Some endpoints advertise XML, but JSON is the happy path.
* **Regions (`region` query param):** `au | ca | de | es | fr | in | it | jp | us | uk` (default: `us`)
* **Common extras:**

  * `update` (0/1): Ask server to refresh upstream data before returning.
  * Some endpoints accept `update` as a **number** (`0|1`); one accepts **string** (`"0"|"1"`). Yeah… it’s a vibe. See “⚠️ Type quirk” below.

### Status Codes & Error Shape

* **200**: Success
* **400**: Bad request (e.g., malformed ASIN).
* **404**: Not found

Errors return:

```json
{
  "statusCode": 400,
  "error": "Bad Request",
  "message": "Bad ASIN"
}
```

updated: 2025-09-06T19:00:01-05:00
---

## Endpoints

### 1) Get a Book by ASIN

**GET** `/books/{ASIN}`

Returns a single **Book**.

**Path params**

* `ASIN` *(string, required)*: Audible’s ID.

**Query params**

* `seedAuthors` *(0|1, optional)*: Whether to seed the book’s authors server-side.
* `update` *(0|1, optional)*: Force an upstream refresh before responding.
* `region` *(enum, optional, default `us`)*

**cURL**

```bash
curl -s "https://api.audnex.us/books/B08G9PRS1K?update=1&region=us"
```

**Python (httpx)**

```python
import httpx

BASE = "https://api.audnex.us"
asin = "B08G9PRS1K"
params = {"update": 1, "region": "us"}  # update can be 0/1 (number) here
r = httpx.get(f"{BASE}/books/{asin}", params=params, timeout=30)
r.raise_for_status()
book = r.json()
print(book["title"], "→", book["runtimeLengthMin"], "min")
```

**Selected response fields (Book)**

* `asin` *(string)*
* `title` *(string)*, `subtitle` *(string, optional)*
* `authors` *(\[Person])*
* `narrators` *(\[Person])*
* `publisherName` *(string)*
* `copyright` *(integer)*
* `formatType` *(string, e.g., "unabridged")*
* `language` *(string)*
* `literatureType` *("fiction"|"nonfiction")*
* `genres` *(\[Genre])*
* `image` *(uri)*
* `rating` *(string)*  ← yes, it’s a string
* `releaseDate` *(ISO 8601 date-time)*
* `runtimeLengthMin` *(number)*
* `seriesPrimary`, `seriesSecondary` *(Series)*
* `summary`, `description` *(string; often HTML)*

**Real-world example**

```json
{
  "asin": "B0CJWTXLPJ",
  "authors": [{"asin": "B076N4Q46Q", "name": "Rifujin na Magonote"}],
  "copyright": 2014,
  "description": "Kicked out by his family and wandering the streets...",
  "formatType": "unabridged",
  "genres": [
    {"asin": "18580715011", "name": "Teen & Young Adult", "type": "genre"},
    {"asin": "18580894011", "name": "Literature & Fiction", "type": "tag"},
    {"asin": "18581048011", "name": "Science Fiction & Fantasy", "type": "tag"},
    {"asin": "18581049011", "name": "Fantasy", "type": "tag"},
    {"asin": "18581061011", "name": "Sword & Sorcery", "type": "tag"}
  ],
  "image": "https://m.media-amazon.com/images/I/91ae0OAgZtL.jpg",
  "isAdult": false,
  "isbn": "",
  "language": "english",
  "literatureType": "fiction",
  "narrators": [{"name": "Cliff Kirk"}],
  "publisherName": "Seven Seas Entertainment, Seven Seas Siren",
  "rating": "4.8",
  "region": "us",
  "releaseDate": "2023-09-26T00:00:00.000Z",
  "runtimeLengthMin": 437,
  "seriesPrimary": {
    "asin": "B0CJYVSQFB",
    "name": "Mushoku Tensei: Jobless Reincarnation",
    "position": "1"
  },
  "subtitle": "Jobless Reincarnation (Light Novel), Vol. 1",
  "summary": "\u003Cp\u003E\u003Cb\u003EDeath is only the beginning! ...",
  "title": "Mushoku Tensei"
}
```

---

### 2) Get Chapters for a Book

**GET** `/books/{ASIN}/chapters`

Returns chapter timing metadata for a single book.

**Path params**

* `ASIN` *(string, required)*

**Query params**

* `update` *(0|1, optional)*: Refresh upstream before responding.
* `region` *(enum, optional, default `us`)*

**cURL**

```bash
curl -s "https://api.audnex.us/books/B08G9PRS1K/chapters?region=us&update=1"
```

**Python (httpx)**

```python
import httpx

BASE = "https://api.audnex.us"
asin = "B08G9PRS1K"
params = {"region": "us", "update": 1}
r = httpx.get(f"{BASE}/books/{asin}/chapters", params=params, timeout=30)
r.raise_for_status()
chap = r.json()
print(chap["asin"], "has", len(chap["chapters"]), "chapters")
```

**Selected response fields (Chapter)**

* `asin` *(string)*
* `brandIntroDurationMs` *(number)*
* `brandOutroDurationMs` *(number)*
* `runtimeLengthMs` *(number)*, `runtimeLengthSec` *(number)*
* `isAccurate` *(boolean)*
* `chapters`: array of

  * `title` *(string)*
  * `startOffsetMs` *(number)*, `startOffsetSec` *(number)*
  * `lengthMs` *(number)*

**Real-world example:**

```json
{
  "asin": "B0C8ZW5N6Y",
  "brandIntroDurationMs": 3924,
  "brandOutroDurationMs": 4945,
  "chapters": [
    {
      "lengthMs": 23243,
      "startOffsetMs": 0,
      "startOffsetSec": 0,
      "title": "Opening Credits"
    },
    {
      "lengthMs": 401658,
      "startOffsetMs": 23243,
      "startOffsetSec": 23,
      "title": "Prologue: On a Moonlit Terrace"
    },
    {
      "lengthMs": 5221680,
      "startOffsetMs": 424901,
      "startOffsetSec": 424,
      "title": "Chapter 1: Project Lorelei"
    },
    {
      "lengthMs": 1096678,
      "startOffsetMs": 5646581,
      "startOffsetSec": 5646,
      "title": "Intermission 1: Lord Ishizuka"
    },
    {
      "lengthMs": 4075264,
      "startOffsetMs": 6743259,
      "startOffsetSec": 6743,
      "title": "Chapter 2: Meeting on a Street Corner in Van"
    },
    {
      "lengthMs": 4060867,
      "startOffsetMs": 10818523,
      "startOffsetSec": 10818,
      "title": "Chapter 3: Negotiations"
    },
    {
      "lengthMs": 4174227,
      "startOffsetMs": 14879390,
      "startOffsetSec": 14879,
      "title": "Chapter 4: Pact"
    },
    {
      "lengthMs": 1973022,
      "startOffsetMs": 19053617,
      "startOffsetSec": 19053,
      "title": "Chapter 5: Withdrawal"
    },
    {
      "lengthMs": 1125169,
      "startOffsetMs": 21026639,
      "startOffsetSec": 21026,
      "title": "Extra Story: The Story of a Certain Group of Adventurers 3"
    },
    {
      "lengthMs": 1379938,
      "startOffsetMs": 22151808,
      "startOffsetSec": 22151,
      "title": "Chapter 6: Standing in Front of the Lion's Cage"
    },
    {
      "lengthMs": 2095066,
      "startOffsetMs": 23531746,
      "startOffsetSec": 23531,
      "title": "Chapter 7: Promise"
    },
    {
      "lengthMs": 726413,
      "startOffsetMs": 25626812,
      "startOffsetSec": 25626,
      "title": "Intermission 2: What the Black-Robed Prime Minister Was Doing Then"
    },
    {
      "lengthMs": 4064373,
      "startOffsetMs": 26353225,
      "startOffsetSec": 26353,
      "title": "Chapter 8: Crime and Punishment"
    },
    {
      "lengthMs": 1029294,
      "startOffsetMs": 30417598,
      "startOffsetSec": 30417,
      "title": "Epilogue: Peace Is Yet Distant"
    },
    {
      "lengthMs": 62437,
      "startOffsetMs": 31446892,
      "startOffsetSec": 31446,
      "title": "End Credits"
    }
  ],
  "isAccurate": true,
  "region": "us",
  "runtimeLengthMs": 31509329,
  "runtimeLengthSec": 31509
}
```

---

### 3) Search Authors by Name

**GET** `/authors?name=...`

Finds authors by display name.

**Query params**

* `name` *(string, required)*: The search term.
* `region` *(enum, optional, default `us`)*

**cURL**

```bash
curl -sG "https://api.audnex.us/authors" --data-urlencode "name=Andy Weir"
```

**Python (httpx)**

```python
import httpx

r = httpx.get(
    "https://api.audnex.us/authors",
    params={"name": "Andy Weir", "region": "us"},
    timeout=30
)
r.raise_for_status()
authors = r.json()   # list of Author
print([a["name"] for a in authors][:5])
```

**Response**: `Author[]`

Each **Author** object:

* `asin` *(string)*
* `name` *(string)*
* `description` *(string)*
* `image` *(string)*
* `genres` *(\[Genre])*
* `region` *(enum)*
  *(Search results may be minimal; see “Get Author by ASIN” for richer detail.)*

---

### 4) Get an Author by ASIN

**GET** `/authors/{ASIN}`

Returns a single **Author** with richer metadata and “similar” authors.

**Path params**

* `ASIN` *(string, required)*

**Query params**

* `update` *("0"|"1", optional)*: **String** form here, not number.
* `region` *(enum, optional, default `us`)*

**cURL**

```bash
curl -s "https://api.audnex.us/authors/B00G0WYW92?update=1&region=us"
```

**Python (httpx)**

```python
import httpx

params = {"update": "1", "region": "us"}  # string "1" here to match spec
r = httpx.get("https://api.audnex.us/authors/B00G0WYW92", params=params, timeout=30)
r.raise_for_status()
author = r.json()
print(author["name"], "→ similar:", [p["name"] for p in author.get("similar", [])])
```

**Selected response fields (Author)**

* `asin`, `name`, `description`, `image`
* `genres` *(\[Genre])*
* `region` *(enum)*
* `similar` *(\[Person])*

---

## Schemas (Condensed)

**Person**

```ts
{
  asin?: string;
  name: string;
}
```

**Genre**

```ts
{
  asin: string;
  name: string;
  type: string; // e.g., "genre" or "tag"
}
```

**Series**

```ts
{
  asin?: string;
  name: string;
  position?: string; // textual position marker like "1"
}
```

**Book**

```ts
{
  asin: string;
  title: string;
  subtitle?: string;
  authors: Person[];
  narrators?: Person[];
  description: string;
  summary: string;            // Often HTML
  image?: string;             // URL
  publisherName: string;
  copyright?: number;
  formatType: string;         // e.g., "unabridged"
  language: string;
  literatureType?: "fiction" | "nonfiction";
  genres?: Genre[];
  rating: string;             // Note: string
  region: "au"|"ca"|"de"|"es"|"fr"|"in"|"it"|"jp"|"us"|"uk";
  releaseDate: string;        // ISO 8601
  runtimeLengthMin: number;
  seriesPrimary?: Series;
  seriesSecondary?: Series;
  isbn?: string;
  isAdult?: boolean;
}
```

**Chapter**

```ts
{
  asin: string;
  brandIntroDurationMs: number;
  brandOutroDurationMs: number;
  isAccurate: boolean;
  region: "au"|"ca"|"de"|"es"|"fr"|"in"|"it"|"jp"|"us"|"uk";
  runtimeLengthMs: number;
  runtimeLengthSec: number;
  chapters: {
    title: string;
    startOffsetMs: number;
    startOffsetSec: number;
    lengthMs: number;
  }[];
}
```

**Author**

```ts
{
  asin: string;
  name: string;
  description: string;
  image?: string;
  genres?: Genre[];
  region: "au"|"ca"|"de"|"es"|"fr"|"in"|"it"|"jp"|"us"|"uk";
  similar?: Person[];
}
```

---

## Tips, Footguns & Nice-to-haves

* **⚠️ Type quirk for `update`:**

  * `/books/{ASIN}` and `/books/{ASIN}/chapters` expect `update` as **number** `0|1`.
  * `/authors/{ASIN}` expects `update` as **string** `"0"|"1"`.
    When in doubt, match the endpoint’s spec exactly to avoid 400s.

* **HTML in `summary`/`description`:** You’ll often get HTML. Sanitize or strip tags if you need plaintext (e.g., in CLI/BBCode).

* **Durations:** Chapters provide both `startOffsetMs` and `startOffsetSec`. If you’re building cue sheets, you’ll love those offsets.

* **Series:** `seriesPrimary` and `seriesSecondary` help you file multi-series crossovers. The `position` is a string—don’t assume it’s numeric.

---

## Minimal End-to-End Example (Python)

```python
import httpx

BASE = "https://api.audnex.us"

def get_book(asin, region="us", update=0):
    return httpx.get(f"{BASE}/books/{asin}", params={"region": region, "update": int(bool(update))}).json()

def get_chapters(asin, region="us", update=0):
    return httpx.get(f"{BASE}/books/{asin}/chapters", params={"region": region, "update": int(bool(update))}).json()

def search_authors(name, region="us"):
    return httpx.get(f"{BASE}/authors", params={"name": name, "region": region}).json()

def get_author(asin, region="us", update=False):
    # string "0"/"1" for this endpoint
    return httpx.get(f"{BASE}/authors/{asin}", params={"region": region, "update": "1" if update else "0"}).json()

if __name__ == "__main__":
    book = get_book("B08G9PRS1K", update=1)
    chapters = get_chapters("B08G9PRS1K")
    author = get_author("B00G0WYW92", update=True)
    print(book["title"], "• chapters:", len(chapters["chapters"]), "• author:", author["name"])
```

---

If you want this turned into a pretty, printable PDF or a README for your repos, say the word and I’ll package it up with a table of contents and some spicy examples (httpx + asyncio batch pulls, rate-friendly retries, the works).
