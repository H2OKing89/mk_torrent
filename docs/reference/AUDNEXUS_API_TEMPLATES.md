# Audnexus API Response Templates

## Successful Response (200)

Example ASIN: `B08G9PRS1K` (Project Hail Mary by Andy Weir)

```json
{
  "asin": "B08G9PRS1K",
  "authors": [
    {
      "asin": "B00G0WYW92",
      "name": "Andy Weir"
    }
  ],
  "copyright": 2021,
  "description": "Ryland Grace is the sole survivor on a desperate, last-chance mission - and if he fails, humanity and the Earth itself will perish. Except that right now, he doesn't know that. He can't even remember his own name, let alone the nature of his assignment or how to complete it....",
  "formatType": "unabridged",
  "genres": [
    {
      "asin": "18580606011",
      "name": "Science Fiction & Fantasy",
      "type": "genre"
    },
    {
      "asin": "18580628011",
      "name": "Science Fiction",
      "type": "tag"
    },
    {
      "asin": "18580629011",
      "name": "Adventure",
      "type": "tag"
    },
    {
      "asin": "18580639011",
      "name": "Hard Science Fiction",
      "type": "tag"
    },
    {
      "asin": "18580645011",
      "name": "Space Opera",
      "type": "tag"
    }
  ],
  "image": "https://m.media-amazon.com/images/I/91vS2L5YfEL.jpg",
  "isAdult": false,
  "isbn": "9781603935470",
  "language": "english",
  "literatureType": "fiction",
  "narrators": [
    {
      "name": "Ray Porter"
    }
  ],
  "publisherName": "Audible Studios",
  "rating": "4.9",
  "region": "us",
  "releaseDate": "2021-05-04T00:00:00.000Z",
  "runtimeLengthMin": 970,
  "summary": "<p><b><i>Winner of the 2022 Audie Awards' Audiobook of the Year</i></b></p> <p><b><i>Number-One Audible and </i></b><b>New York Times</b><b><i> Audio Best Seller</i></b></p> <p><b><i>More than one million audiobooks sold</i></b></p> <p><b>A lone astronaut must save the earth from disaster in this incredible new science-based thriller from the number-one </b><b><i>New York Times</i></b><b> best-selling author of </b><b><i>The Martian</i></b><b>.</b></p> <p>Ryland Grace is the sole survivor on a desperate, last-chance mission - and if he fails, humanity and the Earth itself will perish.</p> <p>Except that right now, he doesn't know that. He can't even remember his own name, let alone the nature of his assignment or how to complete it.</p> <p>All he knows is that he's been asleep for a very, very long time. And he's just been awakened to find himself millions of miles from home, with nothing but two corpses for company.</p> <p>His crewmates dead, his memories fuzzily returning, he realizes that an impossible task now confronts him. Alone on this tiny ship that's been cobbled together by every government and space agency on the planet and hurled into the depths of space, it's up to him to conquer an extinction-level threat to our species.</p> <p>And thanks to an unexpected ally, he just might have a chance.</p> <p>Part scientific mystery, part dazzling interstellar journey, <i>Project Hail Mary</i> is a tale of discovery, speculation, and survival to rival <i>The Martian</i> - while taking us to places it never dreamed of going.</p> <p>PLEASE NOTE: To accommodate this audio edition, some changes to the original text have been made with the approval of author Andy Weir.</p>",
  "title": "Project Hail Mary"
}
```

## Error Responses (400 & 404)

```json
{
  "statusCode": 400,
  "error": "Bad Request",
  "message": "Invalid ASIN format"
}
```

```json
{
  "statusCode": 404,
  "error": "Not Found",
  "message": "Book not found in database"
}
```

## Field Descriptions

### Core Fields
- **asin**: Amazon Standard Identification Number (10-12 characters)
- **title**: Book title
- **authors**: Array of author objects with ASIN and name
- **copyright**: Copyright year (integer)
- **description**: Short description/blurb
- **summary**: Full HTML-formatted summary with rich content

### Audio Format Fields
- **formatType**: "unabridged" or "abridged"
- **runtimeLengthMin**: Total runtime in minutes (integer)
- **narrators**: Array of narrator objects with name

### Classification Fields
- **genres**: Array of genre/tag objects with ASIN, name, and type
  - type: "genre" (main category) or "tag" (subcategory)
- **literatureType**: "fiction" or "non-fiction"
- **isAdult**: Boolean for adult content flag

### Publication Fields
- **publisherName**: Publisher/studio name
- **releaseDate**: ISO 8601 date string
- **isbn**: ISBN-13 format
- **rating**: Average rating as string (e.g., "4.9")
- **region**: Region code (e.g., "us")
- **language**: Language name (e.g., "english")

### Media Fields
- **image**: Direct URL to cover image (high resolution)

### Optional Fields
- **subtitle**: Book subtitle (when present)
- **seriesPrimary**: Series information object with name, position, ASIN

## Metadata Mapping for RED

### Direct Mappings
- `artists` ← `authors[].name`
- `album` ← `title` (+ subtitle if present)
- `year` ← extracted from `releaseDate` or `copyright`
- `format` ← derived from file analysis
- `encoding` ← derived from file analysis

### Enhanced Fields
- `genre` ← first genre where `type == "genre"`
- `tags` ← all genres where `type == "tag"`
- `description` ← HTML-cleaned `summary`
- `duration` ← calculated from `runtimeLengthMin`

### RED-Specific Enhancements
- Clean HTML from summary for upload descriptions
- Extract primary genre for RED genre field
- Format series information for enhanced descriptions
- Combine narrator information for audiobook-specific fields

## API Usage Notes

### Rate Limiting
- No specific rate limits documented
- Recommended: 1 request per second maximum
- Include proper User-Agent header

### Caching Strategy
- Cache successful responses for 24 hours
- Cache 404 responses for 1 hour
- Retry 5xx errors with exponential backoff

### Error Handling
- 200: Success - process normally
- 400: Bad request - invalid ASIN format
- 404: Not found - ASIN not in database
- 5xx: Server error - retry with backoff
