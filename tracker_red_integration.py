#!/usr/bin/env python3
"""
Integration layer between torrent creator and RED uploader
Ensures proper compliance with private tracker requirements
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console

console = Console()

class TrackerIntegration:
    """Handles integration between torrent creation and tracker upload"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tracker_configs = self._load_tracker_configs()
    
    def _load_tracker_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load tracker-specific configurations"""
        configs = {}
        
        # RED configuration
        configs['red'] = {
            'name': 'Redacted',
            'announce_url': self.config.get('red_announce_url', 'https://flacsfor.me/announce'),
            'source_tag': 'RED',
            'requires_private': True,
            'supported_formats': ['v1'],  # RED doesn't support v2 yet
            'api_endpoint': 'https://redacted.ch',
            'upload_endpoint': 'https://redacted.ch/ajax.php?action=upload'
        }
        
        # OPS configuration
        configs['ops'] = {
            'name': 'Orpheus',
            'announce_url': self.config.get('ops_announce_url', ''),
            'source_tag': 'OPS',
            'requires_private': True,
            'supported_formats': ['v1', 'hybrid'],
            'api_endpoint': 'https://orpheus.network'
        }
        
        return configs
    
    def prepare_upload(self, source_path: Path, tracker: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare everything needed for upload to a tracker"""
        
        if tracker not in self.tracker_configs:
            raise ValueError(f"Unknown tracker: {tracker}")
        
        tracker_config = self.tracker_configs[tracker]
        result = {
            'tracker': tracker,
            'tracker_config': tracker_config,
            'source_path': source_path,
            'metadata': metadata,
            'torrent_path': None,
            'success': False,
            'errors': []
        }
        
        console.print(f"\n[cyan]Preparing upload for {tracker_config['name']}[/cyan]")
        
        # Validate requirements
        if not self._validate_tracker_requirements(source_path, tracker_config, metadata):
            result['errors'].append("Failed tracker requirement validation")
            return result
        
        # Create the torrent with proper settings
        from torrent_creator import TorrentCreator
        
        creator = TorrentCreator(config=self.config)
        
        # Configure for this specific tracker
        creator.trackers = [tracker_config['announce_url']]
        creator.private = True
        creator.source = tracker_config['source_tag']
        creator.torrent_format = 'v1'  # Use v1 for maximum compatibility
        
        # Set category and tags based on metadata
        creator.category = metadata.get('release_type', '')
        creator.tags = self._generate_tags(metadata)
        
        # Create the torrent
        torrent_path = creator.create_torrent_for_upload(source_path, tracker_config)
        
        if torrent_path and torrent_path.exists():
            result['torrent_path'] = torrent_path
            result['success'] = True
            console.print(f"[green]✓ Torrent created: {torrent_path}[/green]")
            
            # Add to qBittorrent immediately
            if self.config.get('auto_add_to_client', True):
                success = creator._add_torrent_to_client(torrent_path, source_path)
                if success:
                    console.print("[green]✓ Torrent added to qBittorrent[/green]")
                else:
                    console.print("[yellow]⚠️ Failed to add to qBittorrent - manual add required[/yellow]")
                    result['errors'].append("Failed to add to qBittorrent")
        else:
            result['errors'].append("Failed to create torrent file")
            console.print("[red]✗ Failed to create torrent[/red]")
        
        return result
    
    def _validate_tracker_requirements(self, source_path: Path, tracker_config: Dict, metadata: Dict) -> bool:
        """Validate that all tracker requirements are met"""
        console.print("[cyan]Validating tracker requirements...[/cyan]")
        
        # Check announce URL
        if not tracker_config.get('announce_url'):
            console.print("[red]✗ Missing announce URL[/red]")
            return False
        
        # Check source path exists
        if not source_path.exists():
            console.print(f"[red]✗ Source path does not exist: {source_path}[/red]")
            return False
        
        # For music trackers, validate audio files
        if tracker_config['name'] in ['Redacted', 'Orpheus']:
            if not self._validate_audio_files(source_path):
                return False
        
        # Check required metadata fields
        required_fields = ['artists', 'title', 'year']
        for field in required_fields:
            if not metadata.get(field):
                console.print(f"[yellow]⚠️ Missing required field: {field}[/yellow]")
        
        console.print("[green]✓ Tracker requirements validated[/green]")
        return True
    
    def _validate_audio_files(self, source_path: Path) -> bool:
        """Validate audio files for music trackers"""
        audio_extensions = {'.flac', '.mp3', '.m4a', '.opus', '.ogg'}
        
        if source_path.is_file():
            if source_path.suffix.lower() not in audio_extensions:
                console.print(f"[red]✗ Not a valid audio file: {source_path.suffix}[/red]")
                return False
        else:
            # Check directory contains audio files
            audio_files = []
            for ext in audio_extensions:
                audio_files.extend(source_path.glob(f"**/*{ext}"))
            
            if not audio_files:
                console.print("[red]✗ No audio files found in directory[/red]")
                return False
            
            console.print(f"[green]✓ Found {len(audio_files)} audio files[/green]")
        
        return True
    
    def _generate_tags(self, metadata: Dict) -> list:
        """Generate tags based on metadata"""
        tags = []
        
        # Add format tags
        if metadata.get('format'):
            tags.append(metadata['format'].upper())
        
        # Add encoding tags
        if metadata.get('encoding'):
            tags.append(metadata['encoding'])
        
        # Add release type
        if metadata.get('release_type'):
            tags.append(metadata['release_type'])
        
        # Add year decade
        year = metadata.get('year')
        if year:
            try:
                decade = (int(year) // 10) * 10
                tags.append(f"{decade}s")
            except:
                pass
        
        return tags

def integrate_upload_workflow(source_path: Path, tracker: str, config: Dict[str, Any]) -> bool:
    """Main integration function for upload workflow with enhanced metadata processing"""
    
    console.print("\n[bold cyan]═══ Enhanced Upload Workflow with Metadata Processing ═══[/bold cyan]\n")
    
    # Initialize integration
    integration = TrackerIntegration(config)
    
    # Initialize the RED uploader for metadata processing
    from feature_red_uploader import REDUploader
    
    # Check API key
    api_key = config.get('red_api_key')
    if not api_key:
        console.print("[red]✗ RED API key not configured[/red]")
        console.print("[dim]Use 'python run.py config' to set up API credentials[/dim]")
        return False
    
    uploader = REDUploader(api_key=api_key)
    
    # Test connection first
    console.print("[cyan]Testing RED API connection...[/cyan]")
    if not uploader.test_connection():
        console.print("[red]✗ Failed to connect to RED API[/red]")
        console.print("[dim]Check your API key and network connection[/dim]")
        return False
    
    # Extract comprehensive metadata using the metadata engine
    console.print(f"[cyan]Processing metadata for: {source_path.name}[/cyan]")
    try:
        metadata = uploader.extract_and_prepare_metadata(source_path)
        
        # Display metadata summary
        validation = metadata.get('validation', {})
        console.print(f"\n[cyan]Metadata Summary:[/cyan]")
        
        # Basic info
        artists = metadata.get('artists', [])
        if artists:
            artist_names = [artist['name'] for artist in artists]
            console.print(f"  Artist(s): {', '.join(artist_names)}")
        
        if metadata.get('groupname'):
            console.print(f"  Album: {metadata['groupname']}")
        
        if metadata.get('year'):
            console.print(f"  Year: {metadata['year']}")
        
        if metadata.get('format') and metadata.get('encoding'):
            console.print(f"  Format: {metadata['format']} ({metadata['encoding']})")
        
        # Validation status
        if validation.get('ready_for_upload'):
            console.print(f"[green]✓ Metadata validation passed (Score: {validation.get('score', 0)}/100)[/green]")
        else:
            console.print(f"[yellow]⚠️ Metadata validation issues (Score: {validation.get('score', 0)}/100)[/yellow]")
            
            if validation.get('errors'):
                console.print("[red]Errors:[/red]")
                for error in validation['errors']:
                    console.print(f"  • {error}")
            
            if validation.get('warnings'):
                console.print("[yellow]Warnings:[/yellow]")
                for warning in validation['warnings']:
                    console.print(f"  • {warning}")
            
            # Ask user if they want to continue despite validation issues
            from rich.prompt import Confirm
            if not Confirm.ask("\nContinue with upload preparation despite validation issues?", default=False):
                return False
        
    except Exception as e:
        console.print(f"[red]✗ Error processing metadata: {e}[/red]")
        return False
    
    # Prepare the upload (creates torrent with proper settings)
    console.print(f"\n[cyan]Preparing torrent for {tracker.upper()}...[/cyan]")
    result = integration.prepare_upload(source_path, tracker, metadata)
    
    if not result['success']:
        console.print(f"[red]✗ Upload preparation failed:[/red]")
        for error in result.get('errors', []):
            console.print(f"  • {error}")
        return False
    
    # Show what's ready for upload
    if result['torrent_path']:
        console.print(f"\n[green]✓ Upload preparation complete![/green]")
        console.print(f"  Torrent: {result['torrent_path']}")
        console.print(f"  Source: {source_path}")
        console.print(f"  Tracker: {result['tracker_config']['name']}")
        
        # Offer to perform actual upload
        from rich.prompt import Confirm
        if Confirm.ask(f"\nPerform actual upload to {result['tracker_config']['name']}?", default=False):
            try:
                upload_result = uploader.upload_torrent(
                    result['torrent_path'], 
                    metadata, 
                    dry_run=False
                )
                
                if upload_result.get('success'):
                    torrent_id = upload_result.get('torrent_id')
                    console.print(f"[green]🎉 Upload successful! Torrent ID: {torrent_id}[/green]")
                    
                    # Show direct link
                    if torrent_id:
                        console.print(f"[cyan]View at: https://redacted.ch/torrents.php?torrentid={torrent_id}[/cyan]")
                    
                    return True
                else:
                    error = upload_result.get('error', 'Unknown error')
                    console.print(f"[red]✗ Upload failed: {error}[/red]")
                    return False
                    
            except Exception as e:
                console.print(f"[red]✗ Upload error: {e}[/red]")
                return False
        else:
            console.print("[yellow]Upload skipped by user[/yellow]")
            console.print("[dim]Torrent file is ready for manual upload[/dim]")
            return True
    
    return False
