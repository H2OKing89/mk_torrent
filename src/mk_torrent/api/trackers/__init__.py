"""
DEPRECATED: Tracker API implementations have moved.

This entire module is deprecated. Please update your imports:
- mk_torrent.api.trackers.base -> mk_torrent.trackers.base
- mk_torrent.api.trackers.red -> mk_torrent.trackers.red.adapter
- mk_torrent.api.trackers.mam -> mk_torrent.trackers.mam.adapter
"""

import warnings

warnings.warn(
    "mk_torrent.api.trackers is deprecated; use mk_torrent.trackers.*",
    DeprecationWarning,
    stacklevel=2,
)

# Import through shims (which handle their own deprecation warnings)
try:
    from .base import TrackerAPI, TrackerConfig
except ImportError:
    from mk_torrent.trackers.base import TrackerAPI, TrackerConfig

try:
    from .red import RedactedAPI
except ImportError:
    from mk_torrent.trackers.red.adapter import RedactedAPI

try:
    from .mam import MyAnonaMouseAPI
except ImportError:
    from mk_torrent.trackers.mam.adapter import MyAnonaMouseAPI

__all__ = ["TrackerAPI", "TrackerConfig", "RedactedAPI", "MyAnonaMouseAPI"]

# Registry of available trackers
TRACKER_REGISTRY = {
    "red": RedactedAPI,
    "redacted": RedactedAPI,
    "mam": MyAnonaMouseAPI,
    "myanonamouse": MyAnonaMouseAPI,
    # Future trackers will be added here
    # 'ops': OrpheusAPI,
    # 'orpheus': OrpheusAPI,
}


def get_tracker_api(tracker_name: str, **kwargs):
    """Factory function to get appropriate tracker API"""
    tracker_class = TRACKER_REGISTRY.get(tracker_name.lower())
    if not tracker_class:
        raise ValueError(
            f"Unknown tracker: {tracker_name}. Available: {list(TRACKER_REGISTRY.keys())}"
        )
    return tracker_class(**kwargs)


def list_available_trackers():
    """List all available tracker implementations"""
    return list(TRACKER_REGISTRY.keys())
