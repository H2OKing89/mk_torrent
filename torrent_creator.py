#!/usr/bin/env python3
"""
Interactive Torrent Creator for qBittorrent
Uses qBittorrent Web API v2.10.4+ for native torrent creation
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum

import qbittorrentapi
from qbittorrentapi.torrentcreator import TaskStatus
from qbittorrentapi import exceptions as qba_exc

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich import print as rprint
from prompt_toolkit.shortcuts import checkboxlist_dialog, radiolist_dialog
from tqdm import tqdm

console = Console()

class QBitMode(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"

class TorrentCreator:
    def __init__(self, mode: QBitMode = QBitMode.LOCAL, container_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.mode = mode
        self.container_name = container_name
        self.config = config or {}
        self.trackers = []
        self.web_seeds = []  # Add this line
        self.url_seeds = []  # Add this line (alias for web_seeds for API compatibility)
        self.piece_size = None  # Let qBittorrent auto-select
        self.private = self.config.get("default_private", True)  # Changed default to True for private trackers
        self.comment = ""
        self.category = self.config.get("default_category", "")
        self.tags = self.config.get("default_tags", [])
        self.start_seeding = self.config.get("auto_start_seeding", True)
        self.auto_management = self.config.get("auto_torrent_management", True)  # New setting
        self.torrent_format = self.config.get("default_torrent_format", "v1")  # Default to v1 for compatibility
        self.source = self.config.get("default_source", "")  # New: source field for cross-seeding
        self.optimize_alignment = self.config.get("optimize_alignment", True)  # New: optimize alignment
        self.padded_file_size_limit = self.config.get("padded_file_size_limit", -1)  # New: padding control
        
        # Initialize qBittorrent API client
        self.client = None
        if config:
            try:
                self.client = qbittorrentapi.Client(
                    host=f"{config.get('qbit_host', 'localhost')}:{config.get('qbit_port', 8080)}",
                    username=config.get("qbit_username", "admin"),
                    password=config.get("qbit_password", "adminadmin"),
                    VERIFY_WEBUI_CERTIFICATE=False if config.get("qbit_https", False) else True
                )
                # Test connection
                self.client.auth_log_in()
                console.print("[green]✓ Connected to qBittorrent API[/green]")
                
                # Check API version for torrent creator support
                api_version = self.client.app.web_api_version
                if api_version and api_version >= "2.10.4":
                    console.print(f"[green]✓ Torrent Creator API supported (v{api_version})[/green]")
                else:
                    console.print(f"[yellow]⚠️ API version {api_version} may not support torrent creation[/yellow]")
                    
            except Exception as e:
                console.print(f"[yellow]Warning: Could not connect to qBittorrent API: {e}[/yellow]")
                self.client = None
    
    def load_default_trackers(self):
        """Load default trackers from config or prompt user"""
        config_file = Path.home() / ".config" / "torrent_creator" / "trackers.txt"
        if config_file.exists():
            with open(config_file) as f:
                self.trackers = [line.strip() for line in f if line.strip()]
        else:
            console.print("[yellow]No default trackers found. Add them manually.[/yellow]")
    
    def create_torrent_via_api(self, source_path: Path, output_path: Path) -> bool:
        """Create torrent using qBittorrent Web API"""
        if not self.client:
            console.print("[red]✗ qBittorrent client not initialized[/red]")
            return False
        
        try:
            # Fix: Ensure format is properly typed
            torrent_format: Literal['v1', 'v2', 'hybrid'] = 'v1'  # Default
            if self.torrent_format in ['v1', 'v2', 'hybrid']:
                torrent_format = self.torrent_format  # type: ignore
            
            # Fix: Use url_seeds instead of web_seeds for consistency
            # Create the torrent via API
            task = self.client.torrentcreator.add_task(
                source_path=str(source_path),
                format=torrent_format,
                start_seeding=self.start_seeding,
                is_private=self.private,
                comment=self.comment,
                trackers=self.trackers,
                url_seeds=self.url_seeds,  # This was already correct
                source=self.source
            )
            
            console.print(f"[cyan]Task created with ID: {task.get('taskID')}[/cyan]")
            
            # Poll for completion
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task_progress = progress.add_task("Creating torrent...", total=None)
                
                while True:
                    status = task.status()
                    state = TaskStatus(status.status)
                    
                    if state == TaskStatus.RUNNING:
                        progress.update(task_progress, description="Hashing files...")
                    elif state == TaskStatus.FINISHED:
                        progress.update(task_progress, description="Torrent created!", completed=100)
                        break
                    elif state == TaskStatus.FAILED:
                        progress.update(task_progress, description="Failed!")
                        console.print(f"[red]Torrent creation failed: {getattr(status, 'message', 'Unknown error')}[/red]")
                        task.delete()
                        return False
                    
                    time.sleep(0.5)
            
            # Download the torrent file if not saved on server
            if self.mode == QBitMode.LOCAL and output_path:
                torrent_bytes = task.torrent_file()
                output_path.write_bytes(torrent_bytes)
                console.print(f"[green]✓ Torrent saved to: {output_path}[/green]")
            
            # If start_seeding is True, we need to find and configure the torrent
            if self.start_seeding:
                # Wait a moment for qBittorrent to add the torrent
                time.sleep(1)
                
                # Fix: Use source_path instead of undefined api_source_path
                torrent_hash = self._find_torrent_by_path(str(source_path))
                if torrent_hash:
                    self._configure_torrent(torrent_hash)
                    console.print(f"[green]✓ Torrent configured with category and tags[/green]")
                else:
                    console.print(f"[yellow]⚠️ Could not find torrent to apply settings[/yellow]")
            
            # Clean up the task
            task.delete()
            
            return True
            
        except qba_exc.Conflict409Error as e:
            console.print(f"[red]Too many torrent creation tasks queued: {e}[/red]")
            return False
        except qba_exc.NotFound404Error as e:
            console.print(f"[red]Task not found: {e}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Error creating torrent: {e}[/red]")
            return False
    
    def _find_torrent_by_path(self, source_path: str) -> Optional[str]:
        """Find a torrent by its content path"""
        try:
            # Fix: Check if client exists
            if not self.client:
                return None
                
            # Get all torrents
            torrents = self.client.torrents_info()
            
            # Normalize paths for comparison
            source_normalized = Path(source_path).resolve()
            
            for torrent in torrents:
                # Check if the content path matches
                torrent_path = Path(torrent.content_path)
                if torrent_path == source_normalized:
                    return torrent.hash
                
                # Also check save_path + name for single file torrents
                save_path = Path(torrent.save_path) / torrent.name
                if save_path == source_normalized:
                    return torrent.hash
            
            return None
        except Exception as e:
            console.print(f"[yellow]Error finding torrent: {e}[/yellow]")
            return None
    
    def _configure_torrent(self, torrent_hash: str):
        """Configure a torrent with category, tags, and management settings"""
        try:
            # Fix: Check client is not None before accessing methods
            if self.client is not None:
                torrents = self.client.torrents_info(torrent_hashes=torrent_hash)
            
            # Apply category if set
            if self.category and self.client is not None:
                self.client.torrents_set_category(
                    torrent_hashes=torrent_hash,
                    category=self.category
                )
            
            # Apply tags if set
            if self.tags and self.client is not None:
                self.client.torrents_add_tags(
                    torrent_hashes=torrent_hash,
                    tags=','.join(self.tags) if isinstance(self.tags, list) else self.tags
                )
            
            # Set auto management
            if self.client is not None:
                self.client.torrents_set_auto_management(
                    torrent_hashes=torrent_hash,
                    enable=self.auto_management
                )
            
            # Verify the settings were applied
            self._verify_torrent_settings(torrent_hash)
            
        except Exception as e:
            console.print(f"[yellow]Error configuring torrent: {e}[/yellow]")
    
    def _verify_torrent_settings(self, torrent_hash: str):
        """Verify that torrent settings were properly applied"""
        try:
            # Fix: Check if client exists
            if not self.client:
                return
                
            # Get the torrent info
            torrents = self.client.torrents_info(torrent_hashes=torrent_hash)
            if torrents:
                torrent = torrents[0]
                
                # Verify category
                if self.category and torrent.category != self.category:
                    console.print(f"[yellow]  ⚠️ Category mismatch: expected '{self.category}', got '{torrent.category}'[/yellow]")
                
                # Verify tags
                torrent_tags = set(torrent.tags.split(', ')) if torrent.tags else set()
                expected_tags = set(self.tags)
                if expected_tags and not expected_tags.issubset(torrent_tags):
                    missing = expected_tags - torrent_tags
                    console.print(f"[yellow]  ⚠️ Missing tags: {', '.join(missing)}[/yellow]")
                
                # Verify auto management
                if torrent.auto_tmm != self.auto_management:
                    console.print(f"[yellow]  ⚠️ Auto management: expected {self.auto_management}, got {torrent.auto_tmm}[/yellow]")
                
                # Show final status
                console.print(f"\n[cyan]Torrent Details:[/cyan]")
                console.print(f"  Hash: {torrent.hash[:16]}...")
                console.print(f"  Name: {torrent.name}")
                console.print(f"  Category: {torrent.category}")
                console.print(f"  Tags: {torrent.tags}")
                console.print(f"  Auto Management: {torrent.auto_tmm}")
                console.print(f"  State: {torrent.state}")
                
        except Exception as e:
            console.print(f"[yellow]Could not verify settings: {e}[/yellow]")
    
    def create_single(self):
        """Interactive single torrent creation"""
        console.print(Panel.fit("🎯 Single Torrent Creation", style="bold blue"))
        
        # Get source path
        source = Prompt.ask("Enter path to file/folder", default=".")
        source_path = Path(source).expanduser().resolve()
        
        if not source_path.exists():
            console.print(f"[red]Path does not exist: {source_path}[/red]")
            return
        
        # Docker path mapping if needed
        if self.mode == QBitMode.DOCKER:
            docker_source = self._map_to_docker_path(source_path)
            console.print(f"[cyan]Docker path: {docker_source}[/cyan]")
        
        # Get output location
        default_output = self.config.get("output_directory", str(Path.cwd()))
        output_dir = Prompt.ask("Output directory for .torrent file", default=default_output)
        output_dir = Path(output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate torrent filename
        torrent_name = f"{source_path.name}.torrent"
        output_path = output_dir / torrent_name
        
        # Configure torrent options
        self._configure_torrent_options()
        
        # Ask about qBittorrent integration
        if self.client:
            self.start_seeding = Confirm.ask("Start seeding immediately after creation?", 
                                            default=self.config.get("auto_start_seeding", True))
            
            # Check if source is set and warn about cross-seeding
            if self.source:
                console.print(f"\n[yellow]⚠️ Source is set to '{self.source}'[/yellow]")
                console.print("[yellow]Remember to download the .torrent file for cross-seeding on other trackers[/yellow]")
                
                # Offer to save a copy
                if Confirm.ask("Save a backup copy of the .torrent file?", default=True):
                    backup_dir = Path(self.config.get("backup_directory", Path.home() / "torrent_backups"))
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    backup_path = backup_dir / f"{source_path.name}_{self.source}.torrent"
                    console.print(f"[dim]Backup will be saved to: {backup_path}[/dim]")
            
            # Ask about automatic management
            self.auto_management = Confirm.ask("Enable automatic torrent management?",
                                              default=self.config.get("auto_torrent_management", True))
            
            # Use configured defaults but allow override
            if self.category or Confirm.ask("Set category?", default=bool(self.category)):
                categories = self._get_available_categories()
                if categories:
                    console.print(f"Available categories: {', '.join(categories)}")
                self.category = Prompt.ask("Category", default=self.category)
            
            # Use configured defaults but allow override
            if self.tags or Confirm.ask("Add tags?", default=bool(self.tags)):
                available_tags = self._get_available_tags()
                if available_tags:
                    console.print(f"Available tags: {', '.join(available_tags)}")
                tags_input = Prompt.ask("Tags (comma-separated)", 
                                       default=','.join(self.tags) if self.tags else "")
                self.tags = [t.strip() for t in tags_input.split(',') if t.strip()]
        
        # Create torrent
        success = self.create_torrent_via_api(source_path, output_path)
        
        if success:
            console.print(f"[green]✅ Torrent created successfully![/green]")
            if self.start_seeding:
                console.print(f"[green]✅ Now seeding in qBittorrent[/green]")
            self._save_to_history(source_path, output_path)
        else:
            console.print("[red]✗ Failed to create torrent[/red]")
    
    def _get_available_categories(self) -> List[str]:
        """Get list of available categories from qBittorrent"""
        if not self.client:
            return []
        try:
            categories = self.client.torrents_categories()
            return list(categories.keys())
        except:
            return []
    
    def _get_available_tags(self) -> List[str]:
        """Get available tags from qBittorrent"""
        if self.client:
            try:
                tags = self.client.torrents_tags()
                # Fix: Ensure we return a list of strings
                if isinstance(tags, list):
                    return [str(tag) for tag in tags]
                return []
            except:
                pass
        return []
    
    def create_batch(self):
        """Interactive batch torrent creation"""
        console.print(Panel.fit("📦 Batch Torrent Creation", style="bold blue"))
        
        # Get base directory
        base_dir = Prompt.ask("Base directory containing items", default=".")
        base_path = Path(base_dir).expanduser().resolve()
        
        if not base_path.exists() or not base_path.is_dir():
            console.print(f"[red]Invalid directory: {base_path}[/red]")
            return
        
        # Count items first
        total_items = len([d for d in base_path.iterdir() if not d.name.startswith('.')])
        console.print(f"[cyan]Directory contains {total_items} items[/cyan]")
        
        # Get items to create torrents for
        items = self._select_items_for_batch(base_path)
        if not items:
            console.print("[yellow]No items selected[/yellow]")
            return
        
        console.print(f"\n[green]Creating torrents for {len(items)} selected items[/green]")
        
        # Show what was selected
        console.print("\n[cyan]Selected items:[/cyan]")
        for item in items[:10]:  # Show first 10
            console.print(f"  • {item.name}")
        if len(items) > 10:
            console.print(f"  [dim]... and {len(items) - 10} more[/dim]")
        
        # Confirm before proceeding
        if not Confirm.ask(f"\nCreate {len(items)} torrents?", default=True):
            console.print("[yellow]Cancelled[/yellow]")
            return
        
        # Get output directory
        default_output = self.config.get("output_directory", str(Path.cwd()))
        output_dir = Prompt.ask("Output directory for torrents", default=default_output)
        output_dir = Path(output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure torrent options (apply to all)
        self._configure_torrent_options()
        
        # Ask about category and tags once for all
        if self.client:
            if Confirm.ask("Apply same category to all?", default=bool(self.category)):
                self.category = Prompt.ask("Category", default=self.category)
            
            if Confirm.ask("Apply same tags to all?", default=bool(self.tags)):
                tags_input = Prompt.ask("Tags (comma-separated)", 
                                       default=','.join(self.tags) if self.tags else "")
                self.tags = [t.strip() for t in tags_input.split(',') if t.strip()]
        
        # Create torrents
        console.print(f"\n[cyan]Creating {len(items)} torrents...[/cyan]")
        
        successful = 0
        failed = 0
        
        for item in tqdm(items, desc="Creating torrents", unit="torrent"):
            torrent_name = f"{item.name}.torrent"
            output_path = output_dir / torrent_name
            
            if self.create_torrent_via_api(item, output_path):
                successful += 1
                console.print(f"[green]✓ {torrent_name}[/green]")
                self._save_to_history(item, output_path)
            else:
                failed += 1
                console.print(f"[red]✗ {torrent_name}[/red]")
        
        # Summary
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  [green]Successful: {successful}[/green]")
        if failed > 0:
            console.print(f"  [red]Failed: {failed}[/red]")
    
    def _select_items_for_batch(self, base_path: Path) -> List[Path]:
        """Interactive selection of items for batch processing"""
        items = []
        for item in sorted(base_path.iterdir()):
            if item.name.startswith('.'):
                continue
            # Ensure we're creating proper tuples with strings
            items.append((item.name, item))  # item.name is already a string
        
        if not items:
            return []
        
        # Show count and let user know they can select specific items
        console.print(f"\n[cyan]Found {len(items)} items in directory[/cyan]")
        console.print("[dim]Use SPACE to select/deselect, TAB to select all/none, ENTER to confirm[/dim]")
        console.print("[dim]You can select as many or as few items as you want[/dim]\n")
        
        # Use checkboxlist for multiple selection
        try:
            from prompt_toolkit.shortcuts import checkboxlist_dialog
            
            # Create the dialog with proper string labels
            selected = checkboxlist_dialog(
                title="Select items to create torrents for",
                text="Use space to select/deselect, Enter to confirm:",
                values=items  # items is list of (string, Path) tuples
            ).run()
            
            if selected is None:  # User cancelled
                return []
                
            return selected  # Returns list of Path objects
            
        except Exception as e:
            console.print(f"[red]Error in selection dialog: {e}[/red]")
            console.print(f"[yellow]Falling back to manual selection[/yellow]")
            # Fallback to manual selection
            return self._manual_select_items(items)
    
    def _manual_select_items(self, items: List[tuple]) -> List[Path]:
        """Fallback manual selection if dialog fails"""
        console.print("\n[yellow]Dialog failed, using manual selection[/yellow]")
        
        # Show numbered list
        for i, (name, path) in enumerate(items, 1):
            console.print(f"{i:3d}. {name}")
        
        console.print("\n[cyan]Enter item numbers to create torrents for[/cyan]")
        console.print("[dim]Examples: '1-5' for range, '1,3,5' for specific items, 'all' for everything[/dim]")
        
        selection = Prompt.ask("Selection", default="1-5")
        
        selected_paths = []
        
        if selection.lower() == 'all':
            return [path for name, path in items]
        
        # Parse selection
        try:
            indices = set()
            for part in selection.split(','):
                part = part.strip()
                if '-' in part:
                    # Range
                    start, end = part.split('-')
                    start, end = int(start.strip()), int(end.strip())
                    indices.update(range(start, end + 1))
                else:
                    # Single number
                    indices.add(int(part))
            
            # Convert to paths
            for idx in sorted(indices):
                if 1 <= idx <= len(items):
                    selected_paths.append(items[idx - 1][1])
            
        except ValueError:
            console.print("[red]Invalid selection format[/red]")
            return []
        
        console.print(f"\n[green]Selected {len(selected_paths)} items[/green]")
        return selected_paths
    
    def _configure_torrent_options(self):
        """Interactive configuration of torrent options"""
        console.print("\n[bold cyan]Configure Torrent Options[/bold cyan]")
        
        # Torrent format selection
        format_options = {
            "1": "v1",
            "2": "v2", 
            "3": "hybrid"
        }
        
        console.print("\n[cyan]Torrent Format:[/cyan]")
        console.print("  1. v1 (Compatible with all clients) [recommended]")
        console.print("  2. v2 (Modern, better hash tree)")
        console.print("  3. hybrid (Both v1 and v2, larger file)")
        
        format_choice = Prompt.ask(
            "Select format", 
            choices=["1", "2", "3"], 
            default="1"
        )
        self.torrent_format = format_options[format_choice]
        
        if self.torrent_format == "v2":
            console.print("[yellow]⚠️ Warning: Many trackers don't support v2 torrents yet![/yellow]")
            if not Confirm.ask("Continue with v2 format?", default=False):
                self.torrent_format = "v1"
                console.print("[green]Switched to v1 format for compatibility[/green]")
        
        # Source field for cross-seeding
        console.print("\n[cyan]Source Identification:[/cyan]")
        console.print("[dim]The source field helps identify torrents for cross-seeding[/dim]")
        
        # Show common source tags from config
        common_sources = self.config.get("common_sources", ["RED", "OPS", "GGn", "PTP", "BTN", "MAM"])
        if common_sources:
            console.print(f"Common sources: {', '.join(common_sources)}")
        
        if Confirm.ask("Set source field?", default=bool(self.source)):
            self.source = Prompt.ask("Source tag", default=self.source if self.source else "")
            
            # Warn about cross-seeding implications
            if self.source:
                console.print(f"[yellow]ℹ️ Source set to '{self.source}' - download the .torrent file for safe cross-seeding[/yellow]")
        
        # Trackers
        if Confirm.ask("Add trackers?", default=True):
            self._add_trackers()
        
        # Web seeds
        if Confirm.ask("Add web seeds?", default=False):
            self._add_web_seeds()
        
        # Private torrent - default from config
        self.private = Confirm.ask("Make private torrent?", 
                                  default=self.config.get("default_private", True))
        
        # Comment
        if Confirm.ask("Add comment?", default=False):
            # Offer templates
            comment_templates = self.config.get("comment_templates", [])
            if comment_templates:
                console.print("Comment templates:")
                for i, template in enumerate(comment_templates, 1):
                    console.print(f"  {i}. {template}")
                console.print("  0. Custom comment")
                
                # Fix: Remove invalid parameters from IntPrompt.ask
                choice = IntPrompt.ask("Select template", default=0)
                if choice == 0:
                    self.comment = Prompt.ask("Comment")
                elif 0 < choice <= len(comment_templates):
                    self.comment = comment_templates[choice - 1]
            else:
                self.comment = Prompt.ask("Comment")
        
        # Advanced options
        if Confirm.ask("Configure advanced options?", default=False):
            self._configure_advanced_options()
        
        # Piece size (let qBittorrent auto-select by default)
        if Confirm.ask("Set custom piece size?", default=False):
            sizes = {
                "Auto": None,
                "16 KiB": 16384,
                "32 KiB": 32768,
                "64 KiB": 65536,
                "128 KiB": 131072,
                "256 KiB": 262144,
                "512 KiB": 524288,
                "1 MiB": 1048576,
                "2 MiB": 2097152,
                "4 MiB": 4194304,
                "8 MiB": 8388608,
                "16 MiB": 16777216
            }
            
            size_names = list(sizes.keys())
            for i, size in enumerate(size_names, 1):
                console.print(f"{i}. {size}")
            
            # Fix: Remove invalid parameters from IntPrompt.ask
            idx = IntPrompt.ask("Select", default=1)
            if 1 <= idx <= len(size_names):
                self.piece_size = sizes[size_names[idx - 1]]
    
    def _configure_advanced_options(self):
        """Configure advanced torrent creation options"""
        console.print("\n[cyan]Advanced Options:[/cyan]")
        
        # Optimize alignment
        self.optimize_alignment = Confirm.ask(
            "Optimize file alignment?",
            default=self.config.get("optimize_alignment", True)
        )
        
        # Padding files
        if Confirm.ask("Configure padding?", default=False):
            console.print("[dim]Padding files help with alignment but increase torrent size[/dim]")
            console.print("Enter size limit in MB (0 = no padding, -1 = auto):")
            # Fix: Remove invalid parameters from IntPrompt.ask
            mb_limit = IntPrompt.ask("Padding limit (MB)", default=-1)
            self.padded_file_size_limit = mb_limit * 1024 * 1024 if mb_limit > 0 else mb_limit
    
    def _add_trackers(self):
        """Add tracker URLs"""
        self.load_default_trackers()
        
        if self.trackers:
            console.print("[cyan]Current trackers:[/cyan]")
            for t in self.trackers:
                console.print(f"  • {t}")
            
            if not Confirm.ask("Keep existing trackers?", default=True):
                self.trackers = []
        
        while True:
            tracker = Prompt.ask("Add tracker URL (empty to finish)", default="")
            if not tracker:
                break
            self.trackers.append(tracker)
    
    def _add_web_seeds(self):
        """Add web seed URLs"""
        while True:
            seed = Prompt.ask("Add web seed URL (empty to finish)", default="")
            if not seed:
                break
            self.web_seeds.append(seed)
            self.url_seeds.append(seed)  # Keep both in sync
    
    def _map_to_docker_path(self, host_path: Path) -> str:
        """Map host path to Docker container path"""
        # Use mappings from config
        mappings = self.config.get("docker_mappings", {})
        
        str_path = str(host_path)
        for host_prefix, docker_prefix in mappings.items():
            if str_path.startswith(host_prefix):
                mapped = str_path.replace(host_prefix, docker_prefix, 1)
                console.print(f"[dim]Path mapping: {str_path} → {mapped}[/dim]")
                return mapped
        
        console.print(f"[yellow]Warning: No Docker mapping found for {host_path}[/yellow]")
        return str_path
    
    def _save_to_history(self, source: Path, output: Path):
        """Save torrent creation to history database"""
        try:
            from database import save_torrent_history
            save_torrent_history(source, output, self.trackers, self.private)
        except ImportError:
            # If database module not available, skip history
            pass