"""
DEPRECATED: This module has been moved to mk_torrent.integrations.qbittorrent

This file will be removed in 4 weeks (by 2025-10-09).
Please update your imports to use mk_torrent.integrations.qbittorrent instead.
"""

import warnings
from mk_torrent.integrations.qbittorrent import *  # noqa: F401,F403

# Issue deprecation warning
warnings.warn(
    "mk_torrent.api.qbittorrent is deprecated. "
    "Use mk_torrent.integrations.qbittorrent instead. "
    "This module will be removed by 2025-10-09.",
    DeprecationWarning,
    stacklevel=2,
)
