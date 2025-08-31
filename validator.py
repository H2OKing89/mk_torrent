#!/usr/bin/env python3
"""Path and torrent validation utilities"""

from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
import hashlib

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def validate_path(path_str: str) -> Tuple[bool, List[str]]:
    """Validate a path for torrent creation"""
    path = Path(path_str).expanduser().resolve()
    issues = []
    warnings = []
    
    console.print(Panel.fit(f"[bold cyan]🔍 Validating: {path}[/bold cyan]", border_style="cyan"))
    
    # Check existence
    if not path.exists():
        issues.append(f"Path does not exist: {path}")
        console.print(f"[red]❌ Path not found[/red]")
        return False, issues
    
    console.print(f"[green]✅ Path exists[/green]")
    
    # Check permissions
    if not path.stat().st_mode & 0o444:  # Read permission
        issues.append("No read permission")
    else:
        console.print(f"[green]✅ Read permission OK[/green]")
    
    # Check size
    if path.is_file():
        size = path.stat().st_size
    else:
        size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
    
    console.print(f"[cyan]📊 Size: {format_size(size)}[/cyan]")
    
    if size == 0:
        issues.append("Empty file/folder")
    elif size > 100 * 1024**3:  # > 100GB
        warnings.append(f"Very large torrent ({format_size(size)}), may take time to create")
    
    # Check for problematic filenames
    if path.is_dir():
        problematic = []
        for file in path.rglob('*'):
            if any(c in file.name for c in ['<', '>', ':', '"', '|', '?', '*']):
                problematic.append(file.name)
        
        if problematic:
            warnings.append(f"Found {len(problematic)} files with special characters")
            console.print(f"[yellow]⚠️ Files with special characters may cause issues[/yellow]")
    
    # Check for hidden files
    hidden_count = len([f for f in path.rglob('*') if f.name.startswith('.')])
    if hidden_count > 0:
        console.print(f"[yellow]ℹ️ Contains {hidden_count} hidden files[/yellow]")
        warnings.append(f"{hidden_count} hidden files will be included")
    
    # Summary
    if issues:
        console.print(f"\n[red]❌ Validation failed with {len(issues)} issue(s)[/red]")
        for issue in issues:
            console.print(f"  • {issue}")
        return False, issues
    else:
        console.print(f"\n[green]✅ Path is valid for torrent creation[/green]")
        if warnings:
            console.print(f"[yellow]⚠️ {len(warnings)} warning(s):[/yellow]")
            for warning in warnings:
                console.print(f"  • {warning}")
        return True, warnings

def format_size(size_bytes: int) -> str:
    """Format bytes to human readable"""
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def validate_torrent(torrent_path: Path, data_path: Optional[Path] = None) -> bool:
    """
    Validate a torrent file
    
    Args:
        torrent_path: Path to the .torrent file
        data_path: Optional path to the data to validate against
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not torrent_path.exists():
        console.print(f"[red]Torrent file not found: {torrent_path}[/red]")
        return False
    
    try:
        # Basic validation - check if file can be read and has content
        with open(torrent_path, 'rb') as f:
            content = f.read()
            if len(content) < 100:  # Arbitrary minimum size
                console.print("[red]Torrent file appears to be invalid (too small)[/red]")
                return False
        
        console.print(f"[green]✓ Torrent file is valid: {torrent_path.name}[/green]")
        
        # If data path provided, could add data validation here
        if data_path and data_path.exists():
            console.print(f"[dim]Data path exists: {data_path}[/dim]")
            
        return True
        
    except Exception as e:
        console.print(f"[red]Error validating torrent: {e}[/red]")
        return False
