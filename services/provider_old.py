"""
Anime Provider Service using anipy-api
Handles streaming provider integration with caching for performance
"""
from typing import List, Dict, Optional
from anipy_api.provider import Filters, LanguageTypeEnum
from anipy_api.provider.providers.allanime_provider import AllAnimeProvider
import logging
import time
import re

logger = logging.getLogger(__name__)

# ============================================================================
# ANILIST ID -> PROVIDER ID MAPPING (Instant lookup, no search needed)
# ============================================================================
ANILIST_TO_PROVIDER = {
    # Major Shonen
    21: "ReooPAxPMsHM4KPMY",       # One Piece
    20: "cstcbG4EquLyDnAwN",       # Naruto
    1735: "vDTSJHSpYnrkZnAvG",     # Naruto Shippuden
    269: "XqKvkSEty5koms32i",      # Bleach
    170998: "uP4dqHNypYeYtTnzP",   # Bleach: TYBW
    11061: "mqT9iNNwP6xBLbc6G",    # Hunter x Hunter (2011)
    1535: "RezHft5pjutwWcE3B",     # Death Note
    16498: "wbnpCxPu3fyk9XSaZ",    # Attack on Titan S1
    101922: "gvwLtiYciaenJRoFy",   # Demon Slayer S1
    113415: "JNqf7LSYsHLDgHE7P",   # Hell's Paradise (Jigokuraku)
    145064: "SJms742bSTrcyJZay",   # Demon Slayer S2
    127230: "8Ti9Lnd3gW7TgeCXj",   # Jujutsu Kaisen
    
    # Modern Popular
    21459: "gKwRaeqdMMkgmCLZw",    # My Hero Academia S1
    131681: "osGHAaTHeoTZLTs4o",   # Chainsaw Man
    140960: "LGPNPnjSRKx8TqkGq",   # Spy x Family
    30276: "8sB7F65RGSQ3dMjYa",    # One Punch Man
    21087: "8sB7F65RGSQ3dMjYa",    # One Punch Man (alt ID)
    151807: "B6AMhLy6EQHDgYgBF",   # Solo Leveling
    
    # Trending/Popular
    154587: "ReHMC7TQnch3C6z8j",   # Sousou no Frieren
    182255: "ReHMC7TQnch3C6z8j",   # Frieren S2 (same provider)
    20665: "tWvYfivmWmYh8yo9X",    # Your Lie in April
    98659: "N4PxPNBZ94b3BbTja",    # Classroom of Elite
    101921: "JHCtsyQDXk4cbZni5",   # Fire Force S1
    179062: "JHCtsyQDXk4cbZni5",   # Fire Force S3
    139630: "b3u5TprKSKHBPBcor",   # Oshi no Ko
    182587: "b3u5TprKSKHBPBcor",   # Oshi no Ko S3
    162669: "QLc78PZcyyh3CiCvf",   # To Your Eternity S3
    114535: "QLc78PZcyyh3CiCvf",   # To Your Eternity S1
    
    # Classics
    5114: "yLCKvGbhA6buygXad",     # FMA Brotherhood
    1: "C3sJfKrswsD2CaQXs",        # Cowboy Bebop
    6: "sEYpMHcYB5jXjW5rG",        # Trigun
    19: "TFPbLSqS8RBWwPYyM",       # Monster
    
    # Dragon Ball
    813: "GqvGnNoyj3rML2WMf",      # Dragon Ball Z (Kai)
    20474: "dw453BcS22oy8SKGx",    # Dragon Ball Kai 2014
    
    # Popular Ongoing/Recent
    21519: "gKwRaeqdMMkgmCLZw",    # MHA alternate
    104578: "jaJdELAe23ieuzqXb",   # Vinland Saga
    101759: "RJgTXs5Bv9nhQqHHM",   # Dororo
    110277: "gPZdPDi7QxAhHb4Fg",   # Mob Psycho 100
    97986: "sGF5XZmb4yBCgvbWf",    # Boruto
    114745: "T8sRYJAGJjbKTFQER",   # Ranking of Kings
    105333: "RXqaJYhzDNGbjS5aP",   # Dr. Stone
    97940: "wn3B4v55q4Bb2P9GZ",    # Black Clover
    100166: "gqgoX5eRhxKemyGtG",   # Konosuba
}

