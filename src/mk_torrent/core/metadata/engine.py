"""
Generic metadata processing engine
Tracker-agnostic metadata extraction and processing
"""

from pathlib import Path
from typing import Dict, Any, List, Union, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class MetadataProcessor(ABC):
    """Abstract base for metadata processors"""
    
    @abstractmethod
    def extract(self, source: Union[Path, List[Path]]) -> Dict[str, Any]:
        """Extract metadata from source"""
        pass
    
    @abstractmethod
    def validate(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata completeness"""
        pass
    
    @abstractmethod
    def enhance(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance metadata with external sources"""
        pass

class MetadataEngine:
    """Main metadata engine that delegates to specific processors"""
    
    def __init__(self):
        self.processors = {}
        self._register_processors()
    
    def _register_processors(self):
        """Register available metadata processors"""
        from .audiobook import AudiobookMetadata
        
        self.processors['audiobook'] = AudiobookMetadata()
        # Future processors
        # self.processors['music'] = MusicMetadata()
        # self.processors['video'] = VideoMetadata()
    
    def process(self, source: Union[Path, List[Path]], 
                content_type: Optional[str] = None) -> Dict[str, Any]:
        """Process metadata for given content"""
        
        # Auto-detect content type if not specified
        if not content_type:
            content_type = self._detect_content_type(source)
        
        processor = self.processors.get(content_type)
        if not processor:
            raise ValueError(f"No processor for content type: {content_type}. Available: {list(self.processors.keys())}")
        
        # Extract, validate, and enhance
        metadata = processor.extract(source)
        metadata['validation'] = processor.validate(metadata)
        metadata = processor.enhance(metadata)
        metadata['content_type'] = content_type
        
        return metadata
    
    def _detect_content_type(self, source: Union[Path, List[Path]]) -> str:
        """Auto-detect content type from files"""
        if isinstance(source, list):
            source = source[0] if source else Path()
        
        source = Path(source)
        
        # Check by extension
        if source.suffix.lower() in ['.m4b', '.m4a']:
            # Check if it's an audiobook
            if 'audiobook' in str(source).lower():
                return 'audiobook'
            return 'music'
        elif source.suffix.lower() in ['.mp3', '.flac', '.ogg', '.opus']:
            return 'music'
        elif source.suffix.lower() in ['.mkv', '.mp4', '.avi']:
            return 'video'
        
        # Check by directory structure
        if source.is_dir():
            files = list(source.glob('**/*'))
            if any(f.suffix.lower() == '.m4b' for f in files):
                return 'audiobook'
            elif any(f.suffix.lower() in ['.flac', '.mp3'] for f in files):
                return 'music'
        
        # Default fallback
        return 'unknown'
    
    def list_supported_types(self) -> List[str]:
        """List all supported content types"""
        return list(self.processors.keys())
    
    def register_processor(self, content_type: str, processor: MetadataProcessor):
        """Register a new metadata processor"""
        self.processors[content_type] = processor
        logger.info(f"Registered metadata processor for: {content_type}")

# Convenience function for direct usage
def process_metadata(source: Union[Path, List[Path]], 
                    content_type: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to process metadata"""
    engine = MetadataEngine()
    return engine.process(source, content_type)
