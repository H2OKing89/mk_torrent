"""
Pydantic models for Audnexus API v1.8.0 responses.

These models provide type safety and validation for API responses
following the official Audnexus API specification.
"""

from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


# Supported regions as per API spec
Region = Literal["au", "ca", "de", "es", "fr", "in", "it", "jp", "us", "uk"]


class Person(BaseModel):
    """Person model (Author/Narrator)."""
    asin: Optional[str] = None
    name: str


class Genre(BaseModel):
    """Genre/Tag model."""
    asin: str
    name: str
    type: str = Field(..., description="e.g., 'genre' or 'tag'")


class Series(BaseModel):
    """Series model."""
    asin: Optional[str] = None
    name: str
    position: Optional[str] = Field(None, description="Textual position marker like '1'")


class Book(BaseModel):
    """Book model representing an audiobook from Audnexus API."""
    asin: str
    title: str
    subtitle: Optional[str] = None
    authors: List[Person] = Field(default_factory=list)
    narrators: Optional[List[Person]] = Field(default_factory=list)
    description: str = ""
    summary: str = Field("", description="Often contains HTML")
    image: Optional[HttpUrl] = None
    publisher_name: str = Field("", alias="publisherName")
    copyright: Optional[int] = None
    format_type: str = Field("", alias="formatType", description="e.g., 'unabridged'")
    language: str = ""
    literature_type: Optional[Literal["fiction", "nonfiction"]] = Field(None, alias="literatureType")
    genres: Optional[List[Genre]] = Field(default_factory=list)
    rating: str = Field("", description="Note: this is a string in the API")
    region: Region = "us"
    release_date: Optional[datetime] = Field(None, alias="releaseDate")
    runtime_length_min: int = Field(0, alias="runtimeLengthMin")
    series_primary: Optional[Series] = Field(None, alias="seriesPrimary")
    series_secondary: Optional[Series] = Field(None, alias="seriesSecondary")
    isbn: Optional[str] = ""
    is_adult: Optional[bool] = Field(None, alias="isAdult")

    class Config:
        populate_by_name = True  # Allow both alias and field names
        str_strip_whitespace = True


class ChapterItem(BaseModel):
    """Individual chapter item."""
    title: str
    start_offset_ms: int = Field(..., alias="startOffsetMs")
    start_offset_sec: int = Field(..., alias="startOffsetSec")
    length_ms: int = Field(..., alias="lengthMs")

    class Config:
        populate_by_name = True


class Chapter(BaseModel):
    """Chapter response model."""
    asin: str
    brand_intro_duration_ms: int = Field(..., alias="brandIntroDurationMs")
    brand_outro_duration_ms: int = Field(..., alias="brandOutroDurationMs")
    is_accurate: bool = Field(..., alias="isAccurate")
    region: Region = "us"
    runtime_length_ms: int = Field(..., alias="runtimeLengthMs")
    runtime_length_sec: int = Field(..., alias="runtimeLengthSec")
    chapters: List[ChapterItem] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class Author(BaseModel):
    """Author model with rich metadata."""
    asin: str
    name: str
    description: str = ""
    image: Optional[HttpUrl] = None
    genres: Optional[List[Genre]] = Field(default_factory=list)
    region: Region = "us"
    similar: Optional[List[Person]] = Field(default_factory=list)

    class Config:
        populate_by_name = True
        str_strip_whitespace = True


class ApiError(BaseModel):
    """API error response model."""
    status_code: int = Field(..., alias="statusCode")
    error: str
    message: str

    class Config:
        populate_by_name = True
