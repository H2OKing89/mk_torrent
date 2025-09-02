"""
Feature modules for extended functionality.

This module provides compatibility shims during the migration to the new
metadata core architecture. Legacy imports will continue to work while
we transition to the new system.
"""

import warnings
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

# Import new core metadata system
from ..core.metadata import MetadataEngine as NewMetadataEngine, process_metadata as new_process_metadata

# Legacy compatibility - import old metadata engine  
try:
    from .metadata_engine import MetadataEngine as LegacyMetadataEngine, process_album_metadata
    LEGACY_AVAILABLE = True
except ImportError:
    LEGACY_AVAILABLE = False
    LegacyMetadataEngine = None
    process_album_metadata = None


class MetadataEngine:
    """
    Compatibility wrapper for MetadataEngine during migration.
    
    This wrapper provides the legacy interface while delegating to the new
    core metadata system when possible.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize with backward compatibility."""
        # Create new engine
        self._new_engine = NewMetadataEngine()
        
        # Keep legacy engine if available for fallback
        self._legacy_engine = None
        if LEGACY_AVAILABLE and LegacyMetadataEngine and (args or kwargs):
            # If specific args/kwargs passed, use legacy engine
            self._legacy_engine = LegacyMetadataEngine(*args, **kwargs)
        
        # Issue deprecation warning
        warnings.warn(
            "Importing MetadataEngine from features is deprecated. "
            "Use 'from mk_torrent.core.metadata import MetadataEngine' instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def process_metadata(self, source_files: Union[Path, List[Path]], 
                        external_sources: Optional[Dict] = None) -> Dict[str, Any]:
        """Process metadata with backward compatibility."""
        # Try new engine first
        try:
            if isinstance(source_files, list):
                source = source_files[0] if source_files else Path()
            else:
                source = source_files
            
            result = self._new_engine.process_full_pipeline(source)
            
            # Transform to legacy format if needed
            if result.get("success"):
                return result["metadata"]
            else:
                # Fall back to legacy if new engine failed
                if self._legacy_engine:
                    return self._legacy_engine.process_metadata(source_files, external_sources)
                else:
                    raise RuntimeError("Metadata processing failed")
                    
        except Exception as e:
            # Fall back to legacy engine if available
            if self._legacy_engine:
                return self._legacy_engine.process_metadata(source_files, external_sources)
            else:
                raise e
    
    def __getattr__(self, name):
        """Delegate unknown attributes to legacy engine if available."""
        if self._legacy_engine and hasattr(self._legacy_engine, name):
            return getattr(self._legacy_engine, name)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


# Legacy function compatibility
def process_metadata(source: Union[Path, List[Path]], 
                    content_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Legacy process_metadata function for backward compatibility.
    
    This function maintains the old interface while using the new core system.
    """
    warnings.warn(
        "Importing process_metadata from features is deprecated. "
        "Use 'from mk_torrent.core.metadata import process_metadata' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    return new_process_metadata(source, content_type)


# Export compatibility interface
__all__ = [
    "MetadataEngine",
    "process_metadata",
]

# Add legacy exports if available
if LEGACY_AVAILABLE:
    __all__.extend([
        "process_album_metadata",  # Keep for strict backward compatibility
    ])
