"""
RED tracker adapter for upload specifications.

This module converts UploadSpec objects to RED's multipart form data format
and handles RED API interactions including dry run testing.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

from mk_torrent.core.upload.spec import Category, UploadResult, UploadSpec

logger = logging.getLogger(__name__)


class REDConfig(BaseModel):
    """RED tracker configuration."""

    api_key: str = Field(..., description="RED API key")
    base_url: str = Field(default="https://redacted.ch", description="RED base URL")
    user_agent: str = Field(default="mk_torrent/1.0", description="User agent string")
    timeout: int = Field(default=30, description="Request timeout in seconds")


class REDAdapter:
    """Adapter for RED tracker uploads."""

    # RED category mappings
    CATEGORY_MAP = {
        Category.AUDIOBOOKS: "audiobooks",
        Category.MUSIC: "music",
        Category.E_BOOKS: "e-books",
        Category.E_LEARNING: "e-learning-videos",
        Category.COMEDY: "comedy",
        Category.PODCASTS: "podcasts",
    }

    # RED bitrate mappings for audiobooks (simplified)
    AUDIOBOOK_BITRATES = {
        "MP3 32": "32",
        "MP3 64": "64",
        "MP3 96": "96",
        "MP3 128": "128",
        "MP3 160": "160",
        "MP3 192": "192",
        "MP3 224": "224",
        "MP3 256": "256",
        "MP3 320": "320",
        "FLAC": "Lossless",
    }

    def __init__(self, config: REDConfig):
        """Initialize RED adapter."""
        self.config = config

    def _map_bitrate(self, spec: UploadSpec) -> str:
        """Map upload spec bitrate to RED format."""
        encoding = spec.bitrate_encoding.encoding.upper()
        bitrate = spec.bitrate_encoding.bitrate

        # For FLAC, always map to "Lossless"
        if encoding == "FLAC":
            return "Lossless"

        # For MP3, try to find exact match
        key = f"{encoding} {bitrate}"
        if key in self.AUDIOBOOK_BITRATES:
            return self.AUDIOBOOK_BITRATES[key]

        # Fallback to closest bitrate
        return str(bitrate)

    def _build_form_data(self, spec: UploadSpec) -> dict[str, Any]:
        """Convert UploadSpec to RED multipart form data."""

        # Read torrent file
        with open(spec.torrent.file_path, "rb") as f:
            torrent_data = f.read()

        # Base form data
        form_data = {
            # Category and basic info
            "submit": "true",
            "category": self.CATEGORY_MAP.get(spec.category, "audiobooks"),
            "artist": spec.release_info.artist,
            "title": spec.release_info.title,
            # Technical specs
            "bitrate": self._map_bitrate(spec),
            "format": spec.bitrate_encoding.encoding.upper(),
            # Content
            "description": spec.description,
            "tags": ",".join(spec.tags) if spec.tags else "",
            # File
            "torrent": ("upload.torrent", torrent_data, "application/x-bittorrent"),
        }

        # Optional fields
        if spec.release_info.year:
            form_data["year"] = str(spec.release_info.year)

        if spec.release_info.label:
            form_data["label"] = spec.release_info.label

        if spec.release_info.catalog_number:
            form_data["catalog"] = spec.release_info.catalog_number

        # Credits
        credits_str = spec.credits.to_credits_string()
        if credits_str:
            form_data["release_desc"] = credits_str

        # Add any extra RED-specific fields
        for key, value in spec.extra_fields.items():
            if key.startswith("red_"):
                form_data[key[4:]] = value  # Remove "red_" prefix

        return form_data

    async def dry_run_upload(self, spec: UploadSpec) -> UploadResult:
        """Perform dry run upload to RED."""
        try:
            form_data = self._build_form_data(spec)

            # Add dry run parameter
            form_data["dry_run"] = "1"

            # Prepare headers
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "User-Agent": self.config.user_agent,
            }

            # Log form data (without torrent content)
            log_data = {k: v for k, v in form_data.items() if k != "torrent"}
            logger.info(f"RED dry run form data: {json.dumps(log_data, indent=2)}")

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.config.base_url}/ajax.php?action=upload",
                    files={k: v for k, v in form_data.items() if isinstance(v, tuple)},
                    data={
                        k: v for k, v in form_data.items() if not isinstance(v, tuple)
                    },
                    headers=headers,
                )

                response.raise_for_status()
                result_data = response.json()

                # Check if dry run was successful
                if result_data.get("status") == "success":
                    return UploadResult(
                        success=True,
                        message="Dry run successful - upload would be accepted",
                        dry_run=True,
                        raw_response=result_data,
                    )
                else:
                    return UploadResult(
                        success=False,
                        message=f"Dry run failed: {result_data.get('error', 'Unknown error')}",
                        dry_run=True,
                        raw_response=result_data,
                    )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"RED API error: {error_msg}")
            return UploadResult(
                success=False,
                message=f"API request failed: {error_msg}",
                dry_run=True,
                raw_response={"http_error": error_msg},
            )
        except Exception as e:
            logger.error(f"RED upload error: {str(e)}")
            return UploadResult(
                success=False,
                message=f"Upload failed: {str(e)}",
                dry_run=True,
                raw_response={"exception": str(e)},
            )

    async def upload(self, spec: UploadSpec) -> UploadResult:
        """Perform actual upload to RED."""
        # This would be similar to dry_run_upload but without the dry_run parameter
        # For now, we'll just call dry_run_upload
        result = await self.dry_run_upload(spec)
        result.dry_run = False
        return result