# Title-based lookup (fallback when AniList ID not mapped)
TITLE_TO_PROVIDER = {
    "one piece": "ReooPAxPMsHM4KPMY",
    "naruto": "cstcbG4EquLyDnAwN",
    "naruto shippuden": "vDTSJHSpYnrkZnAvG",
    "naruto shippuuden": "vDTSJHSpYnrkZnAvG",
    "bleach": "XqKvkSEty5koms32i",
    "bleach thousand year blood war": "uP4dqHNypYeYtTnzP",
    "dragon ball z": "GqvGnNoyj3rML2WMf",
    "dragon ball kai": "GqvGnNoyj3rML2WMf",
    "attack on titan": "wbnpCxPu3fyk9XSaZ",
    "shingeki no kyojin": "wbnpCxPu3fyk9XSaZ",
    "demon slayer": "gvwLtiYciaenJRoFy",
    "kimetsu no yaiba": "gvwLtiYciaenJRoFy",
    "jujutsu kaisen": "8Ti9Lnd3gW7TgeCXj",
    "hunter x hunter": "mqT9iNNwP6xBLbc6G",
    "death note": "RezHft5pjutwWcE3B",
    "one punch man": "8sB7F65RGSQ3dMjYa",
    "spy x family": "LGPNPnjSRKx8TqkGq",
    "chainsaw man": "osGHAaTHeoTZLTs4o",
    "my hero academia": "gKwRaeqdMMkgmCLZw",
    "boku no hero academia": "gKwRaeqdMMkgmCLZw",
    "fullmetal alchemist brotherhood": "yLCKvGbhA6buygXad",
    "solo leveling": "B6AMhLy6EQHDgYgBF",
    "jigokuraku": "JNqf7LSYsHLDgHE7P",
    "hells paradise": "JNqf7LSYsHLDgHE7P",
    "hell's paradise": "JNqf7LSYsHLDgHE7P",
    "vinland saga": "jaJdELAe23ieuzqXb",
    "mob psycho 100": "gPZdPDi7QxAhHb4Fg",
    "black clover": "wn3B4v55q4Bb2P9GZ",
    "dr stone": "RXqaJYhzDNGbjS5aP",
    "ranking of kings": "T8sRYJAGJjbKTFQER",
    "ousama ranking": "T8sRYJAGJjbKTFQER",
    "boruto": "sGF5XZmb4yBCgvbWf",
    "cowboy bebop": "C3sJfKrswsD2CaQXs",
    "trigun": "sEYpMHcYB5jXjW5rG",
    "monster": "TFPbLSqS8RBWwPYyM",
    "frieren": "ReHMC7TQnch3C6z8j",
    "sousou no frieren": "ReHMC7TQnch3C6z8j",
    "your lie in april": "tWvYfivmWmYh8yo9X",
    "shigatsu wa kimi no uso": "tWvYfivmWmYh8yo9X",
    "fire force": "JHCtsyQDXk4cbZni5",
    "enen no shouboutai": "JHCtsyQDXk4cbZni5",
    "oshi no ko": "b3u5TprKSKHBPBcor",
    "to your eternity": "QLc78PZcyyh3CiCvf",
    "fumetsu no anata e": "QLc78PZcyyh3CiCvf",
    "classroom of the elite": "N4PxPNBZ94b3BbTja",
    "youkoso jitsuryoku": "N4PxPNBZ94b3BbTja",
    "konosuba": "gqgoX5eRhxKemyGtG",
    "dororo": "RJgTXs5Bv9nhQqHHM",
}


