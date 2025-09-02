"""
Metadata processing engines for different content types
"""

from .engine import MetadataEngine, MetadataProcessor
from .audiobook import AudiobookMetadata

__all__ = ['MetadataEngine', 'MetadataProcessor', 'AudiobookMetadata']
