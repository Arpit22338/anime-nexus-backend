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
        Search for anime in the provider with smart matching
        
        Args:
            query: Anime name to search
            language: 'sub' or 'dub' (not used in new API but kept for compatibility)
            
        Returns:
            List of found anime with id and name, sorted by episode count (main series first)
        """
        if not self.provider:
            raise Exception("Provider not initialized - streaming service unavailable")
        
        try:
            lang_enum = LanguageTypeEnum.SUB if language == "sub" else LanguageTypeEnum.DUB
            all_results = []
            
            # Try multiple search variations
            search_terms = [query]
            
            # Add Japanese title variations for common anime
            title_map = {
                "one piece": ["ワンピース", "1P"],
                "naruto": ["ナルト", "NARUTO"],
                "naruto shippuden": ["ナルト 疾風伝", "Naruto Shippuuden"],
                "dragon ball": ["ドラゴンボール"],
                "dragon ball z": ["ドラゴンボールZ", "DBZ"],
                "attack on titan": ["進撃の巨人", "Shingeki no Kyojin"],
                "demon slayer": ["鬼滅の刃", "Kimetsu no Yaiba"],
                "my hero academia": ["僕のヒーローアカデミア", "Boku no Hero Academia"],
                "jujutsu kaisen": ["呪術廻戦"],
                "bleach": ["ブリーチ", "BLEACH"],
                "hunter x hunter": ["ハンター×ハンター", "HxH"],
                "fullmetal alchemist": ["鋼の錬金術師"],
                "death note": ["デスノート"],
                "one punch man": ["ワンパンマン"],
                "spy x family": ["スパイファミリー", "SPY×FAMILY"],
            }
            
            # Check if query matches any known titles
            query_lower = query.lower().strip()
            for eng_title, variations in title_map.items():
                if eng_title in query_lower or query_lower in eng_title:
                    search_terms.extend(variations)
                    break
            
            # Search all terms and collect results
            seen_ids = set()
            for term in search_terms:
                try:
                    results = list(self.provider.get_search(term, Filters()))
                    for anime in results:
                        if anime.identifier not in seen_ids:
                            seen_ids.add(anime.identifier)
                            # Get episode count to help sort
                            try:
                                eps = list(self.provider.get_episodes(anime.identifier, lang_enum))
                                ep_count = len(eps)
                            except:
                                ep_count = 0
                            all_results.append({
                                "id": anime.identifier,
                                "name": anime.name,
                                "languages": [str(lang) for lang in anime.languages] if hasattr(anime, 'languages') else ["sub"],
                                "episode_count": ep_count
                            })
                except Exception as e:
                    logger.warning(f"Search term '{term}' failed: {e}")
                    continue
            
            # Sort by episode count (main series usually has most episodes)
            all_results.sort(key=lambda x: x.get("episode_count", 0), reverse=True)
            
            # Remove episode_count from final output (internal use only)
            for r in all_results:
                r.pop("episode_count", None)
            
            return all_results[:15]
            
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
    
    def get_stream_url(self, anime_id: str, episode_number: int, language: str = "sub") -> dict:
        """
        Get stream URL for a specific episode
        
        Args:
            anime_id: Provider's anime identifier
            episode_number: Episode number (1-indexed)
            language: 'sub' or 'dub'
            
        Returns:
            Dict with url, referrer, and resolution
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
            return {
                "url": stream.url,
                "referrer": stream.referrer,
                "resolution": stream.resolution
            }
                
        except Exception as e:
            logger.error(f"Failed to get stream URL: {e}")
            raise


# Global provider instance (initialized once)
provider_service = ProviderService()