class ProviderService:
    """Service for anime streaming providers via anipy-api with caching"""
    
    def __init__(self):
        self.provider = None
        self.provider_name = None
        # Caches for performance
        self._search_cache: Dict[str, tuple] = {}  # query -> (results, timestamp)
        self._episode_cache: Dict[str, tuple] = {}  # anime_id -> (episodes, timestamp)
        self._stream_cache: Dict[str, tuple] = {}   # anime_id:ep:lang -> (stream, timestamp)
        self._cache_ttl = 3600  # 1 hour cache
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the streaming provider"""
        try:
            logger.info("Initializing AllAnime provider...")
            self.provider = AllAnimeProvider()
            self.provider_name = "allanime"
            logger.info(f"✅ Provider initialized: allanime")
        except Exception as e:
            logger.error(f"❌ Failed to initialize provider: {e}")
    
    def _is_cache_valid(self, cache_entry: tuple) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry:
            return False
        _, timestamp = cache_entry
        return (time.time() - timestamp) < self._cache_ttl
    
    def get_provider_id_by_anilist(self, anilist_id: int) -> Optional[str]:
        """Get provider ID directly from AniList ID mapping (instant)"""
        return ANILIST_TO_PROVIDER.get(anilist_id)
    
    def get_provider_id_by_title(self, title: str) -> Optional[str]:
        """Get provider ID from title mapping (instant)"""
        title_lower = title.lower().strip()
        # Direct match
        if title_lower in TITLE_TO_PROVIDER:
            return TITLE_TO_PROVIDER[title_lower]
        # Partial match
        for key, provider_id in TITLE_TO_PROVIDER.items():
            if key in title_lower or title_lower in key:
                return provider_id
        return None
    
    def search_anime(self, query: str, language: str = "sub") -> List[Dict]:
        """Search for anime - uses mapping first, then search with caching"""
        if not self.provider:
            raise Exception("Provider not initialized")
        
        query_lower = query.lower().strip()
        cache_key = f"{query_lower}:{language}"
        
        # Check cache
        if cache_key in self._search_cache and self._is_cache_valid(self._search_cache[cache_key]):
            logger.info(f"Cache hit for search: {query}")
            return self._search_cache[cache_key][0]
        
        try:
            lang_enum = LanguageTypeEnum.SUB if language == "sub" else LanguageTypeEnum.DUB
            
            # Try title mapping first (instant)
            provider_id = self.get_provider_id_by_title(query)
            if provider_id:
                try:
                    eps = list(self.provider.get_episodes(provider_id, lang_enum))
                    if len(eps) > 0:
                        logger.info(f"Mapped '{query}' -> provider ID '{provider_id}' ({len(eps)} eps)")
                        result = [{"id": provider_id, "name": query, "languages": ["sub", "dub"]}]
                        self._search_cache[cache_key] = (result, time.time())
                        return result
                except Exception as e:
                    logger.warning(f"Mapped ID failed: {e}")
            
            # Fallback to provider search
            logger.info(f"Searching provider for: {query}")
            results = list(self.provider.get_search(query, Filters()))
            
            # Filter and score results
            scored_results = []
            for anime in results[:10]:  # Limit to first 10
                similarity = self._calculate_similarity(query_lower, anime.name.lower())
                if similarity > 30:  # Minimum threshold
                    scored_results.append({
                        "id": anime.identifier,
                        "name": anime.name,
                        "languages": ["sub", "dub"],
                        "_score": similarity
                    })
            
            # Sort by score
            scored_results.sort(key=lambda x: -x.get("_score", 0))
            
            # Remove internal score
            for r in scored_results:
                r.pop("_score", None)
            
            final_results = scored_results[:5]
            self._search_cache[cache_key] = (final_results, time.time())
            return final_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _calculate_similarity(self, query: str, name: str) -> float:
        """Calculate similarity score"""
        query = re.sub(r'[^\w\s]', '', query.lower()).strip()
        name = re.sub(r'[^\w\s]', '', name.lower()).strip()
        
        if query == name:
            return 100
        if query in name:
            return 80 + (len(query) / len(name)) * 15
        if name in query:
            return 70 + (len(name) / len(query)) * 15
        
        query_words = set(query.split())
        name_words = set(name.split())
        common = query_words & name_words
        
        if common:
            return 40 + (len(common) / max(len(query_words), len(name_words))) * 40
        return 0
    
    def get_episodes(self, anime_id: str, language: str = "sub") -> List[Dict]:
        """Get episode list with caching"""
        if not self.provider:
            raise Exception("Provider not initialized")
        
        cache_key = f"{anime_id}:{language}"
        
        # Check cache
        if cache_key in self._episode_cache and self._is_cache_valid(self._episode_cache[cache_key]):
            logger.info(f"Cache hit for episodes: {anime_id}")
            return self._episode_cache[cache_key][0]
        
        try:
            lang_enum = LanguageTypeEnum.SUB if language == "sub" else LanguageTypeEnum.DUB
            episodes = list(self.provider.get_episodes(anime_id, lang_enum))
            
            result = [{"number": ep, "id": str(ep)} for ep in episodes]
            self._episode_cache[cache_key] = (result, time.time())
            return result
        except Exception as e:
            logger.error(f"Failed to get episodes: {e}")
            raise
    
    def get_stream_url(self, anime_id: str, episode_number: int, language: str = "sub") -> dict:
        """Get stream URL with caching (short TTL for streams)"""
        if not self.provider:
            raise Exception("Provider not initialized")
        
        cache_key = f"{anime_id}:{episode_number}:{language}"
        
        # Check cache (shorter TTL for streams - 10 minutes)
        if cache_key in self._stream_cache:
            cached, timestamp = self._stream_cache[cache_key]
            if (time.time() - timestamp) < 600:  # 10 min cache for streams
                logger.info(f"Cache hit for stream: {anime_id} ep {episode_number}")
                return cached
        
        try:
            lang_enum = LanguageTypeEnum.SUB if language == "sub" else LanguageTypeEnum.DUB
            streams = self.provider.get_video(anime_id, episode_number, lang_enum)
            
            if not streams:
                raise ValueError(f"No streams found for episode {episode_number}")
            
            # Get best quality stream
            stream = streams[0]
            
            if not hasattr(stream, 'url') or not stream.url:
                raise ValueError(f"Stream URL not available for episode {episode_number}")
            
            result = {
                "url": stream.url,
                "referrer": getattr(stream, 'referrer', 'https://allanime.day'),
                "resolution": getattr(stream, 'resolution', 1080)
            }
            self._stream_cache[cache_key] = (result, time.time())
            return result
                
        except Exception as e:
            logger.error(f"Failed to get stream URL: {e}")
            raise
    
    def get_episodes_by_anilist_id(self, anilist_id: int, language: str = "sub") -> List[Dict]:
        """Get episodes using AniList ID (instant lookup)"""
        provider_id = self.get_provider_id_by_anilist(anilist_id)
        if not provider_id:
            raise ValueError(f"No mapping for AniList ID: {anilist_id}")
        return self.get_episodes(provider_id, language)
    
    def check_availability(self, anime_id: str, language: str = "sub") -> bool:
        """Quick check if anime has available episodes"""
        try:
            eps = self.get_episodes(anime_id, language)
            return len(eps) > 0
        except:
            return False


# Global provider instance (initialized once)
provider_service = ProviderService()
