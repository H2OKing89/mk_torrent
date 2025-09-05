"""
Tag normalization service - Core Modular Metadata System.

Part of the new modular metadata architecture providing genre/tag normalization
with case-insensitive deduplication and standardization.

Architecture Documentation:
- Services Overview: docs/core/metadata/07 — Services Details.md
"""

from __future__ import annotations

from typing import Any
import logging

# Check for rapidfuzz availability
try:
    from rapidfuzz import fuzz

    rapidfuzz_available = True
except ImportError:
    fuzz = None  # type: ignore
    rapidfuzz_available = False

logger = logging.getLogger(__name__)


class TagNormalizer:
    """
    Audiobook-focused tag normalization service.

    Handles case-insensitive deduplication, standardization, and cleanup
    of genre/tag metadata from multiple sources. Based on real-world data
    from 1,200+ audiobook collection.
    """

    def __init__(self, content_type: str = "audiobook"):
        """Initialize with content-type specific normalization rules."""
        self.content_type = content_type
        self._genre_map = self._build_audiobook_genre_map()
        self._consolidation_rules = self._build_consolidation_rules()

    def normalize(self, tags: list[str], filter_red_valid: bool = False) -> list[str]:
        """
        Normalize a list of tags/genres with deduplication and standardization.

        Args:
            tags: Raw list of tags/genres from metadata sources
            filter_red_valid: If True, filter to RED-acceptable genres only

        Returns:
            Cleaned, deduplicated, and standardized list of tags
        """
        if not tags:
            return []

        # Step 1: Basic cleanup
        cleaned: list[str] = []
        for tag in tags:
            if tag.strip():
                cleaned.append(tag.strip())

        # Step 2: Apply direct mappings
        mapped: list[str] = []
        for tag in cleaned:
            normalized = self._normalize_single_tag(tag)
            if normalized:
                mapped.append(normalized)

        # Step 3: Consolidate overlapping concepts
        consolidated = self._consolidate_overlapping_tags(mapped)

        # Step 4: Case-insensitive deduplication with stable order
        deduplicated = self._deduplicate_preserve_order(consolidated)

        # Step 5: RED filtering if requested
        if filter_red_valid:
            deduplicated = self._filter_red_genres(deduplicated)

        return deduplicated

    def _normalize_single_tag(self, tag: str) -> str | None:
        """Apply direct mappings for a single tag."""
        # Check exact match first (case-insensitive)
        tag_lower = tag.lower()
        if tag_lower in self._genre_map:
            return self._genre_map[tag_lower]

        # Check fuzzy matching for close variants if rapidfuzz available
        if rapidfuzz_available and fuzz is not None:
            for known_tag, canonical in self._genre_map.items():
                if fuzz.ratio(tag_lower, known_tag) >= 90:  # 90% similarity
                    return canonical

        # Return title-cased version if no mapping found
        return self._smart_title_case(tag)

    def _smart_title_case(self, text: str) -> str:
        """Apply smart title casing with special handling for known patterns."""
        # Handle special cases
        special_cases = {
            "lgbtq+": "LGBTQ+",
            "tv": "TV",
            "nsfk": "NSFK",
            "r&b": "R&B",
            "hip-hop": "Hip-Hop",
            "sci-fi": "Sci-Fi",
        }

        text_lower = text.lower()
        if text_lower in special_cases:
            return special_cases[text_lower]

        # Handle ampersands and prepositions
        words = text.split()
        result: list[str] = []
        for i, word in enumerate(words):
            word_lower = word.lower()
            if word_lower in [
                "&",
                "and",
                "of",
                "the",
                "in",
                "on",
                "at",
                "to",
                "for",
                "with",
            ]:
                if i == 0 or i == len(words) - 1:  # Always capitalize first/last word
                    result.append(word.capitalize())
                else:
                    result.append(word_lower)
            else:
                result.append(word.capitalize())

        return " ".join(result)

    def _consolidate_overlapping_tags(self, tags: list[str]) -> list[str]:
        """Consolidate overlapping/redundant concepts based on rules."""
        tag_set: set[str] = set(tags)
        to_remove: set[str] = set()

        for rule in self._consolidation_rules:
            primary = rule["primary"]
            alternates = rule["alternates"]

            # If primary exists, remove alternates
            if primary in tag_set:
                for alt in alternates:
                    if alt in tag_set:
                        to_remove.add(alt)

        # Remove overlapping tags
        result = [tag for tag in tags if tag not in to_remove]
        return result

    def _deduplicate_preserve_order(self, tags: list[str]) -> list[str]:
        """Remove duplicates while preserving original order (case-insensitive)."""
        seen: set[str] = set()
        result: list[str] = []

        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower not in seen:
                seen.add(tag_lower)
                result.append(tag)

        return result

    def _filter_red_genres(self, tags: list[str]) -> list[str]:
        """Filter to RED-acceptable genres only."""
        # RED's acceptable audiobook genres (simplified list)
        red_genres = {
            "adventure",
            "alternate history",
            "biography",
            "business",
            "classic literature",
            "comedy",
            "contemporary",
            "crime",
            "fantasy",
            "historical",
            "horror",
            "humor",
            "mystery",
            "non-fiction",
            "paranormal",
            "romance",
            "science fiction",
            "suspense",
            "thriller",
            "true crime",
            "western",
            "young adult",
        }

        filtered: list[str] = []
        for tag in tags:
            tag_lower = tag.lower()
            # Check if tag matches any RED genre (partial matching)
            if any(red_genre in tag_lower for red_genre in red_genres):
                filtered.append(tag)

        return filtered

    def _build_audiobook_genre_map(self) -> dict[str, str]:
        """Build genre mapping based on real AudiobookShelf data."""
        return {
            # Direct mappings from your AudiobookShelf data
            "action & adventure": "Action & Adventure",
            "adventure": "Adventure",
            "alternate history": "Alternate History",
            "amateur sleuths": "Amateur Sleuths",
            "animal fiction": "Animal Fiction",
            "animals": "Animals",
            "animals & nature": "Animals & Nature",
            "anthologies": "Anthologies",
            "anthologies & short stories": "Anthologies & Short Stories",
            "apocalyptic & post-apocalyptic": "Post-Apocalyptic",  # Consolidate
            "post-apocalyptic": "Post-Apocalyptic",
            "audio performances & dramatizations": "Dramatizations",  # Consolidate
            "dramatizations": "Dramatizations",
            "classics": "Classics",
            "clean & wholesome": "Clean & Wholesome",
            "coming of age": "Coming of Age",
            "contemporary": "Contemporary",
            "crime": "Crime",
            "crime fiction": "Crime Fiction",
            "crime thrillers": "Crime Thrillers",
            "cyberpunk": "Cyberpunk",
            "dark fantasy": "Dark Fantasy",
            "depression & mental health": "Mental Health",
            "difficult situations": "Difficult Situations",
            "dragons & mythical creatures": "Dragons & Mythical Creatures",
            "dystopian": "Dystopian",
            "emotions & feelings": "Emotions & Feelings",
            "epic": "Epic",
            "espionage": "Espionage",
            "fairy tales": "Fairy Tales",
            "family & relationships": "Family & Relationships",
            "family life": "Family Life",
            "fantasy": "Fantasy",
            "fantasy & magic": "Fantasy",  # Consolidate to main Fantasy
            "first contact": "First Contact",
            "folk tales & myths": "Folk Tales & Myths",
            "friendship": "Friendship",
            "gaslamp": "Gaslamp",
            "genetic engineering": "Genetic Engineering",
            "genre fiction": "Genre Fiction",
            "ghosts": "Ghosts",
            "greek & roman": "Greek & Roman",
            "growing up & facts of life": "Coming of Age",  # Consolidate
            "hard science fiction": "Hard Science Fiction",
            "hard-boiled": "Hard-Boiled",
            "historical": "Historical",
            "horror": "Horror",
            "humor": "Humor",
            "humorous": "Humor",  # Consolidate
            "international mystery & crime": "International Mystery & Crime",
            "lgbtq+": "LGBTQ+",
            "literary fiction": "Literary Fiction",
            "literature & fiction": "Literature & Fiction",
            "magical realism": "Magical Realism",
            "military": "Military",
            "movie": "Movie Tie-In",
            "multicultural": "Multicultural",
            "mysteries & detectives": "Mystery",  # Consolidate
            "mystery": "Mystery",
            "nsfk": "NSFK",
            "occult": "Occult",
            "paranormal": "Paranormal",
            "paranormal & urban": "Urban Fantasy",  # More specific
            "police procedurals": "Police Procedurals",
            "political": "Political",
            "private investigators": "Private Investigators",
            "psychological": "Psychological",
            "racism & discrimination": "Social Issues",
            "romance": "Romance",
            "romantic": "Romance",  # Consolidate
            "romantic comedy": "Romantic Comedy",
            "romantic suspense": "Romantic Suspense",
            "royalty": "Royalty",
            "satire": "Satire",
            "science fiction": "Science Fiction",
            "science fiction & fantasy": "Science Fiction & Fantasy",
            "small town & rural": "Small Town & Rural",
            "space exploration": "Space Exploration",
            "space opera": "Space Opera",
            "spies & politics": "Spies & Politics",
            "superhero": "Superhero",
            "supernatural": "Supernatural",
            "suspense": "Suspense",
            "sword & sorcery": "Sword & Sorcery",
            "technothrillers": "Technothrillers",
            "thriller & suspense": "Thriller & Suspense",
            "thrillers & suspense": "Thriller & Suspense",  # Consolidate pluralization
            "time travel": "Time Travel",
            "traditional detectives": "Traditional Detectives",
            "tv & video game tie-ins": "TV & Video Game Tie-Ins",  # Standardize capitalization
            "urban": "Urban Fantasy",
            "war & military": "War & Military",
            # Common music tags that might appear (legacy support)
            "rap": "Hip-Hop",
            "hiphop": "Hip-Hop",
            "hip hop": "Hip-Hop",
            "rnb": "R&B",
            "rhythm and blues": "R&B",
            "rock": "Rock",
            "pop": "Pop",
            "country": "Country",
            "jazz": "Jazz",
            "classical": "Classical",
            "electronic": "Electronic",
            "folk": "Folk",
            "blues": "Blues",
        }

    def _build_consolidation_rules(self) -> list[dict[str, Any]]:
        """Build rules for consolidating overlapping concepts."""
        return [
            {
                "primary": "Science Fiction",
                "alternates": ["Sci-Fi", "Scifi", "Sci Fi"],
            },
            {
                "primary": "Post-Apocalyptic",
                "alternates": ["Apocalyptic & Post-Apocalyptic"],
            },
            {"primary": "Fantasy", "alternates": ["Fantasy & Magic"]},
            {"primary": "Humor", "alternates": ["Humorous"]},
            {"primary": "Romance", "alternates": ["Romantic"]},
            {"primary": "Mystery", "alternates": ["Mysteries & Detectives"]},
            {
                "primary": "Dramatizations",
                "alternates": ["Audio Performances & Dramatizations"],
            },
            {"primary": "Coming of Age", "alternates": ["Growing Up & Facts of Life"]},
            {"primary": "Thriller & Suspense", "alternates": ["Thrillers & Suspense"]},
            {
                "primary": "TV & Video Game Tie-Ins",
                "alternates": ["TV & Video Game Tie-ins"],
            },
            {"primary": "Urban Fantasy", "alternates": ["Paranormal & Urban", "Urban"]},
        ]
