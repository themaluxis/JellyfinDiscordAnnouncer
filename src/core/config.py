"""
Configuration management for Jellynouncer.
Supports JSON file configuration with environment variable overrides.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator
import logging


@dataclass
class JellyfinConfig:
    """Jellyfin server configuration."""
    server_url: str
    api_key: str
    user_id: str
    timeout: int = 30
    
    def __post_init__(self):
        if not self.server_url.startswith(('http://', 'https://')):
            self.server_url = f"http://{self.server_url}"
        self.server_url = self.server_url.rstrip('/')


@dataclass
class WebhookConfig:
    """Discord webhook configuration."""
    url: str
    enabled: bool = True
    grouping: Dict[str, Any] = field(default_factory=lambda: {
        "mode": "none",  # none, event, type, both
        "delay_minutes": 5,
        "max_items": 20
    })


@dataclass
class DiscordConfig:
    """Discord notification configuration."""
    webhooks: Dict[str, WebhookConfig] = field(default_factory=dict)
    routing: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "fallback_webhook": "default"
    })
    
    def get_webhook_for_content_type(self, content_type: str) -> Optional[WebhookConfig]:
        """Get appropriate webhook for content type."""
        type_mapping = {
            "Movie": "movies",
            "Series": "tv", 
            "Episode": "tv",
            "Audio": "music",
            "MusicAlbum": "music"
        }
        
        webhook_key = type_mapping.get(content_type, "default")
        return self.webhooks.get(webhook_key) or self.webhooks.get("default")


@dataclass
class NotificationConfig:
    """Notification behavior configuration."""
    watch_changes: Dict[str, bool] = field(default_factory=lambda: {
        "resolution": True,
        "codec": True,
        "audio_codec": True,
        "hdr_status": True,
        "quality": True
    })
    filter_renames: bool = True
    filter_deletes: bool = True
    deletion_delay_seconds: int = 30


@dataclass
class ExternalApiConfig:
    """External API configuration."""
    omdb_api_key: Optional[str] = None
    tmdb_api_key: Optional[str] = None
    tvdb_api_key: Optional[str] = None
    timeout: int = 10
    cache_duration_hours: int = 24


@dataclass
class WebConfig:
    """Web interface configuration."""
    enabled: bool = True
    port: int = 1985
    host: str = "0.0.0.0"
    jwt_secret_key: Optional[str] = None
    

class Config:
    """Main configuration manager."""
    
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = Path(config_path)
        self.config_data = {}
        
        # Load configuration
        self._load_config()
        self._apply_env_overrides()
        self._validate_config()
        
        # Initialize configuration objects
        self.jellyfin = self._create_jellyfin_config()
        self.discord = self._create_discord_config()
        self.notifications = self._create_notification_config()
        self.external_apis = self._create_external_api_config()
        self.web = self._create_web_config()
        
        # System configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.log_dir = Path(os.getenv('LOG_DIR', 'logs'))
        self.data_dir = Path(os.getenv('DATA_DIR', 'data'))
        self.template_dir = Path(os.getenv('TEMPLATE_DIR', 'templates'))
        
        # Ensure directories exist
        for directory in [self.log_dir, self.data_dir, self.template_dir]:
            directory.mkdir(exist_ok=True)
    
    def _load_config(self):
        """Load configuration from JSON file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self.config_data = json.load(f)
                logging.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logging.warning(f"Failed to load config file: {e}")
                self.config_data = {}
        else:
            logging.info("No config file found, using environment variables only")
            self.config_data = {}
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        env_mappings = {
            # Jellyfin
            'JELLYFIN_SERVER_URL': ['jellyfin', 'server_url'],
            'JELLYFIN_API_KEY': ['jellyfin', 'api_key'],
            'JELLYFIN_USER_ID': ['jellyfin', 'user_id'],
            
            # Discord webhooks
            'DISCORD_WEBHOOK_URL': ['discord', 'webhooks', 'default', 'url'],
            'DISCORD_WEBHOOK_URL_MOVIES': ['discord', 'webhooks', 'movies', 'url'],
            'DISCORD_WEBHOOK_URL_TV': ['discord', 'webhooks', 'tv', 'url'],
            'DISCORD_WEBHOOK_URL_MUSIC': ['discord', 'webhooks', 'music', 'url'],
            
            # External APIs
            'OMDB_API_KEY': ['external_apis', 'omdb_api_key'],
            'TMDB_API_KEY': ['external_apis', 'tmdb_api_key'],
            'TVDB_API_KEY': ['external_apis', 'tvdb_api_key'],
            
            # Web interface
            'JWT_SECRET_KEY': ['web', 'jwt_secret_key'],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested_config(config_path, value)
    
    def _set_nested_config(self, path: list, value: str):
        """Set nested configuration value."""
        current = self.config_data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _validate_config(self):
        """Validate required configuration."""
        required_fields = [
            ['jellyfin', 'server_url'],
            ['jellyfin', 'api_key'],
            ['jellyfin', 'user_id'],
        ]
        
        # Check for at least one Discord webhook
        discord_webhooks = self.config_data.get('discord', {}).get('webhooks', {})
        if not discord_webhooks and not os.getenv('DISCORD_WEBHOOK_URL'):
            raise ValueError("At least one Discord webhook URL must be configured")
        
        for field_path in required_fields:
            current = self.config_data
            for key in field_path:
                if key not in current:
                    raise ValueError(f"Required configuration missing: {'.'.join(field_path)}")
                current = current[key]
    
    def _create_jellyfin_config(self) -> JellyfinConfig:
        """Create Jellyfin configuration object."""
        jellyfin_data = self.config_data.get('jellyfin', {})
        return JellyfinConfig(
            server_url=jellyfin_data['server_url'],
            api_key=jellyfin_data['api_key'],
            user_id=jellyfin_data['user_id'],
            timeout=jellyfin_data.get('timeout', 30)
        )
    
    def _create_discord_config(self) -> DiscordConfig:
        """Create Discord configuration object."""
        discord_data = self.config_data.get('discord', {})
        webhooks = {}
        
        # Load webhooks from config
        webhook_configs = discord_data.get('webhooks', {})
        for name, webhook_data in webhook_configs.items():
            if isinstance(webhook_data, str):
                # Simple URL string
                webhooks[name] = WebhookConfig(url=webhook_data)
            else:
                # Full configuration object
                webhooks[name] = WebhookConfig(
                    url=webhook_data['url'],
                    enabled=webhook_data.get('enabled', True),
                    grouping=webhook_data.get('grouping', {})
                )
        
        return DiscordConfig(
            webhooks=webhooks,
            routing=discord_data.get('routing', {})
        )
    
    def _create_notification_config(self) -> NotificationConfig:
        """Create notification configuration object."""
        notifications_data = self.config_data.get('notifications', {})
        return NotificationConfig(
            watch_changes=notifications_data.get('watch_changes', {}),
            filter_renames=notifications_data.get('filter_renames', True),
            filter_deletes=notifications_data.get('filter_deletes', True),
            deletion_delay_seconds=notifications_data.get('deletion_delay_seconds', 30)
        )
    
    def _create_external_api_config(self) -> ExternalApiConfig:
        """Create external API configuration object."""
        api_data = self.config_data.get('external_apis', {})
        return ExternalApiConfig(
            omdb_api_key=api_data.get('omdb_api_key'),
            tmdb_api_key=api_data.get('tmdb_api_key'),
            tvdb_api_key=api_data.get('tvdb_api_key'),
            timeout=api_data.get('timeout', 10),
            cache_duration_hours=api_data.get('cache_duration_hours', 24)
        )
    
    def _create_web_config(self) -> WebConfig:
        """Create web interface configuration object."""
        web_data = self.config_data.get('web', {})
        
        # Generate JWT secret if not provided
        jwt_secret = web_data.get('jwt_secret_key')
        if not jwt_secret:
            import secrets
            jwt_secret = secrets.token_urlsafe(32)
            logging.info("Generated new JWT secret key")
        
        return WebConfig(
            enabled=web_data.get('enabled', True),
            port=int(web_data.get('port', 1985)),
            host=web_data.get('host', '0.0.0.0'),
            jwt_secret_key=jwt_secret
        )
    
    def save_config(self):
        """Save current configuration to file."""
        self.config_path.parent.mkdir(exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config_data, f, indent=2)
        logging.info(f"Configuration saved to {self.config_path}")