"""
Clean JSON upload specification for RED tracker.

This module provides a clean, tracker-agnostic JSON upload specification
that maps to RED's multipart form data structure. Based on ChatGPT feedback
for maintainable upload specifications.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AudioFormat(str, Enum):
    """Supported audio formats for RED."""

    FLAC = "FLAC"
    MP3 = "MP3"
    AAC = "AAC"
    AC3 = "AC-3"
    DTS = "DTS"


class AudioBitrate(str, Enum):
    """Supported audio bitrates for RED."""

    K192 = "192"
    K256 = "256"
    K320 = "320"
    V0_VBR = "V0 (VBR)"
    V1_VBR = "V1 (VBR)"
    V2_VBR = "V2 (VBR)"
    APS_VBR = "APS (VBR)"
    APX_VBR = "APX (VBR)"
    LOSSLESS = "Lossless"
    LOSSLESS_24BIT = "24bit Lossless"
    OTHER = "Other"


class MediaType(str, Enum):
    """Supported media types for RED."""

    CD = "CD"
    DVD = "DVD"
    VINYL = "Vinyl"
    SOUNDBOARD = "Soundboard"
    SACD = "SACD"
    DAT = "DAT"
    CASSETTE = "Cassette"
    WEB = "WEB"


class ReleaseType(str, Enum):
    """RED release types."""

    ALBUM = "Album"
    SOUNDTRACK = "Soundtrack"
    EP = "EP"
    ANTHOLOGY = "Anthology"
    COMPILATION = "Compilation"
    SINGLE = "Single"
    LIVE_ALBUM = "Live album"
    REMIX = "Remix"
    BOOTLEG = "Bootleg"
    INTERVIEW = "Interview"
    MIXTAPE = "Mixtape"
    DEMO = "Demo"
    CONCERT_RECORDING = "Concert Recording"
    DJ_MIX = "DJ Mix"
    UNKNOWN = "Unknown"


class ArtistType(str, Enum):
    """Artist type classifications."""

    MAIN = "main"
    GUEST = "guest"
    COMPOSER = "composer"
    CONDUCTOR = "conductor"
    PRODUCER = "producer"
    REMIXER = "remixer"
    FEATURING = "featuring"
    ARRANGER = "arranger"
    WITH = "with"


class Artist(BaseModel):
    """Artist information with type classification."""

    name: str = Field(..., description="Artist name")
    type: ArtistType = Field(default=ArtistType.MAIN, description="Artist role type")


class RemasterInfo(BaseModel):
    """Remaster edition information."""

    year: int | None = Field(None, description="Remaster year")
    title: str | None = Field(None, description="Remaster title/edition")
    record_label: str | None = Field(None, description="Remaster record label")
    catalogue_number: str | None = Field(None, description="Remaster catalogue number")


class Credits(BaseModel):
    """Production credits and metadata."""

    narrator: str | None = Field(None, description="Audiobook narrator")
    publisher: str | None = Field(None, description="Publisher name")
    series: str | None = Field(None, description="Book series name")
    part: str | None = Field(None, description="Series part/volume")
    isbn: str | None = Field(None, description="ISBN number")
    asin: str | None = Field(None, description="Amazon ASIN")
    language: str | None = Field(None, description="Content language")
    duration: str | None = Field(None, description="Duration description")


class REDUploadSpec(BaseModel):
    """
    Clean JSON upload specification for RED tracker.

    This provides a tracker-agnostic representation that can be converted
    to RED's specific form data requirements.
    """

    # Basic release information
    title: str = Field(..., description="Release title")
    artists: list[Artist] = Field(..., description="Artist information with roles")
    year: int = Field(..., description="Release year")

    # Format and technical details
    category: str = Field(..., description="Content category")
    format: AudioFormat = Field(..., description="Audio format")
    bitrate: AudioBitrate = Field(..., description="Audio bitrate")
    other_bitrate: str | None = Field(
        None, description="Custom bitrate string for 'Other' bitrates"
    )
    media: MediaType = Field(default=MediaType.WEB, description="Media source")

    # Release classification
    release_type: ReleaseType = Field(
        default=ReleaseType.ALBUM, description="Type of release"
    )

    # Content
    description: str = Field(..., description="Release description")
    tags: list[str] | None = Field(None, description="Genre/style tags")

    # Optional metadata
    remaster: RemasterInfo | None = Field(None, description="Remaster information")
    credits: Credits | None = Field(None, description="Production credits")

    # Flags
    scene: bool = Field(default=False, description="Scene release flag")
    vanity_house: bool = Field(default=False, description="Vanity House flag")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or contain only whitespace")
        return v

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        if not (1800 <= v <= 2030):
            raise ValueError(f"Year must be between 1800 and 2030, got {v}")
        return v


class REDFormAdapter:
    """
    Converts clean JSON upload spec to RED's multipart form data.

    This adapter handles the mapping between our clean JSON structure
    and RED's specific form field requirements.
    """

    # Category mapping (corrected based on RED API docs)
    CATEGORY_MAPPING = {
        "Music": "0",
        "Applications": "1",
        "E-Books": "2",
        "Audiobooks": "3",
        "E-Learning Videos": "4",
        "Comedy": "5",
        "Comics": "6",
    }

    # Format mapping
    FORMAT_MAPPING = {
        AudioFormat.FLAC: "FLAC",
        AudioFormat.MP3: "MP3",
        AudioFormat.AAC: "AAC",
        AudioFormat.AC3: "AC-3",
        AudioFormat.DTS: "DTS",
    }

    # Release type mapping
    RELEASE_TYPE_MAPPING = {
        ReleaseType.ALBUM: "1",
        ReleaseType.SOUNDTRACK: "3",
        ReleaseType.EP: "5",
        ReleaseType.ANTHOLOGY: "6",
        ReleaseType.COMPILATION: "7",
        ReleaseType.SINGLE: "9",
        ReleaseType.LIVE_ALBUM: "11",
        ReleaseType.REMIX: "13",
        ReleaseType.BOOTLEG: "14",
        ReleaseType.INTERVIEW: "15",
        ReleaseType.MIXTAPE: "16",
        ReleaseType.DEMO: "17",
        ReleaseType.CONCERT_RECORDING: "18",
        ReleaseType.DJ_MIX: "19",
        ReleaseType.UNKNOWN: "21",
    }

    def convert_to_form_data(self, spec: REDUploadSpec) -> dict[str, str]:
        """
        Convert upload spec to RED's multipart form data structure.

        Args:
            spec: Clean JSON upload specification

        Returns:
            Dictionary mapping form field names to values
        """
        form_data = {}

        # Basic release information
        form_data["title"] = spec.title
        form_data["year"] = str(spec.year)

        # Artists (combine all main artists)
        main_artists = [a.name for a in spec.artists if a.type == ArtistType.MAIN]
        form_data["artists[]"] = "; ".join(main_artists)

        # Handle other artist types
        for artist_type in ArtistType:
            if artist_type == ArtistType.MAIN:
                continue

            artists_of_type = [a.name for a in spec.artists if a.type == artist_type]
            if artists_of_type:
                form_data[f"{artist_type.value}[]"] = "; ".join(artists_of_type)

        # Category and format
        form_data["type"] = self.CATEGORY_MAPPING.get(
            spec.category, "3"
        )  # Default to Audiobooks
        form_data["format"] = self.FORMAT_MAPPING.get(spec.format, spec.format.value)

        # Bitrate handling - use string values as RED expects
        bitrate_value = spec.bitrate.value

        # RED API expects specific string values for bitrate
        if bitrate_value == "Other":
            form_data["bitrate"] = "Other"
            # Use the real bitrate string from upload spec if available
            if hasattr(spec, "other_bitrate") and spec.other_bitrate:
                form_data["other_bitrate"] = spec.other_bitrate
                # Determine VBR flag from the bitrate string
                form_data["vbr"] = "true" if "VBR" in spec.other_bitrate else "false"
            else:
                # Fallback to default for audiobooks
                form_data["other_bitrate"] = "64k VBR"
                form_data["vbr"] = "true"
        else:
            # Use the string value directly (e.g., "192", "V0 (VBR)", etc.)
            form_data["bitrate"] = bitrate_value

        # Release type
        form_data["releasetype"] = self.RELEASE_TYPE_MAPPING.get(
            spec.release_type, self.RELEASE_TYPE_MAPPING[ReleaseType.UNKNOWN]
        )

        # Tags
        if spec.tags:
            form_data["tags"] = ", ".join(spec.tags)

        # Description
        form_data["album_desc"] = spec.description

        # Remaster information
        if spec.remaster:
            if spec.remaster.year:
                form_data["remaster_year"] = str(spec.remaster.year)
            if spec.remaster.title:
                form_data["remaster_title"] = spec.remaster.title
            if spec.remaster.record_label:
                form_data["remaster_record_label"] = spec.remaster.record_label
            if spec.remaster.catalogue_number:
                form_data["remaster_catalogue_number"] = spec.remaster.catalogue_number

        # Flags
        form_data["scene"] = "1" if spec.scene else "0"
        form_data["vanity_house"] = "1" if spec.vanity_house else "0"

        return form_data

    def enhance_description_with_credits(self, spec: REDUploadSpec) -> str:
        """
        Enhance description with production credits in BBCode format.

        Args:
            spec: Upload specification with credits

        Returns:
            Enhanced description with credits section
        """
        if not spec.credits:
            return spec.description

        credits_lines = []

        if spec.credits.narrator:
            credits_lines.append(f"[b]Narrator:[/b] {spec.credits.narrator}")

        if spec.credits.publisher:
            credits_lines.append(f"[b]Publisher:[/b] {spec.credits.publisher}")

        if spec.credits.series:
            if spec.credits.part:
                credits_lines.append(
                    f"[b]Series:[/b] {spec.credits.series}, Volume {spec.credits.part}"
                )
            else:
                credits_lines.append(f"[b]Series:[/b] {spec.credits.series}")

        if spec.credits.isbn:
            credits_lines.append(f"[b]ISBN:[/b] {spec.credits.isbn}")

        if spec.credits.asin:
            credits_lines.append(f"[b]ASIN:[/b] {spec.credits.asin}")

        if spec.credits.language:
            credits_lines.append(f"[b]Language:[/b] {spec.credits.language}")

        if spec.credits.duration:
            credits_lines.append(f"[b]Duration:[/b] {spec.credits.duration}")

        if credits_lines:
            credits_section = (
                "\n\n[size=4][b]Production Information[/b][/size]\n"
                + "\n".join(credits_lines)
            )
            return spec.description + credits_section

        return spec.description

    def add_credits_to_description(self, spec: REDUploadSpec) -> str:
        """Alias for enhance_description_with_credits for backward compatibility."""
        return self.enhance_description_with_credits(spec)
