"""
Database manager for Jellynouncer using SQLite with WAL mode.
Handles media item tracking and change detection.
"""

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import aiosqlite
import json

from src.core.config import Config
from src.services.jellyfin_api import MediaItem


class DatabaseManager:
    """SQLite database manager with WAL mode for concurrent access."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db_path = config.data_dir / "jellynouncer.db"
        self.connection = None
        
    async def initialize(self):
        """Initialize database with required tables."""
        try:
            # Ensure data directory exists
            self.config.data_dir.mkdir(exist_ok=True)
            
            # Connect and setup WAL mode
            self.connection = await aiosqlite.connect(self.db_path)
            await self.connection.execute("PRAGMA journal_mode=WAL")
            await self.connection.execute("PRAGMA synchronous=NORMAL")
            await self.connection.execute("PRAGMA cache_size=1000")
            await self.connection.execute("PRAGMA temp_store=memory")
            
            # Create tables
            await self._create_tables()
            
            self.logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _create_tables(self):
        """Create database tables."""
        # Media items table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS media_items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                path TEXT NOT NULL,
                size INTEGER,
                date_created TEXT,
                date_modified TEXT,
                
                -- Media metadata
                overview TEXT,
                year INTEGER,
                runtime_ticks INTEGER,
                genres TEXT,  -- JSON array
                
                -- Series/Episode specific
                series_name TEXT,
                season_number INTEGER,
                episode_number INTEGER,
                
                -- Technical info (stored as JSON)
                streams TEXT,  -- JSON array of MediaStream objects
                
                -- External IDs
                imdb_id TEXT,
                tmdb_id TEXT,
                tvdb_id TEXT,
                
                -- Quality tracking
                quality_hash TEXT,
                
                -- Timestamps
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Notifications log
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                webhook_url TEXT,
                status TEXT DEFAULT 'pending',  -- pending, sent, failed
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                sent_at TEXT
            )
        """)
        
        # Quality changes log
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS quality_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                change_type TEXT NOT NULL,  -- resolution, codec, audio, hdr
                old_value TEXT,
                new_value TEXT,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_media_items_path ON media_items(path)")
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_media_items_type ON media_items(type)")
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_media_items_quality_hash ON media_items(quality_hash)")
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_notifications_item_id ON notifications(item_id)")
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at)")
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_quality_changes_item_id ON quality_changes(item_id)")
        
        await self.connection.commit()
    
    async def get_item(self, item_id: str) -> Optional[MediaItem]:
        """Get media item by ID."""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM media_items WHERE id = ?", (item_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                return self._row_to_media_item(row)
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting item {item_id}: {e}")
            return None
    
    async def get_item_by_path(self, path: str) -> Optional[MediaItem]:
        """Get media item by file path."""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM media_items WHERE path = ?", (path,)
            )
            row = await cursor.fetchone()
            
            if row:
                return self._row_to_media_item(row)
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting item by path {path}: {e}")
            return None
    
    async def upsert_item(self, item: MediaItem):
        """Insert or update media item."""
        try:
            # Serialize complex data
            genres_json = json.dumps(item.genres) if item.genres else "[]"
            streams_json = json.dumps([{
                "codec": s.codec,
                "language": s.language,
                "title": s.title,
                "type": s.type,
                "width": s.width,
                "height": s.height,
                "channels": s.channels,
                "bit_rate": s.bit_rate,
                "video_range": s.video_range
            } for s in item.streams]) if item.streams else "[]"
            
            quality_hash = item.get_quality_hash()
            
            await self.connection.execute("""
                INSERT OR REPLACE INTO media_items (
                    id, name, type, path, size, date_created, date_modified,
                    overview, year, runtime_ticks, genres,
                    series_name, season_number, episode_number,
                    streams, imdb_id, tmdb_id, tvdb_id,
                    quality_hash, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.id, item.name, item.type, item.path, item.size,
                item.date_created, item.date_modified,
                item.overview, item.year, item.runtime_ticks, genres_json,
                item.series_name, item.season_number, item.episode_number,
                streams_json, item.imdb_id, item.tmdb_id, item.tvdb_id,
                quality_hash, datetime.now().isoformat()
            ))
            
            await self.connection.commit()
            self.logger.debug(f"Upserted item: {item.name}")
            
        except Exception as e:
            self.logger.error(f"Error upserting item {item.id}: {e}")
            raise
    
    async def update_item(self, item: MediaItem):
        """Update existing media item."""
        await self.upsert_item(item)
    
    async def delete_item(self, item_id: str):
        """Delete media item."""
        try:
            await self.connection.execute("DELETE FROM media_items WHERE id = ?", (item_id,))
            await self.connection.commit()
            self.logger.debug(f"Deleted item: {item_id}")
            
        except Exception as e:
            self.logger.error(f"Error deleting item {item_id}: {e}")
            raise
    
    async def log_notification(self, notification_type: str, item_id: str, item_name: str, 
                             webhook_url: Optional[str] = None):
        """Log notification attempt."""
        try:
            await self.connection.execute("""
                INSERT INTO notifications (notification_type, item_id, item_name, webhook_url)
                VALUES (?, ?, ?, ?)
            """, (notification_type, item_id, item_name, webhook_url))
            
            await self.connection.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging notification: {e}")
    
    async def update_notification_status(self, notification_id: int, status: str, 
                                       error_message: Optional[str] = None):
        """Update notification status."""
        try:
            sent_at = datetime.now().isoformat() if status == "sent" else None
            
            await self.connection.execute("""
                UPDATE notifications 
                SET status = ?, error_message = ?, sent_at = ?
                WHERE id = ?
            """, (status, error_message, sent_at, notification_id))
            
            await self.connection.commit()
            
        except Exception as e:
            self.logger.error(f"Error updating notification status: {e}")
    
    async def log_quality_change(self, item_id: str, change_type: str, 
                               old_value: str, new_value: str):
        """Log quality change detection."""
        try:
            await self.connection.execute("""
                INSERT INTO quality_changes (item_id, change_type, old_value, new_value)
                VALUES (?, ?, ?, ?)
            """, (item_id, change_type, old_value, new_value))
            
            await self.connection.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging quality change: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = {}
            
            # Total items by type
            cursor = await self.connection.execute("""
                SELECT type, COUNT(*) as count 
                FROM media_items 
                GROUP BY type
            """)
            type_counts = {row[0]: row[1] for row in await cursor.fetchall()}
            stats["items_by_type"] = type_counts
            stats["total_items"] = sum(type_counts.values())
            
            # Notification stats
            cursor = await self.connection.execute("""
                SELECT COUNT(*) FROM notifications
            """)
            stats["total_notifications"] = (await cursor.fetchone())[0]
            
            cursor = await self.connection.execute("""
                SELECT status, COUNT(*) as count
                FROM notifications
                GROUP BY status
            """)
            notification_stats = {row[0]: row[1] for row in await cursor.fetchall()}
            stats["notifications_by_status"] = notification_stats
            
            # Quality changes
            cursor = await self.connection.execute("""
                SELECT COUNT(*) FROM quality_changes
            """)
            stats["total_quality_changes"] = (await cursor.fetchone())[0]
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {}
    
    async def cleanup_old_notifications(self, days_old: int = 30):
        """Clean up old notification logs."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
            
            cursor = await self.connection.execute("""
                DELETE FROM notifications 
                WHERE created_at < ? AND status = 'sent'
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            await self.connection.commit()
            
            self.logger.info(f"Cleaned up {deleted_count} old notifications")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up notifications: {e}")
    
    def _row_to_media_item(self, row) -> MediaItem:
        """Convert database row to MediaItem object."""
        from src.services.jellyfin_api import MediaStream
        
        # Parse JSON fields
        genres = json.loads(row[10]) if row[10] else []
        
        streams = []
        if row[14]:  # streams column
            stream_data = json.loads(row[14])
            for s in stream_data:
                streams.append(MediaStream(
                    codec=s.get("codec"),
                    language=s.get("language"),
                    title=s.get("title"),
                    type=s.get("type"),
                    width=s.get("width"),
                    height=s.get("height"),
                    channels=s.get("channels"),
                    bit_rate=s.get("bit_rate"),
                    video_range=s.get("video_range")
                ))
        
        return MediaItem(
            id=row[0],
            name=row[1],
            type=row[2],
            path=row[3],
            size=row[4],
            date_created=row[5],
            date_modified=row[6],
            overview=row[7],
            year=row[8],
            runtime_ticks=row[9],
            genres=genres,
            series_name=row[11],
            season_number=row[12],
            episode_number=row[13],
            streams=streams,
            imdb_id=row[15],
            tmdb_id=row[16],
            tvdb_id=row[17]
        )
    
    async def close(self):
        """Close database connection."""
        if self.connection:
            await self.connection.close()
            self.logger.info("Database connection closed")