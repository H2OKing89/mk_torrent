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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup, Comment
from PIL import Image
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Modern HTML sanitization
try:
    import nh3
    NH3_AVAILABLE = True
except ImportError:
    NH3_AVAILABLE = False

# Audio metadata libraries
try:
    import mutagen
    from mutagen._file import File
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen.oggvorbis import OggVorbis
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    File = object  # Fallback

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
        """Clean HTML from a single string using modern nh3 sanitizer"""
        if not text:
            return text
        
        try:
            # First, unescape any HTML entities that might be in the JSON
            unescaped_text = html.unescape(text)
            
            if NH3_AVAILABLE:
                # Use nh3 for modern, fast HTML sanitization
                # Strip all HTML tags for plain text output
                clean_text = nh3.clean(unescaped_text, tags=set(), attributes={})
                
                # Clean up whitespace
                clean_text = re.sub(r'\s+', ' ', clean_text)
                
                # Decode any remaining HTML entities that nh3 might have re-encoded
                clean_text = html.unescape(clean_text)
                
                return clean_text.strip()
            else:
                # Fallback to BeautifulSoup if nh3 is not available
                soup = BeautifulSoup(unescaped_text, 'html.parser')
                
                # Remove comments
                for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
                    comment.extract()
                
                # Get text content
                clean_text = soup.get_text()
                
                # Clean up whitespace
                clean_text = re.sub(r'\s+', ' ', clean_text)
                
                return clean_text.strip()
        
        except Exception as e:
            logger.warning(f"Error cleaning HTML from text: {e}")
            return text
        
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
            audio = mutagen.File(str(primary_file))  # type: ignore
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
    
    def _extract_format_info(self, audio: Any, file_path: Path) -> Dict[str, Any]:
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
        
        # Convert bitrate from bits per second to kbps
        bitrate_kbps = bitrate // 1000
        
        if bitrate_mode and bitrate_mode != 0:  # VBR
            if bitrate >= 220000:
                return "MP3 V0"
            elif bitrate >= 190000:
                return "MP3 V1"
            elif bitrate >= 170000:
                return "MP3 V2"
            else:
                return f"MP3 VBR ~{bitrate_kbps}k"
        else:  # CBR
            return f"MP3 {bitrate_kbps}k"
    
    def _validate_consistency(self, audio_files: List[Path]) -> Dict[str, Any]:
        """Validate format consistency across multiple files"""
        formats = set()
        bitrates = set()
        sample_rates = set()
        
        for file_path in audio_files[:10]:  # Sample first 10 files
            try:
                audio = mutagen.File(file_path)  # type: ignore
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
            'format': ', '.join(sorted(formats)) if formats else 'Unknown',
            'encoding': 'Unknown',
            'lossless': 'FLAC' in formats,
            'basic_detection': True
        }

