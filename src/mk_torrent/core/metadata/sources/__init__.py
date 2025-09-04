"""
Metadata extraction sources.

Sources pull raw metadata from various locations:
- embedded: Technical file properties via ffprobe/mutagen
- audnexus: API calls to audnexus.com
- pathinfo: Filename/directory parsing
"""

# Re-export implemented sources
from .embedded import EmbeddedSource
from .audnexus import AudnexusSource
from .pathinfo import PathInfoSource

__all__ = [
    "EmbeddedSource",
    "AudnexusSource",
    "PathInfoSource",
]
