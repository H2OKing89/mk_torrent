#!/usr/bin/env python3
"""
RED Metadata Processing Engine
Handles intelligent metadata extraction, cleaning, and validation for RED compliance
"""

import re
import html
import json
import logging
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup, Comment
from PIL import Image
from rich.console import Console

# Audio metadata libraries
try:
    import mutagen
    from mutagen._file import FileType
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen.oggvorbis import OggVorbis
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    FileType = object  # Fallback for type hints

# MusicBrainz integration (optional)
try:
    import musicbrainzngs
    MUSICBRAINZ_AVAILABLE = True
except ImportError:
    MUSICBRAINZ_AVAILABLE = False

console = Console()
logger = logging.getLogger(__name__)

@dataclass
class AudioFormat:
    """Audio format information"""
    codec: str
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    bit_depth: Optional[int] = None
    vbr: bool = False
    lossless: bool = False

@dataclass
class AlbumArtwork:
    """Album artwork information"""
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    source: str = "unknown"
    confidence: float = 0.0

class HTMLCleaner:
    """Cleans HTML content from metadata sources"""
    
    def __init__(self):
        self.html_tag_pattern = re.compile(r'<[^>]+>')
        self.html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&apos;': "'",
            '&nbsp;': ' ',
            '&mdash;': '—',
            '&ndash;': '–',
            '&hellip;': '…',
            '&copy;': '©',
            '&reg;': '®',
            '&trade;': '™'
        }
    
    def sanitize(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize all string fields in metadata from HTML"""
        if not metadata:
            return metadata
        
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                sanitized[key] = self.clean_html_string(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.clean_html_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def clean_html_string(self, text: str) -> str:
        """Clean HTML from a single string"""
        if not text:
            return text
        
        # Parse with BeautifulSoup for robust HTML handling
        soup = BeautifulSoup(text, 'html.parser')
        
        # Remove comments
        comments = soup.findAll(text=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment.extract()
        
        # Get text content
        clean_text = soup.get_text()
        
        # Decode HTML entities
        clean_text = html.unescape(clean_text)
        
        # Additional entity cleanup
        for entity, replacement in self.html_entities.items():
            clean_text = clean_text.replace(entity, replacement)
        
        # Clean up whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text.strip())
        
        return clean_text

class FormatDetector:
    """Detects audio format and quality information"""
    
    def __init__(self):
        self.supported_formats = {
            '.flac': 'FLAC',
            '.mp3': 'MP3',
            '.m4a': 'AAC',
            '.m4b': 'AAC',  # Audiobook format (AAC container)
            '.aac': 'AAC',
            '.ogg': 'Vorbis',
            '.opus': 'Opus',
            '.wav': 'WAV',
            '.aiff': 'AIFF',
            '.ape': 'APE',
            '.wv': 'WavPack'
        }
    
    def analyze(self, source_files: List[Path]) -> Dict[str, Any]:
        """Analyze audio files and detect format information"""
        if not MUTAGEN_AVAILABLE:
            console.print("[yellow]⚠️ Mutagen not available - limited format detection[/yellow]")
            return self._basic_format_detection(source_files)
        
        audio_files = self._find_audio_files(source_files)
        if not audio_files:
            return {'format': 'Unknown', 'quality': 'Unknown'}
        
        # Analyze the first audio file as representative
        primary_file = audio_files[0]
        try:
            audio = mutagen.File(str(primary_file))
            if not audio:
                return self._basic_format_detection([primary_file])
            
            format_info = self._extract_format_info(audio, primary_file)
            
            # Validate consistency across files
            if len(audio_files) > 1:
                format_info.update(self._validate_consistency(audio_files))
            
            return format_info
            
        except Exception as e:
            logger.error(f"Error analyzing audio file {primary_file}: {e}")
            return self._basic_format_detection([primary_file])
    
    def _find_audio_files(self, source_files: List[Path]) -> List[Path]:
        """Find all audio files in the source"""
        audio_files = []
        
        for file_path in source_files:
            if file_path.is_file():
                if file_path.suffix.lower() in self.supported_formats:
                    audio_files.append(file_path)
            elif file_path.is_dir():
                for ext in self.supported_formats:
                    audio_files.extend(file_path.glob(f"**/*{ext}"))
        
        return sorted(audio_files)
    
    def _extract_format_info(self, audio: FileType, file_path: Path) -> Dict[str, Any]:
        """Extract detailed format information"""
        info = audio.info
        file_ext = file_path.suffix.lower()
        
        format_data = {
            'format': self.supported_formats.get(file_ext, 'Unknown'),
            'extension': file_ext,
            'duration': getattr(info, 'length', 0),
            'bitrate': getattr(info, 'bitrate', None),
            'sample_rate': getattr(info, 'sample_rate', None),
            'channels': getattr(info, 'channels', None),
        }
        
        # Format-specific details
        if isinstance(audio, FLAC):
            format_data.update({
                'lossless': True,
                'bit_depth': getattr(info, 'bits_per_sample', 16),
                'encoding': f"FLAC {getattr(info, 'bits_per_sample', 16)}-bit"
            })
        elif isinstance(audio, MP3):
            bitrate = getattr(info, 'bitrate', None)
            bitrate_mode = getattr(info, 'bitrate_mode', None)
            format_data.update({
                'lossless': False,
                'vbr': bitrate_mode != 0 if bitrate_mode is not None else None,
                'encoding': self._classify_mp3_quality(bitrate, bitrate_mode)
            })
        elif isinstance(audio, MP4):
            bitrate = getattr(info, 'bitrate', None)
            format_data.update({
                'lossless': False,
                'encoding': f"AAC {bitrate}k" if bitrate else "AAC"
            })
            # Special handling for M4B audiobooks
            if file_ext == '.m4b':
                format_data['encoding'] = f"M4B Audiobook ({bitrate}k)" if bitrate else "M4B Audiobook"
        
        return format_data
    
    def _classify_mp3_quality(self, bitrate: Optional[int], bitrate_mode: Optional[int]) -> str:
        """Classify MP3 quality based on bitrate and mode"""
        if not bitrate:
            return "MP3"
        
        if bitrate_mode and bitrate_mode != 0:  # VBR
            if bitrate >= 220:
                return "MP3 V0"
            elif bitrate >= 190:
                return "MP3 V1"
            elif bitrate >= 170:
                return "MP3 V2"
            else:
                return f"MP3 VBR ~{bitrate}k"
        else:  # CBR
            return f"MP3 {bitrate}k"
    
    def _validate_consistency(self, audio_files: List[Path]) -> Dict[str, Any]:
        """Validate format consistency across multiple files"""
        formats = set()
        bitrates = set()
        sample_rates = set()
        
        for file_path in audio_files[:10]:  # Sample first 10 files
            try:
                audio = mutagen.File(file_path)
                if audio and audio.info:
                    formats.add(file_path.suffix.lower())
                    if hasattr(audio.info, 'bitrate') and audio.info.bitrate:
                        bitrates.add(audio.info.bitrate)
                    if hasattr(audio.info, 'sample_rate') and audio.info.sample_rate:
                        sample_rates.add(audio.info.sample_rate)
            except:
                continue
        
        consistency = {
            'format_consistent': len(formats) == 1,
            'bitrate_consistent': len(bitrates) <= 1,
            'sample_rate_consistent': len(sample_rates) <= 1,
            'multiple_formats': list(formats) if len(formats) > 1 else None,
            'multiple_bitrates': list(bitrates) if len(bitrates) > 1 else None
        }
        
        return consistency
    
    def _basic_format_detection(self, source_files: List[Path]) -> Dict[str, Any]:
        """Basic format detection without mutagen"""
        formats = set()
        for file_path in source_files:
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in self.supported_formats:
                    formats.add(self.supported_formats[ext])
        
        return {
            'format': ', '.join(formats) if formats else 'Unknown',
            'encoding': 'Unknown',
            'lossless': 'FLAC' in formats,
            'basic_detection': True
        }

class ImageURLFinder:
    """Discovers and validates album artwork URLs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RedMetadataEngine/1.0 (https://redacted.ch/)'
        })
        
        # Configure MusicBrainz if available
        if MUSICBRAINZ_AVAILABLE:
            musicbrainzngs.set_useragent("RedMetadataEngine", "1.0", "https://redacted.ch/")
    
    def discover(self, metadata: Dict[str, Any]) -> List[AlbumArtwork]:
        """Discover album artwork from multiple sources"""
        artwork_candidates = []
        
        # 1. Check for embedded artwork in files
        embedded = self._check_embedded_artwork(metadata.get('files', []))
        artwork_candidates.extend(embedded)
        
        # 2. Check local folder for image files
        local_images = self._check_folder_images(metadata.get('directory'))
        artwork_candidates.extend(local_images)
        
        # 3. Search MusicBrainz (if available and we have MBID)
        if MUSICBRAINZ_AVAILABLE and metadata.get('musicbrainz_id'):
            mb_artwork = self._search_musicbrainz(metadata['musicbrainz_id'])
            artwork_candidates.extend(mb_artwork)
        
        # 4. Search other sources (placeholder for future implementation)
        # external_artwork = self._search_external_sources(metadata)
        # artwork_candidates.extend(external_artwork)
        
        # Rank and validate candidates
        validated_artwork = self._validate_and_rank_images(artwork_candidates)
        
        return validated_artwork
    
    def _check_embedded_artwork(self, files: List[Path]) -> List[AlbumArtwork]:
        """Check for embedded artwork in audio files (disabled to avoid output flooding)"""
        # Skip embedded artwork check to avoid console flooding with image data
        # User specifically requested to ignore embedded images
        return []
    
    def _check_folder_images(self, directory: Optional[Path]) -> List[AlbumArtwork]:
        """Check for image files in the album directory"""
        if not directory or not directory.is_dir():
            return []
        
        artwork = []
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        # Look for common artwork filenames
        preferred_names = ['cover', 'front', 'folder', 'album', 'artwork']
        
        for image_file in directory.glob("*"):
            if image_file.suffix.lower() not in image_extensions:
                continue
            
            confidence = 0.3  # Base confidence for folder images
            
            # Boost confidence for preferred filenames
            stem_lower = image_file.stem.lower()
            for preferred in preferred_names:
                if preferred in stem_lower:
                    confidence = 0.8
                    break
            
            try:
                # Get image dimensions
                with Image.open(image_file) as img:
                    artwork.append(AlbumArtwork(
                        url=f"file://{image_file}",
                        width=img.width,
                        height=img.height,
                        format=img.format.lower() if img.format else None,
                        source="folder",
                        confidence=confidence
                    ))
            except Exception as e:
                logger.debug(f"Error processing image {image_file}: {e}")
                continue
        
        return artwork
    
    def _search_musicbrainz(self, mbid: str) -> List[AlbumArtwork]:
        """Search for artwork on MusicBrainz Cover Art Archive"""
        if not MUSICBRAINZ_AVAILABLE:
            return []
        
        try:
            result = musicbrainzngs.get_image_list(mbid)
            artwork = []
            
            for image in result.get('images', []):
                if image.get('front', False):  # Prefer front covers
                    artwork.append(AlbumArtwork(
                        url=image['image'],
                        width=None,  # MusicBrainz doesn't provide dimensions
                        height=None,
                        source="musicbrainz",
                        confidence=0.7
                    ))
            
            return artwork
            
        except Exception as e:
            logger.debug(f"Error searching MusicBrainz for artwork: {e}")
            return []
    
    def _validate_and_rank_images(self, candidates: List[AlbumArtwork]) -> List[AlbumArtwork]:
        """Validate and rank artwork candidates"""
        validated = []
        
        for artwork in candidates:
            # Skip validation for embedded/local files (assumed valid)
            if artwork.source in ['embedded_flac', 'embedded_mp3', 'embedded_mp4', 'folder']:
                validated.append(artwork)
                continue
            
            # Validate remote URLs
            if artwork.url.startswith('http'):
                if self._validate_remote_image(artwork.url):
                    validated.append(artwork)
        
        # Sort by confidence (highest first)
        validated.sort(key=lambda x: x.confidence, reverse=True)
        
        return validated
    
    def _validate_remote_image(self, url: str) -> bool:
        """Validate that a remote URL points to a valid image"""
        try:
            response = self.session.head(url, timeout=10)
            content_type = response.headers.get('content-type', '')
            return content_type.startswith('image/') and response.status_code == 200
        except:
            return False

