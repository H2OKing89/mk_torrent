"""Database operations for torrent creation history"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional

from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class TorrentHistory(Base):
    __tablename__ = 'torrent_history'
    
    id = Column(String, primary_key=True)
    source_path = Column(String, nullable=False)
    output_path = Column(String, nullable=False)
    trackers = Column(Text)  # JSON string
    private = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    file_size = Column(String)

def get_db_session():
    """Get database session"""
    db_path = Path.home() / ".config" / "torrent_creator" / "history.db"
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
