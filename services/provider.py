"""
Anime Provider Service using anipy-api
Handles streaming provider integration
"""
from typing import List, Dict, Optional
from anipy_api.provider import Filters, LanguageTypeEnum
# Direct imports - get_provider() is broken in anipy-api 3.8.4
from anipy_api.provider.providers.allanime_provider import AllAnimeProvider
import logging

logger = logging.getLogger(__name__)


class ProviderService:
    """Service for anime streaming providers via anipy-api"""
    
    def __init__(self):
        self.provider = None
        self.provider_name = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the streaming provider using direct imports"""
        try:
            logger.info("Initializing AllAnime provider...")
            self.provider = AllAnimeProvider()
            self.provider_name = "allanime"
            logger.info(f"✅ Successfully initialized provider: allanime")
        except Exception as e:
            logger.error(f"❌ Failed to initialize provider: {e}")
            logger.warning("App will start but streaming features will be unavailable")
    
    def search_anime(self, query: str, language: str = "sub") -> List[Dict]:
        """
        Search for anime in the provider
        
        Args:
            query: Anime name to search
            language: 'sub' or 'dub' (not used in new API but kept for compatibility)
            
        Returns:
            List of found anime with id and name
        """
        if not self.provider:
            raise Exception("Provider not initialized - streaming service unavailable")
        
        try:
            # New API uses Filters() instead of LanguageTypeEnum
            results = list(self.provider.get_search(query, Filters()))
            
            return [
                {
                    "id": anime.identifier,
                    "name": anime.name,
                    "languages": [str(lang) for lang in anime.languages] if hasattr(anime, 'languages') else ["sub"]
                }
                for anime in results[:10]
            ]
        except Exception as e:
            logger.error(f"Provider search failed: {e}")
            return []
    
    def get_episodes(self, anime_id: str, language: str = "sub") -> List[Dict]:
        """
        Get episode list for an anime
        
        Args:
            anime_id: Provider's anime identifier
            language: 'sub' or 'dub'
            
        Returns:
            List of episodes with number
        """
        if not self.provider:
            raise Exception("Provider not initialized - streaming service unavailable")
        
        try:
            lang_enum = LanguageTypeEnum.SUB if language == "sub" else LanguageTypeEnum.DUB
            episodes = list(self.provider.get_episodes(anime_id, lang_enum))
            
            # Episodes are just integers (episode numbers) in new API
            return [
                {
                    "number": ep,
                    "id": str(ep)
                }
                for ep in episodes
            ]
        except Exception as e:
            logger.error(f"Failed to get episodes: {e}")
            raise
    
    def get_stream_url(self, anime_id: str, episode_number: int, language: str = "sub") -> Optional[str]:
        """
        Get stream URL for a specific episode
        
        Args:
            anime_id: Provider's anime identifier
            episode_number: Episode number (1-indexed)
            language: 'sub' or 'dub'
            
        Returns:
            Stream URL string
        """
        if not self.provider:
            raise Exception("Provider not initialized - streaming service unavailable")
        
        try:
            lang_enum = LanguageTypeEnum.SUB if language == "sub" else LanguageTypeEnum.DUB
            
            # New API: get_video(anime_id, episode_number, language) returns list of ProviderStream
            streams = self.provider.get_video(anime_id, episode_number, lang_enum)
            
            if not streams:
                raise ValueError(f"No streams found for episode {episode_number}")
            
            # Get best quality stream (first one is usually best)
            stream = streams[0]
            return stream.url
                
        except Exception as e:
            logger.error(f"Failed to get stream URL: {e}")
            raise


# Global provider instance (initialized once)
provider_service = ProviderService()