class TagNormalizer:
    """Normalizes genre and style tags for RED compliance"""
    
    def __init__(self):
        # RED-approved genres (simplified list - should be expanded)
        self.red_genres = {
            'rock', 'pop', 'electronic', 'hip-hop', 'jazz', 'classical', 
            'folk', 'country', 'blues', 'reggae', 'punk', 'metal',
            'r&b', 'soul', 'funk', 'disco', 'ambient', 'experimental'
        }
        
        # Common tag mappings
        self.tag_mappings = {
            'rap': 'hip-hop',
            'hiphop': 'hip-hop',
            'hip hop': 'hip-hop',
            'rnb': 'r&b',
            'rhythm and blues': 'r&b',
            'dance': 'electronic',
            'edm': 'electronic',
            'techno': 'electronic',
            'house': 'electronic',
            'trance': 'electronic',
            'alternative': 'rock',
            'indie': 'rock',
            'grunge': 'rock',
            'metalcore': 'metal',
            'death metal': 'metal',
            'black metal': 'metal',
            'heavy metal': 'metal'
        }
    
    def normalize(self, tags: List[str]) -> List[str]:
        """Normalize tags for RED compliance"""
        if not tags:
            return []
        
        normalized = []
        
        for tag in tags:
            if not isinstance(tag, str):
                continue
            
            # Clean and lowercase
            clean_tag = tag.strip().lower()
            
            # Apply mappings
            if clean_tag in self.tag_mappings:
                clean_tag = self.tag_mappings[clean_tag]
            
            # Check if it's a valid RED genre
            if clean_tag in self.red_genres:
                normalized.append(clean_tag.title())
            else:
                # Keep original tag but cleaned up
                normalized.append(tag.strip().title())
        
        # Remove duplicates while preserving order
        seen = set()
        final_tags = []
        for tag in normalized:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                final_tags.append(tag)
        
        return final_tags

