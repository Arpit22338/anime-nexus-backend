"""
Anime Streaming Service - Multiple Working Providers
"""
import requests
import logging
import time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

TITLE_TO_MAL = {
    'one piece': '21', 'naruto': '20', 'naruto shippuden': '1735', 'bleach': '269',
    'attack on titan': '16498', 'demon slayer': '101921', 'jujutsu kaisen': '127230',
    'my hero academia': '21459', 'one punch man': '30276', 'hunter x hunter': '11061',
    'death note': '1535', 'fullmetal alchemist': '5114', 'dragon ball': '813',
    'dragon ball z': '813', 'dragon ball super': '21291', 'boruto': '97986',
    'spy x family': '140960', 'chainsaw man': '131681', 'frieren': '154587',
}


class JikanProvider:
    """Jikan API - anime metadata"""
    
    BASE_URL = "https://api.jikan.moe/v4"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        self.last_request_time = 0
    
    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        self.last_request_time = time.time()
    
    def search(self, query: str) -> List[Dict]:
        try:
            self._rate_limit()
            url = f"{self.BASE_URL}/anime"
            params = {'q': query, 'limit': 15, 'sfw': True}
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return []
            data = resp.json()
            results = []
            for item in data.get('data', []):
                mal_id = item.get('mal_id', 0)
                title = item.get('title_english') or item.get('title', '')
                results.append({'id': str(mal_id), 'name': title, 'mal_id': mal_id})
            return results
        except Exception as e:
            logger.error(f"Jikan search error: {e}")
            return []
    
    def get_episodes(self, anime_id: str) -> List[Dict]:
        try:
            self._rate_limit()
            url = f"{self.BASE_URL}/anime/{anime_id}"
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return []
            data = resp.json()
            anime = data.get('data', {})
            episodes = anime.get('episodes')
            if episodes and episodes > 0:
                return [{'number': i, 'id': str(i)} for i in range(1, min(episodes + 1, 1000))]
            elif anime.get('status') == 'Currently Airing':
                return [{'number': 1, 'id': '1'}]
            return []
        except Exception as e:
            logger.error(f"Jikan episodes error: {e}")
            return []


class GogoAnimeProvider:
    """GogoAnime3 - Working direct watch page"""
    
    BASE_URL = "https://gogoanime3.net"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36',
            'Referer': 'https://gogoanime3.net/',
        })
    
    def get_stream_url(self, anime_id: str, episode: int) -> Optional[Dict]:
        return {
            'url': f"{self.BASE_URL}/watch/{anime_id}/ep/{episode}",
            'referrer': self.BASE_URL,
            'resolution': 720,
            'source': 'gogoanime'
        }


class AnimeXProvider:
    """AnimeX.one - Working anime streaming"""
    
    BASE_URL = "https://animex.one"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36',
        })
    
    def search(self, query: str) -> List[Dict]:
        try:
            url = f"{self.BASE_URL}/search"
            params = {'keyword': query}
            resp = self.session.get(url, params=params, timeout=10, follow_redirects=True)
            if resp.status_code != 200:
                return []
            return []
        except Exception as e:
            logger.error(f"AnimeX search error: {e}")
            return []
    
    def get_stream_url(self, anime_id: str, episode: int) -> Optional[Dict]:
        return {
            'url': f"{self.BASE_URL}/watch/{anime_id}/ep-{episode}",
            'referrer': self.BASE_URL,
            'resolution': 720,
            'source': 'animex'
        }


class ProviderService:
    def __init__(self):
        self.jikan = JikanProvider()
        self.gogo = GogoAnimeProvider()
        self.animex = AnimeXProvider()
        self._cache = {}
        self._cache_ttl = 3600
        logger.info("AnimeService: Jikan + GogoAnime + AnimeX")
    
    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache:
            return False
        _, timestamp = self._cache[key]
        return (time.time() - timestamp) < self._cache_ttl
    
    def get_provider_id_by_title(self, title: str) -> Optional[str]:
        title_lower = title.lower().strip()
        if title_lower in TITLE_TO_MAL:
            return TITLE_TO_MAL[title_lower]
        for key, mal_id in TITLE_TO_MAL.items():
            if key in title_lower or title_lower in key:
                return mal_id
        return None
    
    def search_anime(self, query: str, language: str = "sub") -> List[Dict]:
        cache_key = f"search:{query.lower()}:{language}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key][0]
        
        mapped_id = self.get_provider_id_by_title(query)
        if mapped_id:
            eps = self.jikan.get_episodes(mapped_id)
            if eps:
                result = [{'id': mapped_id, 'name': query, 'languages': ['sub', 'dub']}]
                self._cache[cache_key] = (result, time.time())
                return result
        
        results = self.jikan.search(query)
        formatted = [{'id': r['id'], 'name': r['name'], 'languages': ['sub', 'dub']} for r in results]
        self._cache[cache_key] = (formatted, time.time())
        return formatted
    
    def get_episodes(self, anime_id: str, language: str = "sub") -> List[Dict]:
        cache_key = f"episodes:{anime_id}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key][0]
        eps = self.jikan.get_episodes(anime_id)
        self._cache[cache_key] = (eps, time.time())
        return eps
    
    def get_stream_url(self, anime_id: str, episode_number: int, language: str = "sub") -> Dict:
        cache_key = f"stream:{anime_id}:{episode_number}:{language}"
        if cache_key in self._cache:
            cached, timestamp = self._cache[cache_key]
            if (time.time() - timestamp) < 600:
                return cached
        
        stream = self.gogo.get_stream_url(anime_id, episode_number)
        self._cache[cache_key] = (stream, time.time())
        return stream
    
    def get_all_stream_providers(self, anime_id: str, episode: int) -> List[Dict]:
        """Get stream URLs from all providers"""
        providers = []
        
        gogo_stream = self.gogo.get_stream_url(anime_id, episode)
        if gogo_stream:
            providers.append({
                'name': 'GogoAnime',
                'url': gogo_stream['url'],
                'referrer': gogo_stream['referrer']
            })
        
        animex_stream = self.animex.get_stream_url(anime_id, episode)
        if animex_stream:
            providers.append({
                'name': 'AnimeX',
                'url': animex_stream['url'],
                'referrer': animex_stream['referrer']
            })
        
        return providers


provider_service = ProviderService()