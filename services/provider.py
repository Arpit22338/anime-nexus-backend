"""
Anime Provider Service using anipy-api
Handles streaming provider integration
"""
from typing import List, Dict, Optional
from anipy_api.provider import list_providers, get_provider, LanguageTypeEnum
from anipy_api.anime import Anime
import logging

logger = logging.getLogger(__name__)


class ProviderService:
    """Service for anime streaming providers via anipy-api"""
    
    def __init__(self):
        self.provider = None
        self.provider_name = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the streaming provider"""
        try:
            available_providers = list(list_providers())
            
            if not available_providers:
                logger.error("No streaming providers available")
                return  # Don't crash, just log
            
            # Use first available provider
            self.provider_name = available_providers[0]
            provider_class = get_provider(self.provider_name)
            
            if provider_class is None:
                logger.error(f"Could not load provider: {self.provider_name}")
                return  # Don't crash, just log
            
            self.provider = provider_class()
            logger.info(f"✅ Successfully initialized provider: {self.provider_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize provider: {e}")
            # Don't raise - let the app start even if provider fails
            logger.warning("App will start but streaming features will be unavailable")
    
    def search_anime(self, query: str, language: str = "sub") -> List[Dict]:
        """
        Search for anime in the provider
        
        Args:
            query: Anime name to search
            language: 'sub' or 'dub'
            
        Returns:
            List of found anime with id and name
        """
        if not self.provider:
            raise Exception("Provider not initialized - streaming service unavailable")
        
        try:
            lang_enum = LanguageTypeEnum.SUB if language == "sub" else LanguageTypeEnum.DUB
            results = self.provider.get_search(query, lang_enum)
            
            return [
                {
                    "id": anime.identifier,
                    "name": anime.name,
                    "languages": [str(lang) for lang in anime.languages]
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
            List of episodes with number and id
        """
        if not self.provider:
            raise Exception("Provider not initialized - streaming service unavailable")
        
        try:
            lang_enum = LanguageTypeEnum.SUB if language == "sub" else LanguageTypeEnum.DUB
            episodes = self.provider.get_episodes(anime_id, lang_enum)
            
            return [
                {
                    "number": idx + 1,
                    "id": ep.identifier
                }
                for idx, ep in enumerate(episodes)
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
            # Get episodes list first
            episodes = self.get_episodes(anime_id, language)
            
            if episode_number < 1 or episode_number > len(episodes):
                raise ValueError(f"Invalid episode number: {episode_number}")
            
            # Get the specific episode
            lang_enum = LanguageTypeEnum.SUB if language == "sub" else LanguageTypeEnum.DUB
            episodes_list = self.provider.get_episodes(anime_id, lang_enum)
            episode = episodes_list[episode_number - 1]
            
            # Get stream
            stream = self.provider.get_video(episode)
            
            # Extract URL (anipy-api returns different objects depending on provider)
            if hasattr(stream, 'url'):
                return stream.url
            elif hasattr(stream, 'stream_url'):
                return stream.stream_url
            else:
                return str(stream)
                
        except Exception as e:
            logger.error(f"Failed to get stream URL: {e}")
            raise


# Global provider instance (initialized once)
provider_service = ProviderService()
