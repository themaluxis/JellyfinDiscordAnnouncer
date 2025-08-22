"""
FastAPI webhook service for receiving Jellyfin notifications.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

from src.core.config import Config
from src.services.jellyfin_api import JellyfinAPI, MediaItem
from src.services.database_manager import DatabaseManager
from src.services.discord_notifier import DiscordNotifier
from src.services.change_detector import ChangeDetector


class DeletionQueue:
    """Queue for managing deletion events with delay."""
    
    def __init__(self, delay_seconds: int = 30):
        self.delay_seconds = delay_seconds
        self.queue: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def add_deletion(self, item_id: str, webhook_data: Dict[str, Any]):
        """Add deletion to queue with delay."""
        self.queue[item_id] = {
            "data": webhook_data,
            "timestamp": datetime.now(),
            "processed": False
        }
        
        self.logger.debug(f"Added deletion {item_id} to queue")
        
        # Schedule cleanup
        await asyncio.sleep(self.delay_seconds)
        await self._process_deletion(item_id)
    
    def check_and_remove(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Check if item is in deletion queue and remove it."""
        if item_id in self.queue:
            deletion_data = self.queue[item_id]
            del self.queue[item_id]
            self.logger.debug(f"Removed deletion {item_id} from queue (upgrade detected)")
            return deletion_data["data"]
        return None
    
    async def _process_deletion(self, item_id: str):
        """Process deletion after delay."""
        if item_id not in self.queue:
            return
        
        deletion_data = self.queue[item_id]
        if deletion_data["processed"]:
            return
        
        deletion_data["processed"] = True
        self.logger.info(f"Processing delayed deletion for item {item_id}")
        
        # TODO: Send deletion notification
        del self.queue[item_id]


