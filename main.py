#!/usr/bin/env python3
"""
Jellynouncer - Intelligent Discord Notifications for Jellyfin Media Server
Main entry point for the application.
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from src.core.config import Config
from src.core.logger import setup_logging
from src.services.webhook_service import WebhookService
from src.services.background_service import BackgroundService


class JellynouncerApp:
    """Main application orchestrator."""
    
    def __init__(self):
        self.config = None
        self.webhook_service = None
        self.background_service = None
        self.shutdown_event = asyncio.Event()
        
    async def startup(self):
        """Initialize and start all services."""
        try:
            # Load configuration
            self.config = Config()
            
            # Setup logging
            setup_logging(self.config.log_level, self.config.log_dir)
            logger = logging.getLogger(__name__)
            logger.info("Starting Jellynouncer v1.0.0")
            
            # Initialize services
            self.webhook_service = WebhookService(self.config)
            self.background_service = BackgroundService(self.config)
            
            # Start services based on run mode
            run_mode = os.getenv('JELLYNOUNCER_RUN_MODE', 'all').lower()
            
            if run_mode in ['all', 'webhook']:
                await self.webhook_service.start()
                logger.info("Webhook service started on port 1984")
            
            if run_mode in ['all', 'background']:
                await self.background_service.start()
                logger.info("Background service started")
                
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to start application: {e}")
            raise
            
    async def shutdown(self):
        """Gracefully shutdown all services."""
        logger = logging.getLogger(__name__)
        logger.info("Shutting down Jellynouncer...")
        
        if self.background_service:
            await self.background_service.stop()
            
        if self.webhook_service:
            await self.webhook_service.stop()
            
        logger.info("Jellynouncer shutdown complete")
        
    def handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logging.getLogger(__name__).info(f"Received signal {signum}")
        self.shutdown_event.set()
        
    async def run(self):
        """Main application loop."""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        
        try:
            await self.startup()
            await self.shutdown_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            await self.shutdown()


def main():
    """Entry point."""
    # Ensure required directories exist
    for directory in ['config', 'data', 'logs', 'templates']:
        Path(directory).mkdir(exist_ok=True)
    
    app = JellynouncerApp()
    asyncio.run(app.run())


if __name__ == "__main__":
    main()