"""
DEPRECATED: Audnexus client moved to metadata suite

This module is deprecated as of 2025-01-09 and will be removed on 2025-02-09.
All Audnexus functionality has been consolidated into the core metadata system.

Use mk_torrent.core.metadata.sources.audnexus instead.
"""

import warnings

# Re-export from the canonical location
from mk_torrent.core.metadata.sources.audnexus import (
    AudnexusSource as AudnexusClient,
    get_audnexus_metadata,
    get_audnexus_metadata_async,
    extract_asin_from_path,
)

warnings.warn(
    "mk_torrent.integrations.audnexus_client is deprecated. "
    "Use mk_torrent.core.metadata.sources.audnexus instead. "
    "This module will be removed on 2025-02-09.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "AudnexusClient",
    "get_audnexus_metadata",
    "get_audnexus_metadata_async",
    "extract_asin_from_path",
]
