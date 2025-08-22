"""
Discord notification service with multi-channel routing and rate limiting.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import httpx
import json
from collections import deque

from src.core.config import Config, DiscordConfig, WebhookConfig
from src.services.jellyfin_api import MediaItem
from src.services.change_detector import DetectedChange
from src.services.template_engine import TemplateEngine


class RateLimiter:
    """Discord rate limiter (30 requests per minute per webhook)."""
    
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = {}
        self.logger = logging.getLogger(__name__)
    
    async def acquire(self, webhook_url: str) -> bool:
        """
        Acquire rate limit permission for webhook.
        
        Args:
            webhook_url: Discord webhook URL
            
        Returns:
            True if request can proceed, False if rate limited
        """
        now = datetime.now()
        
        if webhook_url not in self.requests:
            self.requests[webhook_url] = deque()
        
        request_times = self.requests[webhook_url]
        
        # Remove old requests outside the window
        while request_times and (now - request_times[0]).total_seconds() > self.window_seconds:
            request_times.popleft()
        
        # Check if we can make another request
        if len(request_times) >= self.max_requests:
            oldest_request = request_times[0]
            wait_time = self.window_seconds - (now - oldest_request).total_seconds()
            self.logger.warning(f"Rate limited for {wait_time:.1f}s on webhook")
            return False
        
        # Record this request
        request_times.append(now)
        return True
    
    async def wait_for_rate_limit(self, webhook_url: str):
        """Wait until rate limit allows the request."""
        while not await self.acquire(webhook_url):
            await asyncio.sleep(1)


class NotificationQueue:
    """Queue for managing notifications with grouping and batching."""
    
    def __init__(self, config: DiscordConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.queues: Dict[str, List[Dict[str, Any]]] = {}
        self.timers: Dict[str, asyncio.Task] = {}
        
    async def add_notification(self, webhook_key: str, notification_data: Dict[str, Any]):
        """Add notification to queue for potential grouping."""
        webhook_config = self.config.webhooks.get(webhook_key)
        if not webhook_config:
            self.logger.warning(f"No webhook config found for {webhook_key}")
            return
        
        grouping_mode = webhook_config.grouping.get("mode", "none")
        
        if grouping_mode == "none":
            # Send immediately
            await self._send_immediate(webhook_config, notification_data)
        else:
            # Add to queue for batching
            await self._add_to_batch_queue(webhook_key, notification_data)
    
    async def _send_immediate(self, webhook_config: WebhookConfig, notification_data: Dict[str, Any]):
        """Send notification immediately."""
        # This will be implemented when we have the actual sending logic
        pass
    
    async def _add_to_batch_queue(self, webhook_key: str, notification_data: Dict[str, Any]):
        """Add notification to batch queue."""
        if webhook_key not in self.queues:
            self.queues[webhook_key] = []
        
        self.queues[webhook_key].append(notification_data)
        
        # Cancel existing timer and start new one
        if webhook_key in self.timers:
            self.timers[webhook_key].cancel()
        
        webhook_config = self.config.webhooks[webhook_key]
        delay_minutes = webhook_config.grouping.get("delay_minutes", 5)
        
        self.timers[webhook_key] = asyncio.create_task(
            self._process_batch_after_delay(webhook_key, delay_minutes * 60)
        )
    
    async def _process_batch_after_delay(self, webhook_key: str, delay_seconds: int):
        """Process batched notifications after delay."""
        await asyncio.sleep(delay_seconds)
        
        if webhook_key in self.queues and self.queues[webhook_key]:
            notifications = self.queues[webhook_key].copy()
            self.queues[webhook_key].clear()
            
            webhook_config = self.config.webhooks[webhook_key]
            await self._send_batch(webhook_config, notifications)
        
        # Cleanup
        if webhook_key in self.timers:
            del self.timers[webhook_key]
    
    async def _send_batch(self, webhook_config: WebhookConfig, notifications: List[Dict[str, Any]]):
        """Send batched notifications."""
        # This will be implemented when we have the template engine
        pass


class DiscordNotifier:
    """Main Discord notification service."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.rate_limiter = RateLimiter()
        self.notification_queue = NotificationQueue(config.discord)
        self.template_engine = None  # Will be initialized later
        
        # HTTP client for Discord API
        self.client = httpx.AsyncClient(
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
    
    async def initialize(self):
        """Initialize the notifier with template engine."""
        from src.services.template_engine import TemplateEngine
        self.template_engine = TemplateEngine(self.config)
        await self.template_engine.initialize()
    
    async def send_new_item_notification(self, item: MediaItem):
        """Send notification for new item."""
        try:
            webhook_config = self.config.discord.get_webhook_for_content_type(item.type)
            if not webhook_config or not webhook_config.enabled:
                self.logger.debug(f"No webhook configured for {item.type}")
                return
            
            # Prepare notification data
            notification_data = {
                "type": "new_item",
                "item": item,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add to queue (handles grouping/immediate sending)
            webhook_key = self._get_webhook_key_for_item(item)
            await self.notification_queue.add_notification(webhook_key, notification_data)
            
        except Exception as e:
            self.logger.error(f"Error sending new item notification: {e}")
            raise
    
    async def send_upgrade_notification(self, item: MediaItem, changes: Dict[str, DetectedChange]):
        """Send notification for item upgrade."""
        try:
            webhook_config = self.config.discord.get_webhook_for_content_type(item.type)
            if not webhook_config or not webhook_config.enabled:
                self.logger.debug(f"No webhook configured for {item.type}")
                return
            
            # Prepare notification data
            notification_data = {
                "type": "upgrade",
                "item": item,
                "changes": changes,
                "timestamp": datetime.now().isoformat()
            }
            
            webhook_key = self._get_webhook_key_for_item(item)
            await self.notification_queue.add_notification(webhook_key, notification_data)
            
        except Exception as e:
            self.logger.error(f"Error sending upgrade notification: {e}")
            raise
    
    async def send_deletion_notification(self, webhook_data: Dict[str, Any]):
        """Send notification for item deletion."""
        try:
            # Use default webhook for deletions
            webhook_config = self.config.discord.webhooks.get("default")
            if not webhook_config or not webhook_config.enabled:
                self.logger.debug("No default webhook configured for deletions")
                return
            
            notification_data = {
                "type": "deletion",
                "webhook_data": webhook_data,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.notification_queue.add_notification("default", notification_data)
            
        except Exception as e:
            self.logger.error(f"Error sending deletion notification: {e}")
            raise
    
    async def send_discord_webhook(self, webhook_url: str, embed_data: Dict[str, Any]) -> bool:
        """
        Send webhook to Discord.
        
        Args:
            webhook_url: Discord webhook URL
            embed_data: Discord embed data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Wait for rate limit
            await self.rate_limiter.wait_for_rate_limit(webhook_url)
            
            # Send webhook
            response = await self.client.post(webhook_url, json=embed_data)
            
            if response.status_code == 204:
                self.logger.debug("Discord webhook sent successfully")
                return True
            elif response.status_code == 429:
                # Rate limited by Discord
                retry_after = response.json().get("retry_after", 1)
                self.logger.warning(f"Discord rate limit hit, retrying after {retry_after}s")
                await asyncio.sleep(retry_after)
                return await self.send_discord_webhook(webhook_url, embed_data)
            else:
                self.logger.error(f"Discord webhook failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending Discord webhook: {e}")
            return False
    
    async def test_webhook(self, webhook_url: str) -> bool:
        """Test Discord webhook connectivity."""
        try:
            test_embed = {
                "embeds": [{
                    "title": "🔔 Jellynouncer Test",
                    "description": "This is a test notification from Jellynouncer",
                    "color": 0x5865F2,  # Discord blue
                    "timestamp": datetime.now().isoformat(),
                    "footer": {
                        "text": "Jellynouncer v1.0.0"
                    }
                }]
            }
            
            return await self.send_discord_webhook(webhook_url, test_embed)
            
        except Exception as e:
            self.logger.error(f"Error testing webhook: {e}")
            return False
    
    def _get_webhook_key_for_item(self, item: MediaItem) -> str:
        """Get appropriate webhook key for media item."""
        type_mapping = {
            "Movie": "movies",
            "Series": "tv", 
            "Episode": "tv",
            "Audio": "music",
            "MusicAlbum": "music"
        }
        
        return type_mapping.get(item.type, "default")
    
    async def close(self):
        """Close the Discord notifier."""
        if self.client:
            await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()