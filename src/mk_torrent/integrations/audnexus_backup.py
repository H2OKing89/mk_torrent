"""
DEPRECATED: Audnexus integration moved to metadata suite

This module is deprecated as of 2025-01-09 and will be removed on 2025-02-09.
All Audnexus functionality has been consolidated into the core metadata system.

Use mk_torrent.core.metadata.sources.audnexus instead.

Migration guide:
- AudnexusAPI -> AudnexusSource
- get_audnexus_metadata -> get_audnexus_metadata (same function)
- get_audnexus_metadata_async -> get_audnexus_metadata_async (same function)
"""

import warnings
from typing import Any
import logging
import importlib.util

# Re-export from the canonical location
from mk_torrent.core.metadata.sources.audnexus import (
    AudnexusSource,
    get_audnexus_metadata,
    get_audnexus_metadata_async,
    extract_asin_from_path,
    # Type definitions
    AuthorData,
    NarratorData,
    GenreData,
    SeriesData,
    AudnexusBookResponse,
)

warnings.warn(
    "mk_torrent.integrations.audnexus is deprecated. "
    "Use mk_torrent.core.metadata.sources.audnexus instead. "
    "All Audnexus functionality has been consolidated into the metadata system. "
    "This module will be removed on 2025-02-09.",
    DeprecationWarning,
    stacklevel=2,
)


class AudnexusAPI(AudnexusSource):
    """DEPRECATED: Use AudnexusSource from core.metadata.sources.audnexus instead."""

    def __init__(self, base_url: str = "https://api.audnex.us") -> None:
        warnings.warn(
            "AudnexusAPI is deprecated. Use AudnexusSource from "
            "mk_torrent.core.metadata.sources.audnexus instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(base_url=base_url)

    def fetch_book_metadata_sync(self, asin: str) -> dict[str, Any] | None:
        """DEPRECATED: Use extract() method instead."""
        warnings.warn(
            "fetch_book_metadata_sync() is deprecated. Use extract() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.extract(asin)

    async def fetch_book_metadata(self, asin: str) -> dict[str, Any] | None:
        """DEPRECATED: Use extract_async() method instead."""
        warnings.warn(
            "fetch_book_metadata() is deprecated. Use extract_async() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self.extract_async(asin)


__all__ = [
    "AudnexusAPI",  # Deprecated alias
    "get_audnexus_metadata",
    "get_audnexus_metadata_async",
    "extract_asin_from_path",
    "AuthorData",
    "NarratorData",
    "GenreData",
    "SeriesData",
    "AudnexusBookResponse",
]

# Check for optional dependencies
HTTPX_AVAILABLE = importlib.util.find_spec("httpx") is not None
NH3_AVAILABLE = importlib.util.find_spec("nh3") is not None

logger = logging.getLogger(__name__)

# Note: The original AudnexusAPI implementation has been replaced with the
# core.metadata.sources.audnexus.AudnexusSource implementation.
# All functionality is now available through the inherited class above.
