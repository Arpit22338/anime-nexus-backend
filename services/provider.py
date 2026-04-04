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
        Search for anime in the provider with strict title matching
        
        Args:
            query: Anime name to search
            language: 'sub' or 'dub'
            
        Returns:
            List of found anime with id and name, sorted by title similarity
        """
        if not self.provider:
            raise Exception("Provider not initialized - streaming service unavailable")
        
        try:
            lang_enum = LanguageTypeEnum.SUB if language == "sub" else LanguageTypeEnum.DUB
            all_results = []
            query_lower = query.lower().strip()
            
            # Hardcoded exact provider IDs for problematic anime
            # These bypass search entirely for known titles
            EXACT_PROVIDER_IDS = {
                "one piece": "one-piece",
                "naruto": "naruto",
                "naruto shippuden": "naruto-shippuden",
                "bleach": "bleach",
                "dragon ball z": "dragon-ball-z",
                "dragon ball": "dragon-ball",
                "attack on titan": "shingeki-no-kyojin",
                "shingeki no kyojin": "shingeki-no-kyojin",
                "demon slayer": "kimetsu-no-yaiba",
                "kimetsu no yaiba": "kimetsu-no-yaiba",
                "jujutsu kaisen": "jujutsu-kaisen",
                "my hero academia": "boku-no-hero-academia",
                "boku no hero academia": "boku-no-hero-academia",
                "hunter x hunter": "hunter-x-hunter-2011",
                "death note": "death-note",
                "fullmetal alchemist brotherhood": "fullmetal-alchemist-brotherhood",
                "one punch man": "one-punch-man",
                "spy x family": "spy-x-family",
                "chainsaw man": "chainsaw-man",
                "solo leveling": "ore-dake-level-up-na-ken",
                "ore dake level up na ken": "ore-dake-level-up-na-ken",
            }
            
            # Check for exact provider ID match first
            for title_key, provider_id in EXACT_PROVIDER_IDS.items():
                if title_key in query_lower or query_lower in title_key:
                    try:
                        eps = list(self.provider.get_episodes(provider_id, lang_enum))
                        if len(eps) > 0:
                            logger.info(f"Using hardcoded provider ID '{provider_id}' for query '{query}'")
                            return [{
                                "id": provider_id,
                                "name": query,
                                "languages": ["sub", "dub"]
                            }]
                    except Exception as e:
                        logger.warning(f"Hardcoded ID '{provider_id}' failed: {e}, falling back to search")
                    break
            
            # Fallback to search with strict filtering
            search_terms = [query]
            
            # Add Japanese title variations
            title_variations = {
                "one piece": ["ワンピース"],
                "naruto": ["ナルト"],
                "attack on titan": ["進撃の巨人", "Shingeki no Kyojin"],
                "demon slayer": ["鬼滅の刃", "Kimetsu no Yaiba"],
                "jujutsu kaisen": ["呪術廻戦"],
                "bleach": ["ブリーチ"],
                "hunter x hunter": ["ハンター×ハンター"],
                "death note": ["デスノート"],
                "one punch man": ["ワンパンマン"],
                "spy x family": ["スパイファミリー"],
            }
            
            for eng_title, variations in title_variations.items():
                if eng_title in query_lower:
                    search_terms.extend(variations)
                    break
            
            # Search and collect results
            seen_ids = set()
            for term in search_terms:
                try:
                    results = list(self.provider.get_search(term, Filters()))
                    for anime in results:
                        if anime.identifier not in seen_ids:
                            seen_ids.add(anime.identifier)
                            
                            name_lower = anime.name.lower()
                            similarity = self._calculate_similarity(query_lower, name_lower)
                            
                            # STRICT FILTER: Only include results with similarity > 0
                            # This filters out completely unrelated anime
                            if similarity > 0:
                                # Get episode count for sorting
                                try:
                                    eps = list(self.provider.get_episodes(anime.identifier, lang_enum))
                                    ep_count = len(eps)
                                except:
                                    ep_count = 0
                                
                                all_results.append({
                                    "id": anime.identifier,
                                    "name": anime.name,
                                    "languages": [str(lang) for lang in anime.languages] if hasattr(anime, 'languages') else ["sub"],
                                    "episode_count": ep_count,
                                    "similarity": similarity
                                })
                except Exception as e:
                    logger.warning(f"Search term '{term}' failed: {e}")
                    continue
            
            # Sort by similarity (highest first), then episode count as tiebreaker
            all_results.sort(key=lambda x: (-x.get("similarity", 0), -x.get("episode_count", 0)))
            
            # Log top result for debugging
            if all_results:
                logger.info(f"Query '{query}' -> Top match: '{all_results[0]['name']}' (similarity: {all_results[0].get('similarity', 0)})")
            
            # Remove internal fields
            for r in all_results:
                r.pop("episode_count", None)
                r.pop("similarity", None)
            
            return all_results[:15]
            
        except Exception as e:
            logger.error(f"Provider search failed: {e}")
            return []
    
    def _calculate_similarity(self, query: str, name: str) -> float:
        """
        Calculate strict similarity score between query and anime name.
        Returns 0 for completely unrelated titles (filters them out).
        """
        query = query.lower().strip()
        name = name.lower().strip()
        
        # Normalize common variations
        query_norm = self._normalize_title(query)
        name_norm = self._normalize_title(name)
        
        # Exact match (after normalization)
        if query_norm == name_norm:
            return 100
        
        # Query is fully contained in name (e.g., "one piece" in "one piece film red")
        if query_norm in name_norm:
            # Bonus for shorter names (more specific)
            length_ratio = len(query_norm) / len(name_norm)
            return 85 + (length_ratio * 10)
        
        # Name is fully contained in query
        if name_norm in query_norm:
            length_ratio = len(name_norm) / len(query_norm)
            return 75 + (length_ratio * 10)
        
        # Word-based matching
        query_words = set(query_norm.split())
        name_words = set(name_norm.split())
        
        # All query words must appear in name for a match
        if query_words.issubset(name_words):
            return 70 + (len(query_words) / len(name_words)) * 20
        
        # Check significant word overlap (at least 50% of query words)
        common_words = query_words & name_words
        if common_words:
            overlap_ratio = len(common_words) / len(query_words)
            if overlap_ratio >= 0.5:
                return 40 + (overlap_ratio * 30)
        
        # No meaningful match - return 0 to filter this result out
        return 0
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison by removing common variations"""
        import re
        title = title.lower().strip()
        # Remove common suffixes/prefixes
        title = re.sub(r'\s*(season|part|cour)\s*\d+', '', title)
        title = re.sub(r'\s*\d+(st|nd|rd|th)\s*season', '', title)
        # Remove special characters but keep spaces
        title = re.sub(r'[^\w\s]', '', title)
        # Normalize whitespace
        title = ' '.join(title.split())
        return title
    
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
            
            if not streams or len(streams) == 0:
                raise ValueError(f"No streams found for episode {episode_number}")
            
            # Get best quality stream (first one is usually best)
            stream = streams[0]
            
            # Check if stream object has required attributes
            if not hasattr(stream, 'url') or not stream.url:
                raise ValueError(f"Stream URL not available for episode {episode_number}")
                
            return {
                "url": stream.url,
                "referrer": getattr(stream, 'referrer', 'https://allanime.day'),
                "resolution": getattr(stream, 'resolution', 1080)
            }
                
        except Exception as e:
            logger.error(f"Failed to get stream URL: {e}")
            raise


# Global provider instance (initialized once)
provider_service = ProviderService()
