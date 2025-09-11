"""
DEPRECATED: This module has been consolidated into mk_torrent.core.upload.spec

This file will be removed in 4 weeks (by 2025-10-09).
Please update your imports to use mk_torrent.core.upload.spec instead.
"""

import warnings
from mk_torrent.core.upload.spec import (
    # Enums
    Category,
    AudioFormat,
    MediaType,
    ReleaseType,
    ArtistType,
    # Classes
    BitrateEncoding,
    Credits,
    ReleaseInfo,
    TorrentFile,
    UploadSpec,
    UploadResult,
    Artist,
)

# Issue deprecation warning
warnings.warn(
    "mk_torrent.trackers.upload_spec is deprecated. "
    "Use mk_torrent.core.upload.spec instead. "
    "This module will be removed by 2025-10-09.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything for backward compatibility
__all__ = [
    "Category",
    "AudioFormat",
    "MediaType",
    "ReleaseType",
    "ArtistType",
    "BitrateEncoding",
    "Credits",
    "ReleaseInfo",
    "TorrentFile",
    "UploadSpec",
    "UploadResult",
    "Artist",
]
