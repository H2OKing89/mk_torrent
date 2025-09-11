"""
DEPRECATED: This module has been moved to mk_torrent.trackers.base

This file will be removed in 4 weeks (by 2025-10-09).
Please update your imports to use mk_torrent.trackers.base instead.
"""

import warnings
from mk_torrent.trackers.base import *  # noqa: F401,F403

# Issue deprecation warning
warnings.warn(
    "mk_torrent.api.trackers.base is deprecated. "
    "Use mk_torrent.trackers.base instead. "
    "This module will be removed by 2025-10-09.",
    DeprecationWarning,
    stacklevel=2,
)
