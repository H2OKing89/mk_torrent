#!/usr/bin/env python3
"""Database operations for torrent history tracking"""

from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime

from rich.console import Console

console = Console()

def get_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Get torrent creation history"""
    # Placeholder - will implement SQLite later
    return []

def clear_history() -> None:
    """Clear all history"""
    # Placeholder
    console.print("[yellow]History clearing not yet implemented[/yellow]")

def add_history_entry(path: str, size: int, status: str) -> None:
    """Add entry to history"""
    # Placeholder
    pass
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def save_torrent_history(source: Path, output: Path, trackers: List[str], private: bool):
    """Save torrent creation to history"""
    import json
    import uuid
    
    session = get_db_session()
    
    # Calculate file size
    if source.is_file():
        size = f"{source.stat().st_size / (1024**3):.2f} GB"
    else:
        total_size = sum(f.stat().st_size for f in source.rglob('*') if f.is_file())
        size = f"{total_size / (1024**3):.2f} GB"
    
    history = TorrentHistory(
        id=str(uuid.uuid4()),
        source_path=str(source),
        output_path=str(output),
        trackers=json.dumps(trackers),
        private=private,
        file_size=size
    )
    
    session.add(history)
    session.commit()
    session.close()

def get_recent_torrents(limit: int = 10):
    """Get recent torrent creations"""
    session = get_db_session()
    torrents = session.query(TorrentHistory).order_by(
        TorrentHistory.created_at.desc()
    ).limit(limit).all()
    session.close()
    return torrents