class MetadataEngine:
    """Main metadata processing engine for RED compliance"""
    
    def __init__(self):
        self.html_cleaner = HTMLCleaner()
        self.format_detector = FormatDetector()
        self.image_finder = ImageURLFinder()
        self.tag_normalizer = TagNormalizer()
    
    def process_metadata(self, source_files: Union[Path, List[Path]], external_sources: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract and clean metadata for RED compliance"""
        console.print("[cyan]Processing metadata for RED compliance...[/cyan]")
        
        # Ensure source_files is always a list
        if isinstance(source_files, Path):
            source_files = [source_files]
        elif not isinstance(source_files, list):
            source_files = list(source_files)
        
        metadata = {}
        
        # 1. Extract from file tags
        console.print("  [dim]Extracting metadata from files...[/dim]")
        metadata.update(self._extract_file_metadata(source_files))
        
        # 2. Clean HTML entities and tags
        console.print("  [dim]Sanitizing HTML content...[/dim]")
        metadata = self.html_cleaner.sanitize(metadata)
        
        # 3. Detect format/quality from audio analysis
        console.print("  [dim]Analyzing audio format...[/dim]")
        metadata.update(self.format_detector.analyze(source_files))
        
        # 4. Find album artwork URLs
        console.print("  [dim]Discovering album artwork...[/dim]")
        metadata['artwork'] = self.image_finder.discover(metadata)
        
        # 5. Normalize tags for RED requirements
        if metadata.get('tags'):
            console.print("  [dim]Normalizing genre tags...[/dim]")
            metadata['tags'] = self.tag_normalizer.normalize(metadata.get('tags', []))
        
        # 6. Validate RED compliance
        console.print("  [dim]Validating RED compliance...[/dim]")
        validation_result = self._validate_red_compliance(metadata)
        metadata['validation'] = validation_result
        
        console.print(f"[green]✓ Metadata processing complete[/green]")
        if validation_result['errors']:
            console.print(f"[yellow]⚠️ {len(validation_result['errors'])} validation warnings[/yellow]")
        
        return metadata
    
    def _extract_file_metadata(self, source_files: List[Path]) -> Dict[str, Any]:
        """Extract metadata from audio files"""
        if not MUTAGEN_AVAILABLE:
            console.print("[yellow]⚠️ Mutagen not available - using basic extraction[/yellow]")
            return self._basic_metadata_extraction(source_files)
        
        metadata = {}
        audio_files = []
        
        # Find audio files
        for file_path in source_files:
            if file_path.is_file() and file_path.suffix.lower() in ['.flac', '.mp3', '.m4a', '.m4b', '.ogg']:
                audio_files.append(file_path)
            elif file_path.is_dir():
                for ext in ['.flac', '.mp3', '.m4a', '.m4b', '.ogg']:
                    audio_files.extend(file_path.glob(f"**/*{ext}"))
        
        if not audio_files:
            return {'files': source_files}
        
        # Extract from first audio file as representative
        try:
            primary_file = audio_files[0]
            audio = mutagen.File(primary_file)
            
            if audio:
                # Common tags across formats
                metadata.update({
                    'artist': self._extract_tag(audio, 'artist'),
                    'album': self._extract_tag(audio, 'album'),
                    'title': self._extract_tag(audio, 'title'),
                    'date': self._extract_tag(audio, 'date'),
                    'genre': self._extract_tag(audio, 'genre'),
                    'comment': self._extract_tag(audio, 'genre'),  # genre fallback for comment
                    'files': audio_files,
                    'directory': primary_file.parent
                })
                
                # Extract audio info (bitrate, VBR, sample rate, etc.)
                if hasattr(audio, 'info') and audio.info:
                    info = audio.info
                    
                    # Basic audio properties
                    if hasattr(info, 'bitrate') and info.bitrate:
                        metadata['bitrate'] = info.bitrate
                    
                    if hasattr(info, 'length') and info.length:
                        metadata['duration'] = info.length
                    
                    if hasattr(info, 'sample_rate') and info.sample_rate:
                        metadata['sample_rate'] = info.sample_rate
                    
                    if hasattr(info, 'channels') and info.channels:
                        metadata['channels'] = info.channels
                    
                    if hasattr(info, 'bits_per_sample') and info.bits_per_sample:
                        metadata['bit_depth'] = info.bits_per_sample
                    
                    # VBR detection (format-specific)
                    metadata['vbr'] = self._detect_vbr(audio, info)
                
                # Extract year from date
                if metadata.get('date'):
                    year_match = re.search(r'\d{4}', str(metadata['date']))
                    if year_match:
                        metadata['year'] = year_match.group()
                
                # Extract genre tags as list
                if metadata.get('genre'):
                    if isinstance(metadata['genre'], str):
                        metadata['tags'] = [g.strip() for g in metadata['genre'].split(',')]
                    else:
                        metadata['tags'] = [str(metadata['genre'])]
        
        except Exception as e:
            logger.error(f"Error extracting metadata from {primary_file}: {e}")
        
        return metadata
    
    def _detect_vbr(self, audio: Any, info: Any) -> bool:
        """Detect if audio file uses Variable Bitrate (VBR)"""
        try:
            # MP3 VBR detection
            if isinstance(audio, MP3):
                # Check for VBR header frames (Xing, VBRI, Info)
                if hasattr(info, 'bitrate_mode'):
                    return info.bitrate_mode != 0  # 0 = CBR, others = VBR variants
                
                # Fallback: look for common VBR indicators in the file
                if hasattr(audio, 'tags'):
                    # Check for TXXX:LAME tag which often indicates VBR
                    for key in audio.tags.keys() if audio.tags else []:
                        if key.startswith('TXXX:') and 'LAME' in str(audio.tags[key]):
                            return True
                
                return False
            
            # MP4/M4A/M4B files 
            elif isinstance(audio, MP4):
                # M4A/M4B generally use VBR by default, but audiobooks often use CBR
                # Check the file extension and bitrate consistency to determine
                file_path = getattr(audio, 'filename', '')
                
                if file_path and file_path.endswith('.m4b'):
                    # Audiobooks typically use CBR for consistency
                    return False
                elif hasattr(info, 'bitrate') and info.bitrate:
                    # For other MP4 files, high consistent bitrates suggest CBR
                    # while lower or unusual bitrates suggest VBR
                    if info.bitrate > 200000:  # > 200kbps likely CBR
                        return False
                    return True
                
                return True  # Default assumption for MP4
            
            # FLAC is always lossless (technically VBR but not in the lossy sense)
            elif isinstance(audio, FLAC):
                return False  # Report as non-VBR for RED compliance
            
            # Other formats default
            else:
                return False
                
        except Exception as e:
            logger.debug(f"Error detecting VBR: {e}")
            return False
    
    def _extract_tag(self, audio: Any, tag_type: str) -> Optional[str]:
        """Extract a specific tag from audio metadata with format-specific handling."""
        if not audio:
            return None
        
        # Define tag mappings for different formats
        tag_mappings = {
            'title': {
                'FLAC': ['TITLE', 'title'],
                'MP3': ['TIT2', 'title'],
                'MP4': ['©nam', 'title'],  # iTunes-style
                'default': ['title', 'TITLE', 'TIT2', '©nam']
            },
            'artist': {
                'FLAC': ['ARTIST', 'artist'],
                'MP3': ['TPE1', 'artist'],
                'MP4': ['©ART', 'artist'],  # iTunes-style
                'default': ['artist', 'ARTIST', 'TPE1', '©ART']
            },
            'album': {
                'FLAC': ['ALBUM', 'album'],
                'MP3': ['TALB', 'album'],
                'MP4': ['©alb', 'album'],  # iTunes-style
                'default': ['album', 'ALBUM', 'TALB', '©alb']
            },
            'genre': {
                'FLAC': ['GENRE', 'genre'],
                'MP3': ['TCON', 'genre'],
                'MP4': ['©gen', 'genre'],
                'default': ['genre', 'GENRE', 'TCON', '©gen']
            },
            'date': {
                'FLAC': ['DATE', 'date'],
                'MP3': ['TDRC', 'date'],
                'MP4': ['©day', 'year_or_date', 'date'],  # iTunes uses year_or_date
                'default': ['date', 'DATE', 'TDRC', '©day']
            },
            'track_number': {
                'FLAC': ['TRACKNUMBER', 'tracknumber'],
                'MP3': ['TRCK', 'tracknumber'],
                'MP4': ['trkn', 'track_number', 'tracknumber'],
                'default': ['tracknumber', 'TRACKNUMBER', 'TRCK', 'trkn']
            }
        }
        
        # Determine file format
        file_format = 'MP4'  # Default to MP4 for M4B files
        if hasattr(audio, 'mime'):
            mime_to_format = {
                'audio/flac': 'FLAC',
                'audio/mp3': 'MP3',
                'audio/mpeg': 'MP3',
                'audio/mp4': 'MP4',
                'audio/m4a': 'MP4',
                'audio/m4b': 'MP4'
            }
            file_format = mime_to_format.get(str(audio.mime), 'MP4')
        
        # Get appropriate tag names for this format and tag type
        tag_names = tag_mappings.get(tag_type, {}).get(file_format, tag_mappings.get(tag_type, {}).get('default', []))
        
        # Try each tag name until we find a value
        for tag_name in tag_names:
            try:
                value = audio.get(tag_name)
                if value:
                    # Handle different value types
                    if isinstance(value, list):
                        # Take first non-empty value
                        for item in value:
                            if item and str(item).strip():
                                return str(item).strip()
                    elif isinstance(value, tuple):
                        # For track numbers like (1, 10)
                        return str(value[0]) if value[0] else None
                    else:
                        # Single value
                        result = str(value).strip()
                        if result:
                            return result
            except (AttributeError, KeyError, TypeError):
                continue
        
        return None
    
    def _basic_metadata_extraction(self, source_files: List[Path]) -> Dict[str, Any]:
        """Basic metadata extraction from file/folder names"""
        if not source_files:
            return {}
        
        # Try to extract from folder structure
        primary_path = source_files[0]
        if primary_path.is_file():
            primary_path = primary_path.parent
        
        # Common folder naming patterns: "Artist - Album (Year)"
        folder_name = primary_path.name
        
        # Try to parse folder name
        pattern = r'^(.+?)\s*-\s*(.+?)(?:\s*\((\d{4})\))?(?:\s*\[.*\])?$'
        match = re.match(pattern, folder_name)
        
        metadata = {'files': source_files, 'directory': primary_path}
        
        if match:
            metadata.update({
                'artist': match.group(1).strip(),
                'album': match.group(2).strip(),
                'year': match.group(3) if match.group(3) else None
            })
        else:
            metadata['album'] = folder_name
        
        return metadata
    
    def _validate_red_compliance(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata for RED compliance"""
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ['artist', 'album']
        for field in required_fields:
            if not metadata.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Recommended fields
        recommended_fields = ['year', 'format', 'encoding']
        for field in recommended_fields:
            if not metadata.get(field):
                warnings.append(f"Missing recommended field: {field}")
        
        # Format validation
        if metadata.get('format'):
            if metadata['format'] not in ['FLAC', 'MP3', 'AAC']:
                warnings.append(f"Uncommon format for RED: {metadata['format']}")
        
        # Year validation
        if metadata.get('year'):
            try:
                year = int(metadata['year'])
                if year < 1900 or year > 2030:
                    warnings.append(f"Unusual year: {year}")
            except ValueError:
                errors.append(f"Invalid year format: {metadata['year']}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'score': max(0, 100 - len(errors) * 20 - len(warnings) * 5)
        }

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extracted metadata for RED compliance.
        
        Args:
            metadata: Dictionary containing extracted metadata
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Check required fields
        required_fields = ['title', 'artist', 'album']
        for field in required_fields:
            if not metadata.get(field):
                validation['errors'].append(f"Missing required field: {field}")
                validation['is_valid'] = False
        
        # Check format compatibility
        valid_formats = ['FLAC', 'MP3', 'AAC']
        if metadata.get('format') not in valid_formats:
            validation['warnings'].append(f"Format {metadata.get('format')} may not be optimal for RED")
        
        # Check bitrate for lossy formats
        if metadata.get('format') in ['MP3', 'AAC']:
            bitrate = metadata.get('bitrate', 0)
            if bitrate < 320000:  # 320 kbps
                validation['warnings'].append(f"Bitrate {bitrate//1000}kbps is below recommended 320kbps for lossy format")
        
        # Check duration
        duration = metadata.get('duration', 0)
        if duration < 30:  # Less than 30 seconds
            validation['warnings'].append("Track duration is very short")
        elif duration > 7200:  # More than 2 hours
            validation['warnings'].append("Track duration is very long")
        
        return validation

# Convenience function for external use
def process_album_metadata(source_path: Union[str, Path], **kwargs) -> Dict[str, Any]:
    """Process metadata for a single album/directory"""
    source_path = Path(source_path)
    
    if source_path.is_file():
        source_files = [source_path]
    else:
        source_files = [source_path]
    
    engine = MetadataEngine()
    return engine.process_metadata(source_files, kwargs.get('external_sources'))

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python feature_metadata_engine.py <path_to_album>")
        sys.exit(1)
    
    album_path = Path(sys.argv[1])
    result = process_album_metadata(album_path)
    
    print(json.dumps(result, indent=2, default=str))