class WebhookService:
    """FastAPI webhook service."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.app = FastAPI(
            title="Jellynouncer Webhook Service",
            description="Intelligent Discord notifications for Jellyfin",
            version="1.0.0"
        )
        
        self.db = DatabaseManager(config)
        self.discord = DiscordNotifier(config)
        self.change_detector = ChangeDetector()
        self.deletion_queue = DeletionQueue(config.notifications.deletion_delay_seconds)
        
        self._setup_routes()
        self.server = None
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.post("/webhook")
        async def webhook_handler(request: Request, background_tasks: BackgroundTasks):
            """Main webhook endpoint for Jellyfin."""
            try:
                # Parse webhook data
                body = await request.body()
                if not body:
                    raise HTTPException(status_code=400, detail="Empty request body")
                
                try:
                    webhook_data = json.loads(body)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid JSON")
                
                # Log webhook receipt
                event_type = webhook_data.get("NotificationType", "Unknown")
                item_name = webhook_data.get("Name", "Unknown")
                self.logger.info(f"Received webhook: {event_type} for '{item_name}'")
                
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"Webhook payload: {json.dumps(webhook_data, indent=2)}")
                
                # Process webhook in background
                background_tasks.add_task(self._process_webhook, webhook_data)
                
                return {"status": "received", "event": event_type}
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error processing webhook: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                # Test database connection
                stats = await self.db.get_stats()
                
                # Test Jellyfin connection
                async with JellyfinAPI(self.config.jellyfin) as api:
                    jellyfin_ok = await api.test_connection()
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "database": "connected",
                    "jellyfin": "connected" if jellyfin_ok else "error",
                    "total_items": stats.get("total_items", 0),
                    "total_notifications": stats.get("total_notifications", 0)
                }
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return JSONResponse(
                    status_code=503,
                    content={"status": "unhealthy", "error": str(e)}
                )
        
        @self.app.get("/stats")
        async def get_stats():
            """Get service statistics."""
            try:
                stats = await self.db.get_stats()
                return {
                    "database": stats,
                    "deletion_queue": len(self.deletion_queue.queue),
                    "uptime": "TODO"  # TODO: Track uptime
                }
            except Exception as e:
                self.logger.error(f"Error getting stats: {e}")
                raise HTTPException(status_code=500, detail="Failed to get stats")
        
        @self.app.post("/sync")
        async def trigger_sync(background_tasks: BackgroundTasks):
            """Trigger manual library synchronization."""
            background_tasks.add_task(self._sync_library)
            return {"status": "sync_started"}
        
        @self.app.post("/test-webhook")
        async def test_webhook(background_tasks: BackgroundTasks):
            """Send test notification."""
            test_data = {
                "NotificationType": "ItemAdded",
                "Name": "Test Movie",
                "ItemId": "test-123",
                "ItemType": "Movie",
                "Year": 2024
            }
            background_tasks.add_task(self._process_webhook, test_data)
            return {"status": "test_sent"}
    
    async def _process_webhook(self, webhook_data: Dict[str, Any]):
        """Process incoming webhook data."""
        try:
            event_type = webhook_data.get("NotificationType")
            item_id = webhook_data.get("ItemId")
            
            if not item_id:
                self.logger.warning("Webhook missing ItemId")
                return
            
            if event_type == "ItemDeleted":
                await self._handle_deletion(item_id, webhook_data)
            elif event_type == "ItemAdded":
                await self._handle_addition(item_id, webhook_data)
            else:
                self.logger.debug(f"Ignoring webhook event type: {event_type}")
                
        except Exception as e:
            self.logger.error(f"Error processing webhook: {e}")
    
    async def _handle_deletion(self, item_id: str, webhook_data: Dict[str, Any]):
        """Handle item deletion with delayed processing."""
        if self.config.notifications.filter_deletes:
            # Add to deletion queue for upgrade detection
            await self.deletion_queue.add_deletion(item_id, webhook_data)
        else:
            # Process deletion immediately
            await self._send_deletion_notification(item_id, webhook_data)
    
    async def _handle_addition(self, item_id: str, webhook_data: Dict[str, Any]):
        """Handle item addition."""
        # Check if this is an upgrade (deletion + addition)
        deletion_data = self.deletion_queue.check_and_remove(item_id)
        is_upgrade = deletion_data is not None
        
        # Get item details from Jellyfin
        async with JellyfinAPI(self.config.jellyfin) as api:
            item = await api.get_item(item_id)
        
        if not item:
            self.logger.warning(f"Could not retrieve item {item_id} from Jellyfin")
            return
        
        # Check for name-only changes (renames)
        if self.config.notifications.filter_renames:
            existing_item = await self.db.get_item_by_path(item.path)
            if existing_item and existing_item.name != item.name:
                self.logger.info(f"Detected rename: {existing_item.name} -> {item.name}")
                await self.db.update_item(item)
                return
        
        # Detect changes
        existing_item = await self.db.get_item(item_id)
        if existing_item:
            changes = self.change_detector.detect_changes(existing_item, item)
            if changes and not is_upgrade:
                # Quality upgrade without deletion
                await self._send_upgrade_notification(item, changes)
            elif not changes:
                self.logger.debug(f"No significant changes detected for {item.name}")
        else:
            # New item
            await self._send_new_item_notification(item)
        
        # Update database
        await self.db.upsert_item(item)
    
    async def _send_new_item_notification(self, item: MediaItem):
        """Send notification for new item."""
        try:
            await self.discord.send_new_item_notification(item)
            await self.db.log_notification("new_item", item.id, item.name)
            self.logger.info(f"Sent new item notification: {item.name}")
        except Exception as e:
            self.logger.error(f"Failed to send new item notification: {e}")
    
    async def _send_upgrade_notification(self, item: MediaItem, changes: Dict[str, Any]):
        """Send notification for item upgrade."""
        try:
            await self.discord.send_upgrade_notification(item, changes)
            await self.db.log_notification("upgrade", item.id, item.name)
            self.logger.info(f"Sent upgrade notification: {item.name}")
        except Exception as e:
            self.logger.error(f"Failed to send upgrade notification: {e}")
    
    async def _send_deletion_notification(self, item_id: str, webhook_data: Dict[str, Any]):
        """Send notification for item deletion."""
        try:
            item_name = webhook_data.get("Name", "Unknown")
            await self.discord.send_deletion_notification(webhook_data)
            await self.db.log_notification("deletion", item_id, item_name)
            self.logger.info(f"Sent deletion notification: {item_name}")
        except Exception as e:
            self.logger.error(f"Failed to send deletion notification: {e}")
    
    async def _sync_library(self):
        """Synchronize with Jellyfin library."""
        try:
            self.logger.info("Starting library synchronization")
            
            async with JellyfinAPI(self.config.jellyfin) as api:
                items = await api.get_library_items()
            
            sync_count = 0
            for item in items:
                existing = await self.db.get_item(item.id)
                if not existing:
                    await self.db.upsert_item(item)
                    sync_count += 1
            
            self.logger.info(f"Library sync complete: {sync_count} new items added")
            
        except Exception as e:
            self.logger.error(f"Library sync failed: {e}")
    
    async def start(self):
        """Start the webhook service."""
        try:
            # Initialize database
            await self.db.initialize()
            
            # Start server
            config = uvicorn.Config(
                app=self.app,
                host="0.0.0.0",
                port=1984,
                log_level="warning",  # Use our own logging
                access_log=False
            )
            self.server = uvicorn.Server(config)
            
            # Run server in background
            await self.server.serve()
            
        except Exception as e:
            self.logger.error(f"Failed to start webhook service: {e}")
            raise
    
    async def stop(self):
        """Stop the webhook service."""
        if self.server:
            self.server.should_exit = True
            await self.server.shutdown()
        
        if self.db:
            await self.db.close()