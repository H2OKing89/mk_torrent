#!/usr/bin/env python3
"""
RED (Redacted) Tracker Uploader
Handles API communication and metadata preparation for RED uploads
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .metadata_engine import MetadataEngine, process_album_metadata

console = Console()
logger = logging.getLogger(__name__)

@dataclass
class REDReleaseType:
    """RED release type mappings"""
    ALBUM = 1
    SOUNDTRACK = 3
    EP = 5
    ANTHOLOGY = 6
    COMPILATION = 7
    SINGLE = 9
    LIVE_ALBUM = 11
    REMIX = 13
    BOOTLEG = 14
    INTERVIEW = 15
    MIXTAPE = 16
    DEMO = 17
    CONCERT_RECORDING = 18
    DJ_MIX = 19
    UNKNOWN = 21

@dataclass
class REDFormat:
    """RED format and encoding mappings"""
    FLAC_24BIT = "FLAC 24bit Lossless"
    FLAC = "FLAC Lossless"
    MP3_320 = "MP3 320"
    MP3_V0 = "MP3 V0 (VBR)"
    MP3_V1 = "MP3 V1 (VBR)" 
    MP3_V2 = "MP3 V2 (VBR)"
    MP3_256 = "MP3 256"
    MP3_192 = "MP3 192"
    AAC_320 = "AAC 320"
    AAC_256 = "AAC 256"
    AAC_VBR = "AAC VBR"

class REDAPIError(Exception):
    """RED API specific errors"""
    pass

class REDUploader:
    """Handles uploads to RED tracker via their API"""
    
    def __init__(self, api_key: str, base_url: str = "https://redacted.ch"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'REDUploader/1.0 (RED Torrent Creator)',
            'Authorization': f'Bearer {api_key}'
        })
        
        self.metadata_engine = MetadataEngine()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests
    
    def _rate_limit(self):
        """Enforce rate limiting between API requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None, 
                     files: Optional[Dict] = None, timeout: int = 30) -> Dict[str, Any]:
        """Make an authenticated request to RED API"""
        self._rate_limit()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=data, timeout=timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, data=data, files=files, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            result = response.json()
            
            # Check for API errors
            if result.get('status') == 'failure':
                error_msg = result.get('error', 'Unknown API error')
                raise REDAPIError(f"RED API error: {error_msg}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            raise REDAPIError(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise REDAPIError(f"Invalid API response: {e}")
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            result = self._make_request("ajax.php?action=index")
            if result.get('status') == 'success':
                console.print("[green]✓ RED API connection successful[/green]")
                return True
            else:
                console.print("[red]✗ RED API connection failed[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ RED API connection failed: {e}[/red]")
            return False
    
    def search_existing_torrent(self, artist: str, album: str) -> List[Dict[str, Any]]:
        """Search for existing torrents on RED"""
        try:
            search_params = {
                'action': 'browse',
                'artistname': artist,
                'groupname': album,
                'searchstr': ''
            }
            
            result = self._make_request("ajax.php", "GET", search_params)
            
            if result.get('status') == 'success' and 'response' in result:
                return result['response'].get('results', [])
            
            return []
            
        except Exception as e:
            logger.warning(f"Error searching for existing torrents: {e}")
            return []
    
    def extract_and_prepare_metadata(self, source_path: Union[str, Path]) -> Dict[str, Any]:
        """Extract and prepare metadata for RED upload"""
        source_path = Path(source_path)
        
        console.print(f"[cyan]Preparing metadata for: {source_path.name}[/cyan]")
        
        # Use metadata engine to extract and clean metadata
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing metadata...", total=None)
            
            if source_path.is_file():
                source_files = [source_path]
            else:
                source_files = [source_path]
            
            metadata = self.metadata_engine.process_metadata(source_files)
            progress.remove_task(task)
        
        # Convert to RED-specific format
        red_metadata = self._convert_to_red_format(metadata)
        
        # Validate for RED requirements
        validation = self._validate_for_red(red_metadata)
        red_metadata['validation'] = validation
        
        return red_metadata
    
    def _convert_to_red_format(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Convert metadata to RED-specific format"""
        red_data = {
            'artists': [],
            'groupname': metadata.get('album', ''),
            'year': metadata.get('year', ''),
            'releasetype': self._detect_release_type(metadata),
            'format': self._map_audio_format(metadata),
            'encoding': self._map_encoding(metadata),
            'media': 'CD',  # Default, could be WEB, Vinyl, etc.
            'genre_tags': metadata.get('tags', []),
            'image': '',  # Album artwork URL
            'album_desc': '',  # Album description
            'release_desc': '',  # Release description
            'tags': self._generate_red_tags(metadata)
        }
        
        # Process artists
        if metadata.get('artist'):
            if isinstance(metadata['artist'], str):
                red_data['artists'] = [{'name': metadata['artist']}]
            elif isinstance(metadata['artist'], list):
                red_data['artists'] = [{'name': artist} for artist in metadata['artist']]
        
        # Handle album artwork
        artwork = metadata.get('artwork', [])
        if artwork:
            # Use the highest confidence artwork
            best_artwork = max(artwork, key=lambda x: x.confidence)
            red_data['image'] = best_artwork.url
        
        # Generate descriptions
        red_data['album_desc'] = self._generate_album_description(metadata)
        red_data['release_desc'] = self._generate_release_description(metadata)
        
        return red_data
    
    def _detect_release_type(self, metadata: Dict[str, Any]) -> int:
        """Detect RED release type from metadata"""
        # Try to detect from directory name or metadata
        title = metadata.get('album', '').lower()
        
        # Common patterns
        if any(word in title for word in ['soundtrack', 'ost', 'score']):
            return REDReleaseType.SOUNDTRACK
        elif any(word in title for word in ['ep', 'extended play']):
            return REDReleaseType.EP
        elif any(word in title for word in ['single']):
            return REDReleaseType.SINGLE
        elif any(word in title for word in ['compilation', 'collection', 'best of']):
            return REDReleaseType.COMPILATION
        elif any(word in title for word in ['live', 'concert', 'tour']):
            return REDReleaseType.LIVE_ALBUM
        elif any(word in title for word in ['remix', 'remixes']):
            return REDReleaseType.REMIX
        elif any(word in title for word in ['mixtape', 'mix tape']):
            return REDReleaseType.MIXTAPE
        elif any(word in title for word in ['demo', 'demos']):
            return REDReleaseType.DEMO
        else:
            return REDReleaseType.ALBUM  # Default to album
    
    def _map_audio_format(self, metadata: Dict[str, Any]) -> str:
        """Map audio format to RED format"""
        format_type = metadata.get('format', '').upper()
        
        if format_type == 'FLAC':
            bit_depth = metadata.get('bit_depth')
            if bit_depth and bit_depth > 16:
                return "FLAC"  # RED uses same format string for both
            return "FLAC"
        elif format_type == 'MP3':
            return "MP3"
        elif format_type in ['AAC', 'M4A']:
            return "AAC"
        else:
            return format_type or "Unknown"
    
    def _map_encoding(self, metadata: Dict[str, Any]) -> str:
        """Map encoding quality to RED encoding"""
        encoding = metadata.get('encoding', '')
        format_type = metadata.get('format', '').upper()
        
        if format_type == 'FLAC':
            bit_depth = metadata.get('bit_depth', 16)
            if bit_depth > 16:
                return "24bit Lossless"
            return "Lossless"
        elif format_type == 'MP3':
            if 'V0' in encoding.upper():
                return "V0 (VBR)"
            elif 'V1' in encoding.upper():
                return "V1 (VBR)"
            elif 'V2' in encoding.upper():
                return "V2 (VBR)"
            elif '320' in encoding:
                return "320"
            elif '256' in encoding:
                return "256"
            elif '192' in encoding:
                return "192"
            else:
                return "320"  # Default assumption
        elif format_type == 'AAC':
            if '320' in encoding:
                return "320"
            elif '256' in encoding:
                return "256"
            else:
                return "VBR"
        
        return encoding or "Unknown"
    
    def _generate_red_tags(self, metadata: Dict[str, Any]) -> List[str]:
        """Generate appropriate tags for RED"""
        tags = []
        
        # Add format tags
        format_type = metadata.get('format', '').lower()
        if format_type:
            tags.append(format_type)
        
        # Add encoding quality
        encoding = metadata.get('encoding', '')
        if 'lossless' in encoding.lower():
            tags.append('lossless')
        elif any(quality in encoding.lower() for quality in ['v0', 'v1', 'v2', '320', '256']):
            tags.append('lossy')
        
        # Add year decade
        year = metadata.get('year')
        if year:
            try:
                decade = (int(year) // 10) * 10
                tags.append(f"{decade}s")
            except ValueError:
                pass
        
        # Add genre tags (normalized)
        genre_tags = metadata.get('tags', [])
        tags.extend([tag.lower() for tag in genre_tags[:3]])  # Limit to 3 main genres
        
        return tags
    
    def _generate_album_description(self, metadata: Dict[str, Any]) -> str:
        """Generate album description for RED"""
        description_parts = []
        
        # Basic info
        artist = metadata.get('artist', 'Unknown Artist')
        album = metadata.get('album', 'Unknown Album')
        year = metadata.get('year', 'Unknown Year')
        
        description_parts.append(f"Album: {album}")
        description_parts.append(f"Artist: {artist}")
        description_parts.append(f"Year: {year}")
        
        # Technical info
        format_info = metadata.get('format', '')
        encoding = metadata.get('encoding', '')
        if format_info and encoding:
            description_parts.append(f"Format: {format_info} ({encoding})")
        
        # File count and size info
        files = metadata.get('files', [])
        if files:
            description_parts.append(f"Files: {len(files)} tracks")
        
        return "\\n".join(description_parts)
    
    def _generate_release_description(self, metadata: Dict[str, Any]) -> str:
        """Generate release-specific description"""
        description_parts = []
        
        # Quality information
        format_info = metadata.get('format', '')
        encoding = metadata.get('encoding', '')
        
        if format_info == 'FLAC':
            bit_depth = metadata.get('bit_depth', 16)
            sample_rate = metadata.get('sample_rate', 44100)
            description_parts.append(f"Ripped from CD to FLAC {bit_depth}-bit/{sample_rate}Hz")
        elif format_info == 'MP3':
            description_parts.append(f"Encoded to {encoding}")
        
        # Consistency check
        consistency = metadata.get('format_consistent', True)
        if not consistency:
            description_parts.append("Note: Mixed format release")
        
        return " ".join(description_parts) if description_parts else ""
    
    def _validate_for_red(self, red_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata for RED upload requirements"""
        errors = []
        warnings = []
        
        # Required fields for RED upload
        required_fields = {
            'artists': 'Artist information',
            'groupname': 'Album title',
            'year': 'Release year',
            'format': 'Audio format',
            'encoding': 'Audio encoding'
        }
        
        for field, description in required_fields.items():
            if not red_metadata.get(field):
                errors.append(f"Missing {description}")
        
        # Validate year
        year = red_metadata.get('year')
        if year:
            try:
                year_int = int(year)
                if year_int < 1900 or year_int > datetime.now().year + 1:
                    warnings.append(f"Unusual release year: {year}")
            except ValueError:
                errors.append(f"Invalid year format: {year}")
        
        # Validate artists
        artists = red_metadata.get('artists', [])
        if not artists or not any(artist.get('name') for artist in artists):
            errors.append("At least one artist name is required")
        
        # Check for image
        if not red_metadata.get('image'):
            warnings.append("No album artwork found")
        
        # Validate format/encoding combination
        format_type = red_metadata.get('format', '')
        encoding = red_metadata.get('encoding', '')
        if format_type == 'FLAC' and 'lossless' not in encoding.lower():
            warnings.append("FLAC format should have lossless encoding")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'ready_for_upload': len(errors) == 0,
            'score': max(0, 100 - len(errors) * 25 - len(warnings) * 5)
        }
    
    def upload_torrent(self, torrent_path: Path, metadata: Dict[str, Any], 
                      dry_run: bool = True) -> Dict[str, Any]:
        """Upload torrent to RED (dry run by default)"""
        if dry_run:
            console.print("[yellow]DRY RUN: Would upload torrent to RED[/yellow]")
            return {
                'success': True,
                'dry_run': True,
                'message': 'Dry run completed successfully',
                'torrent_id': None,
                'metadata': metadata
            }
        
        # Validate torrent file exists
        if not torrent_path.exists():
            raise REDAPIError(f"Torrent file not found: {torrent_path}")
        
        # Prepare upload data
        upload_data = {
            'submit': 'true',
            'type': '0',  # Music
            'artists[]': [artist['name'] for artist in metadata.get('artists', [])],
            'groupname': metadata.get('groupname', ''),
            'year': metadata.get('year', ''),
            'releasetype': metadata.get('releasetype', REDReleaseType.ALBUM),
            'format': metadata.get('format', ''),
            'bitrate': metadata.get('encoding', ''),
            'media': metadata.get('media', 'CD'),
            'genre_tags': metadata.get('genre_tags', []),
            'tags': ','.join(metadata.get('tags', [])),
            'image': metadata.get('image', ''),
            'album_desc': metadata.get('album_desc', ''),
            'release_desc': metadata.get('release_desc', '')
        }
        
        # Prepare torrent file
        files = {
            'file_input': ('torrent.torrent', open(torrent_path, 'rb'), 'application/x-bittorrent')
        }
        
        try:
            console.print("[cyan]Uploading to RED...[/cyan]")
            result = self._make_request("ajax.php?action=upload", "POST", 
                                      data=upload_data, files=files, timeout=60)
            
            if result.get('status') == 'success':
                torrent_id = result.get('response', {}).get('torrentid')
                console.print(f"[green]✓ Upload successful! Torrent ID: {torrent_id}[/green]")
                return {
                    'success': True,
                    'dry_run': False,
                    'torrent_id': torrent_id,
                    'message': 'Upload completed successfully',
                    'metadata': metadata
                }
            else:
                error_msg = result.get('error', 'Unknown upload error')
                raise REDAPIError(f"Upload failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {
                'success': False,
                'dry_run': False,
                'error': str(e),
                'metadata': metadata
            }
        finally:
            # Close file handle
            if 'file_input' in files:
                files['file_input'][1].close()

# Convenience function for external use
def upload_album_to_red(source_path: Union[str, Path], torrent_path: Union[str, Path], 
                       api_key: str, dry_run: bool = True) -> Dict[str, Any]:
    """Upload an album to RED with automatic metadata processing"""
    uploader = REDUploader(api_key)
    
    # Test connection first
    if not uploader.test_connection():
        return {'success': False, 'error': 'Failed to connect to RED API'}
    
    # Extract and prepare metadata
    metadata = uploader.extract_and_prepare_metadata(source_path)
    
    # Validate metadata
    validation = metadata.get('validation', {})
    if not validation.get('ready_for_upload', False):
        return {
            'success': False, 
            'error': 'Metadata validation failed',
            'validation': validation
        }
    
    # Upload torrent
    return uploader.upload_torrent(Path(torrent_path), metadata, dry_run=dry_run)

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python red_uploader.py <source_path> <torrent_path> <api_key> [dry_run]")
        sys.exit(1)
    
    source_path = sys.argv[1]
    torrent_path = sys.argv[2]
    api_key = sys.argv[3]
    dry_run = len(sys.argv) < 5 or sys.argv[4].lower() != 'false'
    
    result = upload_album_to_red(source_path, torrent_path, api_key, dry_run)
    print(json.dumps(result, indent=2, default=str))
