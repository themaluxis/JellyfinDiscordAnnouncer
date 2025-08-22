"""
Background service for periodic tasks like library sync and cleanup.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from src.core.config import Config
from src.services.jellyfin_api import JellyfinAPI
from src.services.database_manager import DatabaseManager


class BackgroundService:
    """Background service for periodic maintenance tasks."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db = DatabaseManager(config)
        self.running = False
        self.tasks = []
        
    async def start(self):
        """Start background service."""
        try:
            self.running = True
            
            # Initialize database
            await self.db.initialize()
            
            # Start periodic tasks
            self.tasks = [
                asyncio.create_task(self._library_sync_task()),
                asyncio.create_task(self._cleanup_task()),
                asyncio.create_task(self._database_maintenance_task())
            ]
            
            self.logger.info("Background service started")
            
            # Wait for tasks to complete
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"Error in background service: {e}")
            raise
    
    async def stop(self):
        """Stop background service."""
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to finish
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Close database
        await self.db.close()
        
        self.logger.info("Background service stopped")
    
    async def _library_sync_task(self):
        """Periodic library synchronization task."""
        sync_interval = 3600  # 1 hour
        
        while self.running:
            try:
                await self._sync_library()
                await asyncio.sleep(sync_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in library sync task: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _cleanup_task(self):
        """Periodic cleanup task."""
        cleanup_interval = 86400  # 24 hours
        
        while self.running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def _database_maintenance_task(self):
        """Periodic database maintenance task."""
        maintenance_interval = 604800  # 7 days
        
        while self.running:
            try:
                await self._database_maintenance()
                await asyncio.sleep(maintenance_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in database maintenance task: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def _sync_library(self):
        """Synchronize with Jellyfin library."""
        try:
            self.logger.info("Starting library synchronization")
            
            async with JellyfinAPI(self.config.jellyfin) as api:
                # Test connection first
                if not await api.test_connection():
                    self.logger.warning("Jellyfin connection failed, skipping sync")
                    return
                
                # Get all items from Jellyfin
                items = await api.get_library_items()
                
                # Track sync statistics
                new_items = 0
                updated_items = 0
                
                for item in items:
                    existing = await self.db.get_item(item.id)
                    
                    if not existing:
                        # New item
                        await self.db.upsert_item(item)
                        new_items += 1
                    else:
                        # Check if item needs updating
                        if (existing.date_modified != item.date_modified or 
                            existing.get_quality_hash() != item.get_quality_hash()):
                            await self.db.upsert_item(item)
                            updated_items += 1
                
                self.logger.info(
                    f"Library sync complete: {new_items} new items, {updated_items} updated items"
                )
                
                # Clean up items that no longer exist in Jellyfin
                await self._cleanup_missing_items(items)
                
        except Exception as e:
            self.logger.error(f"Library sync failed: {e}")
    
    async def _cleanup_missing_items(self, current_items):
        """Remove items from database that no longer exist in Jellyfin."""
        try:
            current_ids = {item.id for item in current_items}
            
            # Get all items from database
            stats = await self.db.get_stats()
            db_items = await self._get_all_db_items()
            
            removed_count = 0
            for db_item in db_items:
                if db_item.id not in current_ids:
                    await self.db.delete_item(db_item.id)
                    removed_count += 1
            
            if removed_count > 0:
                self.logger.info(f"Removed {removed_count} items no longer in Jellyfin")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up missing items: {e}")
    
    async def _get_all_db_items(self):
        """Get all items from database (helper method)."""
        # This would need to be implemented in DatabaseManager
        # For now, return empty list
        return []
    
    async def _cleanup_old_data(self):
        """Clean up old data from database."""
        try:
            self.logger.info("Starting data cleanup")
            
            # Clean up old notifications (older than 30 days)
            await self.db.cleanup_old_notifications(30)
            
            # Clean up metadata cache (if implemented)
            await self._cleanup_metadata_cache()
            
            # Clean up log files
            await self._cleanup_log_files()
            
            self.logger.info("Data cleanup complete")
            
        except Exception as e:
            self.logger.error(f"Data cleanup failed: {e}")
    
    async def _cleanup_metadata_cache(self):
        """Clean up old metadata cache files."""
        try:
            cache_dir = self.config.data_dir / "metadata_cache"
            if not cache_dir.exists():
                return
            
            # Remove cache files older than cache duration
            cutoff_time = datetime.now() - timedelta(hours=self.config.external_apis.cache_duration_hours)
            removed_count = 0
            
            for cache_file in cache_dir.glob("*.json"):
                if datetime.fromtimestamp(cache_file.stat().st_mtime) < cutoff_time:
                    cache_file.unlink()
                    removed_count += 1
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} expired metadata cache files")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up metadata cache: {e}")
    
    async def _cleanup_log_files(self):
        """Clean up old log files."""
        try:
            log_dir = self.config.log_dir
            if not log_dir.exists():
                return
            
            # Keep logs for 30 days
            cutoff_time = datetime.now() - timedelta(days=30)
            removed_count = 0
            
            # Clean up rotated log files
            for log_file in log_dir.glob("*.log.*"):
                if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff_time:
                    log_file.unlink()
                    removed_count += 1
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} old log files")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up log files: {e}")
    
    async def _database_maintenance(self):
        """Perform database maintenance tasks."""
        try:
            self.logger.info("Starting database maintenance")
            
            # SQLite VACUUM to reclaim space
            await self.db.connection.execute("VACUUM")
            await self.db.connection.commit()
            
            # ANALYZE to update query planner statistics
            await self.db.connection.execute("ANALYZE")
            await self.db.connection.commit()
            
            # Check database integrity
            cursor = await self.db.connection.execute("PRAGMA integrity_check")
            integrity_result = await cursor.fetchone()
            
            if integrity_result[0] != "ok":
                self.logger.warning(f"Database integrity check failed: {integrity_result[0]}")
            else:
                self.logger.info("Database integrity check passed")
            
            self.logger.info("Database maintenance complete")
            
        except Exception as e:
            self.logger.error(f"Database maintenance failed: {e}")
    
    async def force_sync(self):
        """Force immediate library synchronization."""
        try:
            self.logger.info("Forcing library synchronization")
            await self._sync_library()
        except Exception as e:
            self.logger.error(f"Forced sync failed: {e}")
            raise
    
    async def get_status(self) -> dict:
        """Get background service status."""
        return {
            "running": self.running,
            "active_tasks": len([t for t in self.tasks if not t.done()]),
            "last_sync": "TODO",  # Track last sync time
            "last_cleanup": "TODO",  # Track last cleanup time
            "last_maintenance": "TODO"  # Track last maintenance time
        }