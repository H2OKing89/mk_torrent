"""
Audiobook-specific metadata processor
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Union
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

class AudiobookMetadata(MetadataProcessor):
    """Metadata processor for audiobooks"""
    
    def extract(self, source: Union[Path, List[Path]]) -> Dict[str, Any]:
        """Extract metadata from audiobook source"""
        source_path = Path(source) if isinstance(source, (str, Path)) else source[0]
        
        metadata = {
            'type': 'audiobook',
            'source_path': str(source_path),
            'title': '',
            'author': '',
            'narrator': '',
            'series': '',
            'volume': '',
            'year': '',
            'duration': '',
            'format': '',
            'encoding': '',
            'chapters': [],
            'description': '',
            'genre': [],
            'isbn': '',
            'asin': '',
            'publisher': '',
            'language': 'en',
            'artwork_url': ''
        }
        
        # Extract from filename/folder structure
        metadata.update(self._extract_from_path(source_path))
        
        # Extract from audio files if available
        if source_path.is_dir():
            audio_files = list(source_path.glob('*.m4b')) or list(source_path.glob('*.mp3'))
            if audio_files:
                metadata.update(self._extract_from_audio_file(audio_files[0]))
        elif source_path.suffix.lower() in ['.m4b', '.mp3']:
            metadata.update(self._extract_from_audio_file(source_path))
        
        return metadata
    
    def _extract_from_path(self, path: Path) -> Dict[str, Any]:
        """Extract metadata from file/folder path"""
        metadata = {}
        
        # Parse filename pattern: "Title - vol_XX (YEAR) (AUTHOR) {ASIN.XXXXX} [UPLOADER]"
        path_name = path.name if path.is_dir() else path.parent.name
        
        import re
        
        # Extract title and volume
        if ' - vol_' in path_name:
            title_part = path_name.split(' - vol_')[0]
            metadata['title'] = title_part.strip()
            metadata['album'] = title_part.strip()  # For RED compatibility
            
            volume_part = path_name.split(' - vol_')[1].split()[0]
            metadata['volume'] = volume_part
        else:
            # Fallback - extract title before first parenthesis
            title_match = re.match(r'^([^(]+)', path_name)
            if title_match:
                metadata['title'] = title_match.group(1).strip()
                metadata['album'] = title_match.group(1).strip()
        
        # Extract year (first set of parentheses with 4 digits)
        year_match = re.search(r'\((\d{4})\)', path_name)
        if year_match:
            metadata['year'] = year_match.group(1)
        
        # Extract author (second set of parentheses, after year)
        if year_match:
            # Look for next parentheses after year
            after_year = path_name[year_match.end():]
            author_match = re.search(r'\(([^)]+)\)', after_year)
            if author_match:
                author = author_match.group(1).strip()
                metadata['author'] = author
                metadata['artists'] = [author]  # For RED compatibility
        
        # Extract ASIN
        asin_match = re.search(r'\{ASIN\.([^}]+)\}', path_name)
        if asin_match:
            metadata['asin'] = asin_match.group(1)
        
        # Extract uploader
        uploader_match = re.search(r'\[([^\]]+)\]$', path_name)
        if uploader_match:
            metadata['uploader'] = uploader_match.group(1)
        
        # Set defaults for RED requirements
        if not metadata.get('artists'):
            metadata['artists'] = [metadata.get('author', 'Unknown')]
        
        if not metadata.get('album'):
            metadata['album'] = metadata.get('title', 'Unknown')
        
        return metadata
        asin_match = re.search(r'ASIN\.([A-Z0-9]+)', path_str)
        if asin_match:
            metadata['asin'] = asin_match.group(1)
        
        return metadata
    
    def _extract_from_audio_file(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from audio file tags"""
        metadata = {}
        
        try:
            # This would use mutagen or similar library
            # For now, just basic file info
            stat = file_path.stat()
            metadata['file_size'] = stat.st_size
            metadata['format'] = file_path.suffix.upper().lstrip('.')
            
            # TODO: Add actual audio metadata extraction
            # import mutagen
            # audio_file = mutagen.File(file_path)
            # if audio_file:
            #     metadata['title'] = audio_file.get('TIT2', [''])[0]
            #     metadata['author'] = audio_file.get('TPE1', [''])[0]
            #     etc.
            
        except Exception as e:
            logger.warning(f"Failed to extract audio metadata from {file_path}: {e}")
        
        return metadata
    
    def validate(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate audiobook metadata completeness"""
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ['title', 'author']
        for field in required_fields:
            if not metadata.get(field):
                errors.append(f"Missing {field}")
        
        # Recommended fields
        recommended_fields = ['year', 'narrator', 'duration']
        for field in recommended_fields:
            if not metadata.get(field):
                warnings.append(f"Missing recommended field: {field}")
        
        # Validate year format
        if metadata.get('year'):
            try:
                year_int = int(metadata['year'])
                if year_int < 1800 or year_int > 2030:
                    warnings.append(f"Unusual year: {year_int}")
            except ValueError:
                errors.append(f"Invalid year format: {metadata['year']}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'completeness': len([f for f in required_fields + recommended_fields if metadata.get(f)]) / len(required_fields + recommended_fields)
        }
    
    def enhance(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance metadata with external sources"""
        enhanced = metadata.copy()
        
        # TODO: Add external data source integration
        # - Audible API lookup by ASIN
        # - Goodreads integration
        # - ISBN database lookup
        # - Automatic genre classification
        
        # For now, just add some derived fields
        if enhanced.get('title') and enhanced.get('author'):
            enhanced['display_name'] = f"{enhanced['title']} by {enhanced['author']}"
        
        if enhanced.get('series') and enhanced.get('volume'):
            enhanced['series_info'] = f"{enhanced['series']} #{enhanced['volume']}"
        
        # Add tags based on content
        tags = []
        if enhanced.get('narrator'):
            tags.append('narrated')
        if enhanced.get('series'):
            tags.append('series')
        if enhanced.get('asin'):
            tags.append('audible')
        
        enhanced['tags'] = tags
        
        return enhanced
