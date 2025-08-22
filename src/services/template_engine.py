"""
Jinja2 template engine for customizable Discord embed generation.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import jinja2
from jinja2 import Environment, FileSystemLoader, TemplateError
import json
from datetime import datetime

from src.core.config import Config
from src.services.jellyfin_api import MediaItem
from src.services.change_detector import DetectedChange


class TemplateEngine:
    """Jinja2 template engine for Discord embeds."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.template_dir = config.template_dir
        self.env = None
        
        # Template cache
        self._template_cache = {}
        
    async def initialize(self):
        """Initialize the template engine."""
        try:
            # Ensure template directory exists
            self.template_dir.mkdir(exist_ok=True)
            
            # Create default templates if they don't exist
            await self._create_default_templates()
            
            # Setup Jinja2 environment
            self.env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=True,
                trim_blocks=True,
                lstrip_blocks=True
            )
            
            # Add custom filters and functions
            self._setup_custom_filters()
            
            self.logger.info(f"Template engine initialized with templates from {self.template_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize template engine: {e}")
            raise
    
    def _setup_custom_filters(self):
        """Setup custom Jinja2 filters and functions."""
        
        @self.env.filter('format_runtime')
        def format_runtime(runtime_ticks):
            """Format runtime from ticks to human readable."""
            if not runtime_ticks:
                return "Unknown"
            
            # Jellyfin stores runtime in ticks (10,000,000 ticks per second)
            seconds = runtime_ticks // 10_000_000
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        
        @self.env.filter('format_file_size')
        def format_file_size(size_bytes):
            """Format file size in human-readable format."""
            if not size_bytes:
                return "Unknown"
            
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} PB"
        
        @self.env.filter('discord_timestamp')
        def discord_timestamp(iso_string, format_type='R'):
            """Convert ISO timestamp to Discord timestamp format."""
            if not iso_string:
                return ""
            
            try:
                dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
                timestamp = int(dt.timestamp())
                return f"<t:{timestamp}:{format_type}>"
            except:
                return iso_string
        
        @self.env.filter('truncate_text')
        def truncate_text(text, max_length=1024):
            """Truncate text to Discord's embed limits."""
            if not text:
                return ""
            
            if len(text) <= max_length:
                return text
            
            return text[:max_length-3] + "..."
        
        @self.env.filter('join_with_limit')
        def join_with_limit(items, separator=", ", max_length=256):
            """Join items with separator, respecting length limits."""
            if not items:
                return ""
            
            result = ""
            for item in items:
                new_result = result + (separator if result else "") + str(item)
                if len(new_result) > max_length:
                    if result:
                        result += separator + "..."
                    break
                result = new_result
            
            return result
        
        # Add global functions
        self.env.globals['now'] = datetime.now
        self.env.globals['format_change'] = self._format_change
    
    def _format_change(self, change: DetectedChange) -> str:
        """Format a change object for display."""
        if change.is_upgrade:
            return f"⬆️ {change.change_type.replace('_', ' ').title()}: {change.old_value} → {change.new_value}"
        else:
            return f"🔄 {change.change_type.replace('_', ' ').title()}: {change.old_value} → {change.new_value}"
    
    async def render_new_item_embed(self, item: MediaItem, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Render Discord embed for new item."""
        try:
            template = self.env.get_template("new_item.j2")
            
            context = {
                "item": item,
                "metadata": metadata or {},
                "config": self.config
            }
            
            rendered = template.render(context)
            return json.loads(rendered)
            
        except (TemplateError, json.JSONDecodeError) as e:
            self.logger.error(f"Error rendering new item template: {e}")
            return self._get_fallback_embed(item, "New Item Added")
    
    async def render_upgrade_embed(self, item: MediaItem, changes: Dict[str, DetectedChange], 
                                 metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Render Discord embed for item upgrade."""
        try:
            template = self.env.get_template("upgraded_item.j2")
            
            context = {
                "item": item,
                "changes": changes,
                "metadata": metadata or {},
                "config": self.config
            }
            
            rendered = template.render(context)
            return json.loads(rendered)
            
        except (TemplateError, json.JSONDecodeError) as e:
            self.logger.error(f"Error rendering upgrade template: {e}")
            return self._get_fallback_embed(item, "Item Upgraded")
    
    async def render_deletion_embed(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render Discord embed for item deletion."""
        try:
            template = self.env.get_template("deleted_item.j2")
            
            context = {
                "webhook_data": webhook_data,
                "config": self.config
            }
            
            rendered = template.render(context)
            return json.loads(rendered)
            
        except (TemplateError, json.JSONDecodeError) as e:
            self.logger.error(f"Error rendering deletion template: {e}")
            return self._get_fallback_deletion_embed(webhook_data)
    
    async def render_grouped_embed(self, items: List[Dict[str, Any]], group_type: str) -> Dict[str, Any]:
        """Render Discord embed for grouped notifications."""
        try:
            template_name = f"{group_type}_grouped.j2"
            template = self.env.get_template(template_name)
            
            context = {
                "items": items,
                "group_type": group_type,
                "count": len(items),
                "config": self.config
            }
            
            rendered = template.render(context)
            return json.loads(rendered)
            
        except (TemplateError, json.JSONDecodeError) as e:
            self.logger.error(f"Error rendering grouped template: {e}")
            return self._get_fallback_grouped_embed(items, group_type)
    
    def _get_fallback_embed(self, item: MediaItem, title: str) -> Dict[str, Any]:
        """Get fallback embed when template rendering fails."""
        return {
            "embeds": [{
                "title": f"🎬 {title}",
                "description": f"**{item.name}**\\n{item.type}",
                "color": 0x00D4AA,  # Jellyfin green
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "Jellynouncer"
                }
            }]
        }
    
    def _get_fallback_deletion_embed(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback embed for deletions."""
        return {
            "embeds": [{
                "title": "🗑️ Item Deleted",
                "description": f"**{webhook_data.get('Name', 'Unknown')}**",
                "color": 0xFF6B6B,  # Red
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "Jellynouncer"
                }
            }]
        }
    
    def _get_fallback_grouped_embed(self, items: List[Dict[str, Any]], group_type: str) -> Dict[str, Any]:
        """Get fallback embed for grouped notifications."""
        return {
            "embeds": [{
                "title": f"📚 {len(items)} {group_type.replace('_', ' ').title()}",
                "description": "Multiple items processed",
                "color": 0x5865F2,  # Discord blue
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "Jellynouncer"
                }
            }]
        }
    
    async def validate_template(self, template_name: str) -> Dict[str, Any]:
        """Validate a template with sample data."""
        try:
            template = self.env.get_template(template_name)
            
            # Create sample data based on template type
            if "new_item" in template_name:
                sample_data = self._get_sample_item_data()
                rendered = template.render(sample_data)
            elif "upgrade" in template_name:
                sample_data = self._get_sample_upgrade_data()
                rendered = template.render(sample_data)
            elif "delete" in template_name:
                sample_data = self._get_sample_deletion_data()
                rendered = template.render(sample_data)
            else:
                return {"valid": False, "error": "Unknown template type"}
            
            # Try to parse as JSON
            json.loads(rendered)
            
            return {"valid": True, "rendered": rendered}
            
        except TemplateError as e:
            return {"valid": False, "error": f"Template error: {e}"}
        except json.JSONDecodeError as e:
            return {"valid": False, "error": f"Invalid JSON output: {e}"}
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {e}"}
    
    def _get_sample_item_data(self) -> Dict[str, Any]:
        """Get sample data for testing item templates."""
        from src.services.jellyfin_api import MediaItem, MediaStream
        
        sample_item = MediaItem(
            id="sample-123",
            name="Sample Movie",
            type="Movie",
            path="/media/movies/Sample Movie (2024).mkv",
            size=2_500_000_000,  # 2.5GB
            year=2024,
            overview="This is a sample movie for testing templates.",
            genres=["Action", "Adventure"],
            streams=[
                MediaStream(codec="H265", type="Video", width=1920, height=1080),
                MediaStream(codec="AAC", type="Audio", channels=6)
            ]
        )
        
        return {
            "item": sample_item,
            "metadata": {
                "imdb_rating": "8.5",
                "poster_url": "https://example.com/poster.jpg"
            },
            "config": self.config
        }
    
    def _get_sample_upgrade_data(self) -> Dict[str, Any]:
        """Get sample data for testing upgrade templates."""
        sample_data = self._get_sample_item_data()
        
        from src.services.change_detector import DetectedChange
        sample_data["changes"] = {
            "resolution": DetectedChange("resolution", "1080p", "4K", True),
            "video_codec": DetectedChange("video_codec", "H264", "H265", True)
        }
        
        return sample_data
    
    def _get_sample_deletion_data(self) -> Dict[str, Any]:
        """Get sample data for testing deletion templates."""
        return {
            "webhook_data": {
                "Name": "Sample Movie",
                "ItemType": "Movie",
                "Year": 2024
            },
            "config": self.config
        }
    
    async def _create_default_templates(self):
        """Create default templates if they don't exist."""
        templates = {
            "new_item.j2": self._get_default_new_item_template(),
            "upgraded_item.j2": self._get_default_upgrade_template(),
            "deleted_item.j2": self._get_default_deletion_template(),
            "new_items_grouped.j2": self._get_default_grouped_template("new_items"),
            "upgraded_items_grouped.j2": self._get_default_grouped_template("upgraded_items")
        }
        
        for template_name, template_content in templates.items():
            template_path = self.template_dir / template_name
            if not template_path.exists():
                with open(template_path, 'w') as f:
                    f.write(template_content)
                self.logger.info(f"Created default template: {template_name}")
    
    def _get_default_new_item_template(self) -> str:
        """Get default new item template."""
        return '''{
  "embeds": [{
    "title": "🎬 New {{ item.type }} Added",
    "description": "**{{ item.name }}**{% if item.year %} ({{ item.year }}){% endif %}",
    "color": 6736947,
    "fields": [
      {% if item.overview %}
      {
        "name": "Overview",
        "value": "{{ item.overview | truncate_text(300) }}",
        "inline": false
      },
      {% endif %}
      {% if item.genres %}
      {
        "name": "Genre",
        "value": "{{ item.genres | join_with_limit }}",
        "inline": true
      },
      {% endif %}
      {% if item.resolution %}
      {
        "name": "Quality",
        "value": "{{ item.resolution }}{% if item.video_codec %} ({{ item.video_codec }}){% endif %}{% if item.has_hdr %} HDR{% endif %}",
        "inline": true
      },
      {% endif %}
      {% if item.runtime_ticks %}
      {
        "name": "Runtime",
        "value": "{{ item.runtime_ticks | format_runtime }}",
        "inline": true
      },
      {% endif %}
      {% if item.size %}
      {
        "name": "File Size",
        "value": "{{ item.size | format_file_size }}",
        "inline": true
      }
      {% endif %}
    ],
    {% if metadata.poster_url %}
    "thumbnail": {
      "url": "{{ metadata.poster_url }}"
    },
    {% endif %}
    "timestamp": "{{ now().isoformat() }}",
    "footer": {
      "text": "Jellynouncer"
    }
  }]
}'''
    
    def _get_default_upgrade_template(self) -> str:
        """Get default upgrade template."""
        return '''{
  "embeds": [{
    "title": "⬆️ {{ item.type }} Upgraded",
    "description": "**{{ item.name }}**{% if item.year %} ({{ item.year }}){% endif %}",
    "color": 3066993,
    "fields": [
      {
        "name": "Changes Detected",
        "value": "{% for change in changes.values() %}{{ format_change(change) }}\\n{% endfor %}",
        "inline": false
      },
      {% if item.resolution %}
      {
        "name": "Current Quality",
        "value": "{{ item.resolution }}{% if item.video_codec %} ({{ item.video_codec }}){% endif %}{% if item.has_hdr %} HDR{% endif %}",
        "inline": true
      },
      {% endif %}
      {% if item.size %}
      {
        "name": "File Size",
        "value": "{{ item.size | format_file_size }}",
        "inline": true
      }
      {% endif %}
    ],
    {% if metadata.poster_url %}
    "thumbnail": {
      "url": "{{ metadata.poster_url }}"
    },
    {% endif %}
    "timestamp": "{{ now().isoformat() }}",
    "footer": {
      "text": "Jellynouncer"
    }
  }]
}'''
    
    def _get_default_deletion_template(self) -> str:
        """Get default deletion template."""
        return '''{
  "embeds": [{
    "title": "🗑️ {{ webhook_data.ItemType }} Deleted",
    "description": "**{{ webhook_data.Name }}**{% if webhook_data.Year %} ({{ webhook_data.Year }}){% endif %}",
    "color": 15158332,
    "timestamp": "{{ now().isoformat() }}",
    "footer": {
      "text": "Jellynouncer"
    }
  }]
}'''
    
    def _get_default_grouped_template(self, group_type: str) -> str:
        """Get default grouped template."""
        icon = "🎬" if "new" in group_type else "⬆️"
        action = "Added" if "new" in group_type else "Upgraded"
        
        return f'''{{
  "embeds": [{{
    "title": "{icon} {{{{ count }}}} Items {action}",
    "description": "{% for item_data in items[:10] %}**{{{{ item_data.item.name }}}}**{% if item_data.item.year %} ({{{{ item_data.item.year }}}}){% endif %}\\n{% endfor %}{% if count > 10 %}... and {{{{ count - 10 }}}} more{% endif %}",
    "color": {"6736947" if "new" in group_type else "3066993"},
    "timestamp": "{{{{ now().isoformat() }}}}",
    "footer": {{
      "text": "Jellynouncer"
    }}
  }}]
}}'''