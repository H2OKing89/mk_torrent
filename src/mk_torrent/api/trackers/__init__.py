"""
Tracker API implementations
"""

from .base import TrackerAPI, TrackerConfig
from .red import RedactedAPI
from .mam import MyAnonaMouseAPI

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
