"""
Core metadata processing system for mk_torrent.

This module provides a clean, extensible architecture for extracting,
validating, and mapping metadata across different content types.
"""

from .base import (
    AudiobookMeta,
    ValidationResult,
    MetadataSource,
    MetadataService,
    MetadataValidator,
    MetadataProcessor,
    MetadataMapper,
    Source,
    MetadataDict,
)
from .engine import MetadataEngine, process_metadata
from .exceptions import (
    MetadataError,
    SourceUnavailable,
    MetadataConflict,
    ValidationError,
    ProcessorNotFound,
    ConfigurationError,
    ExtractionError,
)

__all__ = [
    # Core data models
    "AudiobookMeta",
    "ValidationResult",
    
    # Protocols/interfaces
    "MetadataSource",
    "MetadataService", 
    "MetadataValidator",
    "MetadataProcessor",
    "MetadataMapper",
    
    # Main engine
    "MetadataEngine",
    "process_metadata",
    
    # Exceptions
    "MetadataError",
    "SourceUnavailable",
    "MetadataConflict",
    "ValidationError",
    "ProcessorNotFound",
    "ConfigurationError",
    "ExtractionError",
    
    # Type aliases
    "Source",
    "MetadataDict",
]

__version__ = "1.0.0"