class AudnexusAPI:
    """Audible metadata API integration for comprehensive book information"""
    
    def __init__(self):
        self.base_url = "https://api.audnex.us"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RED-Metadata-Engine/1.0'
        })
    
    def extract_asin(self, path_or_filename: str) -> Optional[str]:
        """Extract ASIN from filename or path pattern {ASIN.B0C8ZW5N6Y}"""
        asin_pattern = r'\{ASIN\.([A-Z0-9]{10,12})\}'
        match = re.search(asin_pattern, str(path_or_filename))
        return match.group(1) if match else None
    
    def get_book_metadata(self, asin: str) -> Optional[Dict[str, Any]]:
        """Fetch comprehensive book metadata from audnex.us API"""
        try:
            url = f"{self.base_url}/books/{asin}?update=1"
            logger.info(f"Fetching book metadata from: {url}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._normalize_audnexus_data(data)
            
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch audnexus metadata for {asin}: {e}")
            return None
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse audnexus response for {asin}: {e}")
            return None
    
    def _normalize_audnexus_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize audnexus API response to metadata format - capture ALL available data"""
        try:
            # Start with ALL raw API data to preserve everything
            metadata = dict(data)  # Copy all fields from API response
            
            # Clean the HTML summary while preserving the original
            if data.get('summary'):
                metadata['summary_cleaned'] = self._clean_html_summary(data.get('summary', ''))
                metadata['summary'] = metadata['summary_cleaned']  # Use cleaned version as primary
            
            # Extract and enhance specific fields
            
            # Extract authors with enhanced information
            authors = data.get('authors', [])
            if authors:
                metadata['authors'] = [author.get('name') for author in authors if author.get('name')]
                metadata['authors_detailed'] = authors  # Keep full author objects with ASINs
                metadata['artist'] = metadata['authors'][0] if metadata['authors'] else None
            
            # Extract narrators with enhanced information
            narrators = data.get('narrators', [])
            if narrators:
                metadata['narrators'] = [narrator.get('name') for narrator in narrators if narrator.get('name')]
                metadata['narrators_detailed'] = narrators  # Keep full narrator objects
            
            # Extract series information with all details
            series = data.get('seriesPrimary')
            if series:
                metadata['series'] = {
                    'name': series.get('name'),
                    'position': series.get('position'),
                    'asin': series.get('asin')
                }
                metadata['series_detailed'] = series  # Keep full series object
            
            # Extract and format genres with enhanced structure
            genres = data.get('genres', [])
            if genres:
                genre_names = []
                tags = []
                genre_details = []
                
                for genre in genres:
                    genre_type = genre.get('type', '').lower()
                    genre_name = genre.get('name')
                    
                    # Keep full genre object for detailed info
                    genre_details.append(genre)
                    
                    if genre_name:
                        if genre_type == 'genre':
                            genre_names.append(genre_name)
                        elif genre_type == 'tag':
                            tags.append(genre_name)
                
                if genre_names:
                    metadata['genre'] = '; '.join(genre_names)
                    metadata['genres'] = genre_names
                
                if tags:
                    metadata['tags'] = tags
                
                # Store detailed genre information with ASINs
                metadata['genres_detailed'] = genre_details
            
            # Format full album name for RED compliance
            if metadata.get('title') and metadata.get('subtitle'):
                metadata['album'] = f"{metadata['title']}: {metadata['subtitle']}"
            elif metadata.get('title'):
                metadata['album'] = metadata['title']
            
            # Extract year from release date
            if metadata.get('releaseDate'):
                try:
                    release_date = datetime.fromisoformat(metadata['releaseDate'].replace('Z', '+00:00'))
                    metadata['year'] = str(release_date.year)
                    metadata['date'] = metadata['year']
                    metadata['release_date_formatted'] = release_date.strftime('%B %d, %Y')
                except:
                    pass
            elif metadata.get('copyright'):
                metadata['year'] = str(metadata['copyright'])
                metadata['date'] = metadata['year']
            
            # Additional useful derived fields
            if metadata.get('runtimeLengthMin'):
                hours = metadata['runtimeLengthMin'] // 60
                minutes = metadata['runtimeLengthMin'] % 60
                metadata['runtime_formatted'] = f"{hours}h {minutes}m"
            
            # Store API source information
            metadata['audnexus_source'] = True
            metadata['audnexus_fetched_at'] = datetime.now().isoformat()
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error normalizing audnexus data: {e}")
            return dict(data) if data else {}  # Return raw data if normalization fails
    
    def _clean_html_summary(self, summary: str) -> str:
        """Clean HTML from summary while preserving structure using modern nh3 sanitizer"""
        if not summary:
            return ""
        
        try:
            # First, unescape any HTML entities that might be in the JSON
            unescaped_summary = html.unescape(summary)
            
            if NH3_AVAILABLE:
                # Use nh3 for modern, fast HTML sanitization
                # Allow basic formatting tags but strip everything else
                clean_text = nh3.clean(
                    unescaped_summary,
                    tags={"p", "strong", "em", "b", "i", "br", "ul", "ol", "li"},
                    attributes={}  # no attributes allowed
                )
                
                # Convert to plain text if desired, or keep basic HTML formatting
                # For RED descriptions, we want plain text
                plain_text = nh3.clean(unescaped_summary, tags=set(), attributes={})
                
                # Clean up whitespace and normalize line breaks
                plain_text = re.sub(r'\s+', ' ', plain_text)
                plain_text = re.sub(r'(\. )', r'\1\n\n', plain_text)  # Add paragraph breaks after sentences
                plain_text = re.sub(r'\n\s*\n\s*', '\n\n', plain_text)
                
                return plain_text.strip()
            
            else:
                # Fallback to BeautifulSoup if nh3 is not available
                soup = BeautifulSoup(unescaped_summary, 'html.parser')
                
                # Convert paragraphs to line breaks
                for p in soup.find_all('p'):
                    p.replace_with(p.get_text() + '\n\n')
                
                # Get clean text and normalize whitespace
                clean_text = soup.get_text()
                clean_text = re.sub(r'\n\s*\n\s*', '\n\n', clean_text)
                clean_text = re.sub(r'[ \t]+', ' ', clean_text)
                
                return clean_text.strip()
            
        except Exception as e:
            logger.warning(f"Failed to clean HTML summary: {e}")
            return summary

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
        self.audnexus_api = AudnexusAPI()
    
    def process_metadata(self, source_files: Union[Path, List[Path]], external_sources: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract and clean metadata for RED compliance"""
        console.print("[cyan]Processing metadata for RED compliance...[/cyan]")
        
        # Ensure source_files is always a list
        if isinstance(source_files, Path):
            source_files = [source_files]
        elif not isinstance(source_files, list):
            source_files = list(source_files)
        
        metadata = {}
        
        # Progress tracking for metadata processing steps
        steps = [
            "Extracting metadata from files",
            "Enriching with audnexus API data", 
            "Sanitizing HTML content",
            "Analyzing audio format",
            "Discovering album artwork",
            "Normalizing genre tags",
            "Validating RED compliance"
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Processing metadata...", total=len(steps))
            
            # 1. Extract from file tags
            progress.update(task, description=steps[0])
            metadata.update(self._extract_file_metadata(source_files))
            progress.advance(task)
            
            # 1.5. Enrich with audnexus API data if ASIN found
            progress.update(task, description=steps[1])
            metadata.update(self._enrich_with_audnexus(source_files, metadata))
            progress.advance(task)
            
            # 2. Clean HTML entities and tags
            progress.update(task, description=steps[2])
            metadata = self.html_cleaner.sanitize(metadata)
            progress.advance(task)
            
            # 3. Detect format/quality from audio analysis
            progress.update(task, description=steps[3])
            metadata.update(self.format_detector.analyze(source_files))
            progress.advance(task)
            
            # 4. Find album artwork URLs
            progress.update(task, description=steps[4])
            metadata['artwork'] = self.image_finder.discover(metadata)
            progress.advance(task)
            
            # 5. Normalize tags for RED requirements
            if metadata.get('tags'):
                progress.update(task, description=steps[5])
                metadata['tags'] = self.tag_normalizer.normalize(metadata.get('tags', []))
            else:
                progress.advance(task)
            
            # 6. Validate RED compliance
            progress.update(task, description=steps[6])
            validation_result = self._validate_red_compliance(metadata)
            metadata['validation'] = validation_result
            progress.advance(task)
        
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
            audio = mutagen.File(primary_file)  # type: ignore
            
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
                
                # Extract chapter information for audiobooks (M4B files)
                if primary_file.suffix.lower() == '.m4b':
                    chapters = self._extract_chapters(audio, primary_file)
                    if chapters:
                        metadata['chapters'] = chapters
                        metadata['track_count'] = len(chapters)
                        console.print(f"[green]📚 Extracted {len(chapters)} chapters from M4B file[/green]")
                
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
    
    def _extract_chapters(self, audio: Any, file_path: Path) -> List[Dict[str, Any]]:
        """Extract chapter information from M4B audiobook files using Mutagen"""
        chapters = []
        
        try:
            from mutagen.mp4 import MP4
            
            if not isinstance(audio, MP4):
                return chapters
            
            # Use Mutagen's built-in chapter extraction (same as test script)
            chap_list = getattr(audio, "chapters", None)
            if not chap_list:
                logger.debug("No chapters found in M4B file")
                return chapters
            
            for idx, ch in enumerate(chap_list, 1):
                # Extract timestamp
                t = None
                for attr in ("start_time", "time", "start", "timestamp"):
                    if hasattr(ch, attr):
                        t = getattr(ch, attr)
                        break
                
                # Extract title
                title = getattr(ch, "title", f"Chapter {idx}")
                
                # Convert timestamp to float seconds
                try:
                    start_seconds = float(t) if t is not None else None
                except Exception:
                    start_seconds = None
                
                # Format timestamp as HH:MM:SS.mmm
                start_formatted = None
                if start_seconds is not None:
                    ms = int(round((start_seconds - int(start_seconds)) * 1000))
                    s = int(start_seconds) % 60
                    m = (int(start_seconds) // 60) % 60
                    h = int(start_seconds) // 3600
                    start_formatted = f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
                
                chapters.append({
                    'index': idx,
                    'title': title,
                    'start_seconds': start_seconds,
                    'start': start_formatted,
                    'duration': None  # Could calculate from next chapter start
                })
            
            if chapters:
                console.print(f"[green]📚 Extracted {len(chapters)} chapters from M4B file[/green]")
            else:
                console.print(f"[yellow]📖 No chapters found in M4B file[/yellow]")
                        
        except Exception as e:
            logger.error(f"Error extracting chapters from {file_path}: {e}")
        
        return chapters
    
    def _parse_mp4_chapters(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse actual chapter information from MP4/M4B file structure"""
        chapters = []
        
        try:
            # Use ffprobe or similar to extract chapter information
            # This is a more advanced approach that can extract the actual Menu data
            
            import subprocess
            import json
            
            # Use ffprobe to extract chapter information
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_chapters',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                probe_data = json.loads(result.stdout)
                
                if 'chapters' in probe_data and probe_data['chapters']:
                    for i, chapter in enumerate(probe_data['chapters']):
                        start_time = float(chapter.get('start_time', 0))
                        end_time = float(chapter.get('end_time', 0))
                        duration = end_time - start_time
                        
                        # Try to get chapter title from tags
                        title = chapter.get('tags', {}).get('title', f'Chapter {i+1}')
                        
                        chapters.append({
                            'title': title,
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': duration,
                            'chapter_number': i + 1
                        })
                    
                    return chapters
            
            # Alternative: Try to parse using mediainfo if ffprobe fails
            try:
                cmd = ['mediainfo', '--Output=JSON', str(file_path)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    media_info = json.loads(result.stdout)
                    
                    # Look for menu/chapter information in mediainfo output
                    if 'media' in media_info and 'track' in media_info['media']:
                        for track in media_info['media']['track']:
                            if track.get('@type') == 'Menu':
                                # Parse menu entries
                                menu_entries = self._parse_menu_entries(track)
                                if menu_entries:
                                    chapters.extend(menu_entries)
                                    return chapters
            
            except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
                pass  # ffprobe/mediainfo not available or failed
                
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.debug(f"Could not parse chapters from {file_path} using external tools")
        
        return chapters
    
    def _parse_menu_entries(self, menu_track: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse menu entries from mediainfo output"""
        chapters = []
        
        try:
            # Look for menu entries in the track
            if 'extra' in menu_track:
                extra = menu_track['extra']
                
                # Try to find timestamped entries
                chapter_pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*:\s*(.+)'
                
                for key, value in extra.items():
                    if isinstance(value, str):
                        match = re.search(chapter_pattern, value)
                        if match:
                            time_str, title = match.groups()
                            
                            # Convert time string to seconds
                            time_parts = time_str.split(':')
                            if len(time_parts) == 3:
                                hours, minutes, seconds = time_parts
                                seconds = seconds.split('.')[0]  # Remove milliseconds
                                start_time = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
                                
                                chapters.append({
                                    'title': title.strip(),
                                    'start_time': float(start_time),
                                    'chapter_number': len(chapters) + 1
                                })
                
                # If we found chapters, calculate durations
                if chapters:
                    for i in range(len(chapters) - 1):
                        chapters[i]['end_time'] = chapters[i + 1]['start_time']
                        chapters[i]['duration'] = chapters[i]['end_time'] - chapters[i]['start_time']
                    
                    # Last chapter duration unknown, set to 0
                    if chapters:
                        chapters[-1]['end_time'] = chapters[-1]['start_time']
                        chapters[-1]['duration'] = 0
        
        except Exception as e:
            logger.debug(f"Error parsing menu entries: {e}")
        
        return chapters

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
        
        metadata: Dict[str, Any] = {'files': source_files, 'directory': primary_path}
        
        if match:
            metadata.update({
                'artist': match.group(1).strip(),
                'album': match.group(2).strip(),
                'year': match.group(3) if match.group(3) else None
            })
        else:
            metadata['album'] = folder_name
        
        return metadata
    
    def _enrich_with_audnexus(self, source_files: List[Path], existing_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich metadata using audnexus API if ASIN is found"""
        enriched_metadata = {}
        
        try:
            # Try to extract ASIN from file paths
            asin = None
            
            # Check all source file paths and parent directories
            search_paths = source_files + [f.parent for f in source_files]
            
            for path in search_paths:
                asin = self.audnexus_api.extract_asin(str(path))
                if asin:
                    break
            
            if not asin:
                logger.info("No ASIN found in file paths, skipping audnexus enrichment")
                return enriched_metadata
            
            logger.info(f"Found ASIN: {asin}, fetching metadata from audnexus API")
            
            # Add the ASIN to enriched metadata
            enriched_metadata['asin'] = asin
            
            # Fetch metadata from audnexus API
            api_metadata = self.audnexus_api.get_book_metadata(asin)
            
            if api_metadata:
                # Prioritize API metadata but don't overwrite existing good data
                for key, value in api_metadata.items():
                    if value is not None and value != "":
                        # Only use API data if we don't have this field or it's better
                        if (key not in existing_metadata or 
                            not existing_metadata.get(key) or 
                            key in ['summary', 'description', 'image', 'series', 'narrators']):
                            enriched_metadata[key] = value
                
                # Special handling for artwork from API
                if api_metadata.get('image'):
                    artwork_from_api = AlbumArtwork(
                        url=api_metadata['image'],
                        source='audnexus_api',
                        confidence=0.9  # High confidence for official API source
                    )
                    
                    # Add to existing artwork list or create new one
                    existing_artwork = existing_metadata.get('artwork', [])
                    if isinstance(existing_artwork, list):
                        enriched_metadata['artwork'] = [artwork_from_api] + existing_artwork
                    else:
                        enriched_metadata['artwork'] = [artwork_from_api]
                
                logger.info(f"Successfully enriched metadata with audnexus API data for ASIN: {asin}")
                
                # Build enhanced description for RED upload
                enhanced_description = self._build_enhanced_description(api_metadata)
                if enhanced_description:
                    enriched_metadata['red_description'] = enhanced_description
            
            else:
                logger.warning(f"No metadata returned from audnexus API for ASIN: {asin}")
        
        except Exception as e:
            logger.error(f"Error during audnexus enrichment: {e}")
        
        return enriched_metadata
    
    def _build_enhanced_description(self, api_metadata: Dict[str, Any]) -> str:
        """Build an enhanced description for RED upload using audnexus data"""
        description_parts = []
        
        # Add title and subtitle
        title_parts = []
        if api_metadata.get('title'):
            title_parts.append(api_metadata['title'])
        if api_metadata.get('subtitle'):
            title_parts.append(api_metadata['subtitle'])
        
        if title_parts:
            description_parts.append("**" + " - ".join(title_parts) + "**")
        
        # Add the full summary (detailed description) if available - this is the main content
        if api_metadata.get('summary'):
            description_parts.append(api_metadata['summary'])
        elif api_metadata.get('description'):
            # Fallback to shorter description if full summary not available
            description_parts.append(api_metadata['description'])
        
        # Add metadata information
        metadata_info = []
        
        # Authors
        if api_metadata.get('authors'):
            author_names = []
            for author in api_metadata['authors']:
                if isinstance(author, dict) and author.get('name'):
                    author_names.append(author['name'])
                elif isinstance(author, str):
                    author_names.append(author)
            
            if author_names:
                metadata_info.append(f"**Author(s):** {', '.join(author_names)}")
        
        # Series information
        if api_metadata.get('series'):
            series = api_metadata['series']
            series_text = f"**Series:** {series.get('name')}"
            if series.get('position'):
                series_text += f" - Book {series.get('position')}"
            metadata_info.append(series_text)
        
        # Publisher and release info
        if api_metadata.get('publisherName'):
            metadata_info.append(f"**Publisher:** {api_metadata['publisherName']}")
        
        if api_metadata.get('releaseDate'):
            try:
                release_date = datetime.fromisoformat(api_metadata['releaseDate'].replace('Z', '+00:00'))
                metadata_info.append(f"**Release Date:** {release_date.strftime('%B %d, %Y')}")
            except:
                pass
        
        # Runtime
        if api_metadata.get('runtimeLengthMin'):
            hours = api_metadata['runtimeLengthMin'] // 60
            minutes = api_metadata['runtimeLengthMin'] % 60
            metadata_info.append(f"**Runtime:** {hours}h {minutes}m")
        
        # Narrators
        if api_metadata.get('narrators'):
            narrator_names = []
            for narrator in api_metadata['narrators']:
                if isinstance(narrator, dict) and narrator.get('name'):
                    narrator_names.append(narrator['name'])
                elif isinstance(narrator, str):
                    narrator_names.append(narrator)
            
            if narrator_names:
                metadata_info.append(f"**Narrated by:** {', '.join(narrator_names)}")
        
        # Rating
        if api_metadata.get('rating'):
            metadata_info.append(f"**Rating:** {api_metadata['rating']}/5.0")
        
        # ISBN
        if api_metadata.get('isbn'):
            metadata_info.append(f"**ISBN:** {api_metadata['isbn']}")
        
        # Add metadata section if we have info
        if metadata_info:
            description_parts.append("\n---\n**Book Information:**\n" + "\n".join(metadata_info))
        
        return "\n\n".join(description_parts)

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
        validation: Dict[str, Any] = {
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
