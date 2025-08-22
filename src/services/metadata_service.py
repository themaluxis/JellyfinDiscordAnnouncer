"""
External metadata service for enriching media information.
Integrates with OMDb, TMDb, and TVDb APIs.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
import json
from pathlib import Path

from src.core.config import Config, ExternalApiConfig
from src.services.jellyfin_api import MediaItem


class MetadataCache:
    """Simple file-based cache for metadata."""
    
    def __init__(self, cache_dir: Path, cache_duration_hours: int = 24):
        self.cache_dir = cache_dir
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.logger = logging.getLogger(__name__)
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for key."""
        # Sanitize key for filename
        safe_key = "".join(c for c in cache_key if c.isalnum() or c in "._-")
        return self.cache_dir / f"{safe_key}.json"
    
    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached data if not expired."""
        try:
            cache_path = self._get_cache_path(cache_key)
            
            if not cache_path.exists():
                return None
            
            # Check if cache is expired
            cache_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
            if datetime.now() - cache_time > self.cache_duration:
                cache_path.unlink()  # Remove expired cache
                return None
            
            with open(cache_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.warning(f"Error reading cache for {cache_key}: {e}")
            return None
    
    async def set(self, cache_key: str, data: Dict[str, Any]):
        """Cache data."""
        try:
            cache_path = self._get_cache_path(cache_key)
            
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Error writing cache for {cache_key}: {e}")


class OMDbClient:
    """OMDb API client."""
    
    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.base_url = "http://www.omdbapi.com/"
        self.client = httpx.AsyncClient(timeout=timeout)
        self.logger = logging.getLogger(__name__)
    
    async def get_by_imdb_id(self, imdb_id: str) -> Optional[Dict[str, Any]]:
        """Get movie/show info by IMDb ID."""
        try:
            params = {
                "apikey": self.api_key,
                "i": imdb_id,
                "plot": "full"
            }
            
            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("Response") == "True":
                return {
                    "imdb_rating": data.get("imdbRating"),
                    "metascore": data.get("Metascore"),
                    "rotten_tomatoes": self._extract_rt_score(data.get("Ratings", [])),
                    "plot": data.get("Plot"),
                    "awards": data.get("Awards"),
                    "poster_url": data.get("Poster") if data.get("Poster") != "N/A" else None
                }
            else:
                self.logger.warning(f"OMDb API error for {imdb_id}: {data.get('Error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching OMDb data for {imdb_id}: {e}")
            return None
    
    def _extract_rt_score(self, ratings: list) -> Optional[str]:
        """Extract Rotten Tomatoes score from ratings."""
        for rating in ratings:
            if rating.get("Source") == "Rotten Tomatoes":
                return rating.get("Value")
        return None
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class TMDbClient:
    """TMDb API client."""
    
    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.client = httpx.AsyncClient(timeout=timeout)
        self.logger = logging.getLogger(__name__)
    
    async def get_movie(self, tmdb_id: str) -> Optional[Dict[str, Any]]:
        """Get movie info by TMDb ID."""
        try:
            url = f"{self.base_url}/movie/{tmdb_id}"
            params = {"api_key": self.api_key}
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "tmdb_rating": data.get("vote_average"),
                "tmdb_votes": data.get("vote_count"),
                "popularity": data.get("popularity"),
                "poster_url": self._get_poster_url(data.get("poster_path")),
                "backdrop_url": self._get_backdrop_url(data.get("backdrop_path")),
                "tagline": data.get("tagline"),
                "budget": data.get("budget"),
                "revenue": data.get("revenue")
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching TMDb movie data for {tmdb_id}: {e}")
            return None
    
    async def get_tv_show(self, tmdb_id: str) -> Optional[Dict[str, Any]]:
        """Get TV show info by TMDb ID."""
        try:
            url = f"{self.base_url}/tv/{tmdb_id}"
            params = {"api_key": self.api_key}
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "tmdb_rating": data.get("vote_average"),
                "tmdb_votes": data.get("vote_count"),
                "popularity": data.get("popularity"),
                "poster_url": self._get_poster_url(data.get("poster_path")),
                "backdrop_url": self._get_backdrop_url(data.get("backdrop_path")),
                "tagline": data.get("tagline"),
                "seasons": data.get("number_of_seasons"),
                "episodes": data.get("number_of_episodes"),
                "status": data.get("status")
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching TMDb TV data for {tmdb_id}: {e}")
            return None
    
    def _get_poster_url(self, poster_path: Optional[str]) -> Optional[str]:
        """Get full poster URL."""
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"
        return None
    
    def _get_backdrop_url(self, backdrop_path: Optional[str]) -> Optional[str]:
        """Get full backdrop URL."""
        if backdrop_path:
            return f"https://image.tmdb.org/t/p/w1280{backdrop_path}"
        return None
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class TVDbClient:
    """TVDb API client."""
    
    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.base_url = "https://api4.thetvdb.com/v4"
        self.client = httpx.AsyncClient(timeout=timeout)
        self.logger = logging.getLogger(__name__)
        self.token = None
        self.token_expires = None
    
    async def _get_token(self) -> bool:
        """Get authentication token."""
        try:
            if self.token and self.token_expires and datetime.now() < self.token_expires:
                return True
            
            url = f"{self.base_url}/login"
            data = {"apikey": self.api_key}
            
            response = await self.client.post(url, json=data)
            response.raise_for_status()
            
            result = response.json()
            self.token = result["data"]["token"]
            self.token_expires = datetime.now() + timedelta(hours=23)  # Token valid for 24h
            
            # Update authorization header
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error getting TVDb token: {e}")
            return False
    
    async def get_series(self, tvdb_id: str) -> Optional[Dict[str, Any]]:
        """Get TV series info by TVDb ID."""
        try:
            if not await self._get_token():
                return None
            
            url = f"{self.base_url}/series/{tvdb_id}/extended"
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()["data"]
            
            return {
                "tvdb_rating": data.get("score"),
                "status": data.get("status", {}).get("name"),
                "network": data.get("originalNetwork", {}).get("name"),
                "country": data.get("originalCountry"),
                "first_aired": data.get("firstAired"),
                "last_aired": data.get("lastAired"),
                "poster_url": self._get_image_url(data.get("image")),
                "fanart_url": self._get_fanart_url(data.get("artworks", []))
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching TVDb data for {tvdb_id}: {e}")
            return None
    
    def _get_image_url(self, image_path: Optional[str]) -> Optional[str]:
        """Get full image URL."""
        if image_path:
            return f"https://artworks.thetvdb.com{image_path}"
        return None
    
    def _get_fanart_url(self, artworks: list) -> Optional[str]:
        """Get fanart URL from artworks."""
        for artwork in artworks:
            if artwork.get("type") == 3:  # Fanart type
                return f"https://artworks.thetvdb.com{artwork.get('image')}"
        return None
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class MetadataService:
    """Main metadata service."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize cache
        cache_dir = config.data_dir / "metadata_cache"
        self.cache = MetadataCache(cache_dir, config.external_apis.cache_duration_hours)
        
        # Initialize API clients
        self.omdb_client = None
        self.tmdb_client = None
        self.tvdb_client = None
        
        if config.external_apis.omdb_api_key:
            self.omdb_client = OMDbClient(
                config.external_apis.omdb_api_key,
                config.external_apis.timeout
            )
        
        if config.external_apis.tmdb_api_key:
            self.tmdb_client = TMDbClient(
                config.external_apis.tmdb_api_key,
                config.external_apis.timeout
            )
        
        if config.external_apis.tvdb_api_key:
            self.tvdb_client = TVDbClient(
                config.external_apis.tvdb_api_key,
                config.external_apis.timeout
            )
    
    async def get_metadata(self, item: MediaItem) -> Dict[str, Any]:
        """
        Get enriched metadata for media item.
        
        Args:
            item: MediaItem to enrich
            
        Returns:
            Dictionary with enriched metadata
        """
        cache_key = f"{item.type}_{item.id}"
        
        # Try cache first
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            self.logger.debug(f"Using cached metadata for {item.name}")
            return cached_data
        
        metadata = {}
        
        try:
            # Gather metadata from different sources
            if item.type in ["Movie", "Series", "Episode"]:
                if item.imdb_id and self.omdb_client:
                    omdb_data = await self.omdb_client.get_by_imdb_id(item.imdb_id)
                    if omdb_data:
                        metadata.update(omdb_data)
                
                if item.tmdb_id and self.tmdb_client:
                    if item.type == "Movie":
                        tmdb_data = await self.tmdb_client.get_movie(item.tmdb_id)
                    else:
                        tmdb_data = await self.tmdb_client.get_tv_show(item.tmdb_id)
                    
                    if tmdb_data:
                        metadata.update(tmdb_data)
                
                if item.tvdb_id and self.tvdb_client and item.type in ["Series", "Episode"]:
                    tvdb_data = await self.tvdb_client.get_series(item.tvdb_id)
                    if tvdb_data:
                        metadata.update(tvdb_data)
            
            # Cache the result
            if metadata:
                await self.cache.set(cache_key, metadata)
                self.logger.debug(f"Cached metadata for {item.name}")
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error getting metadata for {item.name}: {e}")
            return {}
    
    async def get_poster_url(self, item: MediaItem) -> Optional[str]:
        """Get the best available poster URL for an item."""
        metadata = await self.get_metadata(item)
        
        # Priority: TMDb > OMDb > TVDb
        return (
            metadata.get("poster_url") or
            metadata.get("tmdb_poster_url") or
            metadata.get("omdb_poster_url") or
            metadata.get("tvdb_poster_url")
        )
    
    async def test_connections(self) -> Dict[str, bool]:
        """Test connections to all configured APIs."""
        results = {}
        
        if self.omdb_client:
            try:
                # Test with a known IMDb ID (The Shawshank Redemption)
                result = await self.omdb_client.get_by_imdb_id("tt0111161")
                results["omdb"] = result is not None
            except:
                results["omdb"] = False
        
        if self.tmdb_client:
            try:
                # Test with a known TMDb ID (The Shawshank Redemption)
                result = await self.tmdb_client.get_movie("278")
                results["tmdb"] = result is not None
            except:
                results["tmdb"] = False
        
        if self.tvdb_client:
            try:
                # Test with a known TVDb ID (Breaking Bad)
                result = await self.tvdb_client.get_series("81189")
                results["tvdb"] = result is not None
            except:
                results["tvdb"] = False
        
        return results
    
    async def close(self):
        """Close all API clients."""
        if self.omdb_client:
            await self.omdb_client.close()
        if self.tmdb_client:
            await self.tmdb_client.close()
        if self.tvdb_client:
            await self.tvdb_client.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()