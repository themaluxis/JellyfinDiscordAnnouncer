"""
Jellyfin API client for retrieving media information.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import httpx
from dataclasses import dataclass

from src.core.config import JellyfinConfig


@dataclass
class MediaStream:
    """Media stream information."""
    codec: Optional[str] = None
    language: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None  # Video, Audio, Subtitle
    width: Optional[int] = None
    height: Optional[int] = None
    channels: Optional[int] = None
    bit_rate: Optional[int] = None
    video_range: Optional[str] = None  # SDR, HDR


@dataclass 
class MediaItem:
    """Jellyfin media item representation."""
    id: str
    name: str
    type: str  # Movie, Series, Episode, Audio, etc.
    path: str
    size: Optional[int] = None
    date_created: Optional[str] = None
    date_modified: Optional[str] = None
    
    # Media metadata
    overview: Optional[str] = None
    year: Optional[int] = None
    runtime_ticks: Optional[int] = None
    genres: List[str] = None
    
    # Series/Episode specific
    series_name: Optional[str] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    
    # Technical info
    streams: List[MediaStream] = None
    
    # External IDs
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    
    def __post_init__(self):
        if self.genres is None:
            self.genres = []
        if self.streams is None:
            self.streams = []
    
    @property
    def resolution(self) -> Optional[str]:
        """Get video resolution."""
        for stream in self.streams:
            if stream.type == "Video" and stream.width and stream.height:
                if stream.width >= 3840:
                    return "4K"
                elif stream.width >= 1920:
                    return "1080p"
                elif stream.width >= 1280:
                    return "720p"
                else:
                    return f"{stream.width}x{stream.height}"
        return None
    
    @property
    def video_codec(self) -> Optional[str]:
        """Get video codec."""
        for stream in self.streams:
            if stream.type == "Video" and stream.codec:
                return stream.codec.upper()
        return None
    
    @property
    def audio_codec(self) -> Optional[str]:
        """Get primary audio codec."""
        for stream in self.streams:
            if stream.type == "Audio" and stream.codec:
                return stream.codec.upper()
        return None
    
    @property
    def has_hdr(self) -> bool:
        """Check if video has HDR."""
        for stream in self.streams:
            if stream.type == "Video" and stream.video_range:
                return "HDR" in stream.video_range.upper()
        return False
    
    @property
    def audio_channels(self) -> Optional[str]:
        """Get audio channel configuration."""
        max_channels = 0
        for stream in self.streams:
            if stream.type == "Audio" and stream.channels:
                max_channels = max(max_channels, stream.channels)
        
        if max_channels >= 8:
            return "7.1"
        elif max_channels >= 6:
            return "5.1"
        elif max_channels >= 2:
            return "Stereo"
        elif max_channels == 1:
            return "Mono"
        return None
    
    def get_quality_hash(self) -> str:
        """Generate hash for quality comparison."""
        import hashlib
        quality_data = f"{self.resolution}|{self.video_codec}|{self.audio_codec}|{self.has_hdr}|{self.audio_channels}"
        return hashlib.md5(quality_data.encode()).hexdigest()


class JellyfinAPI:
    """Jellyfin API client."""
    
    def __init__(self, config: JellyfinConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.client = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "X-Emby-Authorization": f'MediaBrowser Token="{self.config.api_key}"',
                "Content-Type": "application/json"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def get_item(self, item_id: str) -> Optional[MediaItem]:
        """
        Get detailed item information from Jellyfin.
        
        Args:
            item_id: Jellyfin item ID
            
        Returns:
            MediaItem object or None if not found
        """
        try:
            url = f"{self.config.server_url}/Users/{self.config.user_id}/Items/{item_id}"
            params = {
                "Fields": "Path,MediaStreams,ProviderIds,Overview,Genres,Runtime",
                "EnableUserData": "false"
            }
            
            self.logger.debug(f"Fetching item {item_id} from Jellyfin")
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_item(data)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self.logger.warning(f"Item {item_id} not found in Jellyfin")
                return None
            else:
                self.logger.error(f"HTTP error fetching item {item_id}: {e}")
                raise
        except Exception as e:
            self.logger.error(f"Error fetching item {item_id}: {e}")
            raise
    
    async def get_library_items(self, library_id: Optional[str] = None) -> List[MediaItem]:
        """
        Get all items from a library or all libraries.
        
        Args:
            library_id: Optional library ID to filter by
            
        Returns:
            List of MediaItem objects
        """
        try:
            url = f"{self.config.server_url}/Users/{self.config.user_id}/Items"
            params = {
                "Recursive": "true",
                "Fields": "Path,MediaStreams,ProviderIds,Overview,Genres,Runtime",
                "IncludeItemTypes": "Movie,Series,Episode,Audio,MusicAlbum",
                "EnableUserData": "false"
            }
            
            if library_id:
                params["ParentId"] = library_id
            
            self.logger.debug(f"Fetching library items from Jellyfin")
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = []
            
            for item_data in data.get("Items", []):
                item = self._parse_item(item_data)
                if item:
                    items.append(item)
            
            self.logger.info(f"Retrieved {len(items)} items from library")
            return items
            
        except Exception as e:
            self.logger.error(f"Error fetching library items: {e}")
            raise
    
    def _parse_item(self, data: Dict[str, Any]) -> Optional[MediaItem]:
        """
        Parse Jellyfin item data into MediaItem.
        
        Args:
            data: Raw Jellyfin item data
            
        Returns:
            MediaItem object or None if parsing fails
        """
        try:
            # Parse media streams
            streams = []
            for stream_data in data.get("MediaStreams", []):
                stream = MediaStream(
                    codec=stream_data.get("Codec"),
                    language=stream_data.get("Language"),
                    title=stream_data.get("Title"),
                    type=stream_data.get("Type"),
                    width=stream_data.get("Width"),
                    height=stream_data.get("Height"),
                    channels=stream_data.get("Channels"),
                    bit_rate=stream_data.get("BitRate"),
                    video_range=stream_data.get("VideoRange")
                )
                streams.append(stream)
            
            # Parse external IDs
            provider_ids = data.get("ProviderIds", {})
            
            # Create MediaItem
            item = MediaItem(
                id=data["Id"],
                name=data["Name"],
                type=data["Type"],
                path=data.get("Path", ""),
                size=data.get("Size"),
                date_created=data.get("DateCreated"),
                date_modified=data.get("DateModified"),
                overview=data.get("Overview"),
                year=data.get("ProductionYear"),
                runtime_ticks=data.get("RunTimeTicks"),
                genres=data.get("Genres", []),
                series_name=data.get("SeriesName"),
                season_number=data.get("ParentIndexNumber"),
                episode_number=data.get("IndexNumber"),
                streams=streams,
                imdb_id=provider_ids.get("Imdb"),
                tmdb_id=provider_ids.get("Tmdb"),
                tvdb_id=provider_ids.get("Tvdb")
            )
            
            return item
            
        except KeyError as e:
            self.logger.error(f"Missing required field in item data: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing item data: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """
        Test connection to Jellyfin server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            url = f"{self.config.server_url}/System/Info"
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            server_name = data.get("ServerName", "Unknown")
            version = data.get("Version", "Unknown")
            
            self.logger.info(f"Connected to Jellyfin server: {server_name} v{version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Jellyfin server: {e}")
            return False