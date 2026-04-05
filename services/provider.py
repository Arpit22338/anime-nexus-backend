"""
Multi-Provider Anime Streaming Service
Uses Anitaku (Gogoanime) as primary - reliable free streaming
"""
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import logging
import time
import re

logger = logging.getLogger(__name__)


# AniList ID -> Anitaku ID mapping for popular anime
ANILIST_TO_ANITAKU = {
    # Major Shonen
    21: "one-piece",
    20: "naruto",
    1735: "naruto-shippuuden",
    269: "bleach",
    170998: "bleach-sennen-kessen-hen",
    11061: "hunter-x-hunter-2011",
    1535: "death-note",
    16498: "shingeki-no-kyojin",
    110277: "shingeki-no-kyojin-the-final-season",
    101922: "kimetsu-no-yaiba",
    113415: "jigokuraku",
    170890: "jigokuraku-2nd-season",  # Season 2
    145064: "kimetsu-no-yaiba-yuukaku-hen",
    127230: "jujutsu-kaisen-tv",
    145064: "jujutsu-kaisen-2nd-season",
    
    # Modern Popular
    21459: "boku-no-hero-academia",
    131681: "chainsaw-man",
    140960: "spy-x-family",
    142838: "spy-x-family-season-2",
    30276: "one-punch-man",
    21087: "one-punch-man",
    151807: "ore-dake-level-up-na-ken",
    176496: "ore-dake-level-up-na-ken-season-2-arise-from-the-shadow",
    
    # Trending/Popular 2024-2026
    154587: "sousou-no-frieren",
    163146: "dandadan",
    171018: "blue-lock-vs-u-20-japan",
    166216: "kaijuu-8-gou",
    21: "one-piece",
    20665: "shigatsu-wa-kimi-no-uso",
    98659: "youkoso-jitsuryoku-shijou-shugi-no-kyoushitsu-e-tv",
    101921: "enen-no-shouboutai",
    139630: "oshi-no-ko",
    166531: "oshi-no-ko-2nd-season",
    173440: "oshi-no-ko-3rd-season",
    162669: "fumetsu-no-anata-e-2nd-season",
    114535: "fumetsu-no-anata-e",
    
    # Classics
    5114: "fullmetal-alchemist-brotherhood",
    1: "cowboy-bebop",
    6: "trigun",
    19: "monster",
    21: "one-piece",
    97: "gintama",
    918: "gintama",
    
    # Dragon Ball
    813: "dragon-ball-kai",
    20474: "dragon-ball-kai-2014",
    21291: "dragon-ball-super",
    
    # Popular Ongoing/Recent
    21519: "boku-no-hero-academia",
    104578: "vinland-saga",
    136430: "vinland-saga-season-2",
    101759: "dororo",
    97986: "boruto-naruto-next-generations",
    114745: "ousama-ranking",
    105333: "dr-stone",
    97940: "black-clover-tv",
    100166: "kono-subarashii-sekai-ni-shukufuku-wo",
    136804: "kono-subarashii-sekai-ni-shukufuku-wo-3",
    
    # Romance/Slice of Life
    21519: "boku-no-hero-academia",
    98707: "kaguya-sama-wa-kokurasetai-tensai-tachi-no-renai-zunousen",
    101921: "enen-no-shouboutai",
    124080: "kaguya-sama-wa-kokurasetai-tensai-tachi-no-renai-zunousen-2",
    125367: "horimiya",
    21234: "violet-evergarden",
    
    # Isekai
    21855: "re-zero-kara-hajimeru-isekai-seikatsu",
    108465: "re-zero-kara-hajimeru-isekai-seikatsu-2nd-season",
    97938: "isekai-maou-to-shoukan-shoujo-no-dorei-majutsu",
    101348: "tensei-shitara-slime-datta-ken",
    116742: "tensei-shitara-slime-datta-ken-2nd-season",
    155783: "mushoku-tensei-ii-isekai-ittara-honki-dasu",
    108725: "mushoku-tensei-isekai-ittara-honki-dasu",
}

# Title-based lookup
TITLE_TO_ANITAKU = {
    "one piece": "one-piece",
    "naruto": "naruto",
    "naruto shippuden": "naruto-shippuuden",
    "naruto shippuuden": "naruto-shippuuden",
    "bleach": "bleach",
    "bleach thousand year blood war": "bleach-sennen-kessen-hen",
    "attack on titan": "shingeki-no-kyojin",
    "shingeki no kyojin": "shingeki-no-kyojin",
    "demon slayer": "kimetsu-no-yaiba",
    "kimetsu no yaiba": "kimetsu-no-yaiba",
    "jujutsu kaisen": "jujutsu-kaisen-tv",
    "hunter x hunter": "hunter-x-hunter-2011",
    "death note": "death-note",
    "one punch man": "one-punch-man",
    "my hero academia": "boku-no-hero-academia",
    "boku no hero academia": "boku-no-hero-academia",
    "chainsaw man": "chainsaw-man",
    "spy x family": "spy-x-family",
    "frieren": "sousou-no-frieren",
    "sousou no frieren": "sousou-no-frieren",
    "solo leveling": "ore-dake-level-up-na-ken",
    "jigokuraku": "jigokuraku",
    "hell's paradise": "jigokuraku",
    "vinland saga": "vinland-saga",
    "mob psycho 100": "mob-psycho-100",
    "mob psycho": "mob-psycho-100",
    "black clover": "black-clover-tv",
    "dr stone": "dr-stone",
    "dr. stone": "dr-stone",
    "ranking of kings": "ousama-ranking",
    "ousama ranking": "ousama-ranking",
    "boruto": "boruto-naruto-next-generations",
    "cowboy bebop": "cowboy-bebop",
    "trigun": "trigun",
    "monster": "monster",
    "fullmetal alchemist brotherhood": "fullmetal-alchemist-brotherhood",
    "fullmetal alchemist": "fullmetal-alchemist-brotherhood",
    "your lie in april": "shigatsu-wa-kimi-no-uso",
    "shigatsu wa kimi no uso": "shigatsu-wa-kimi-no-uso",
    "fire force": "enen-no-shouboutai",
    "enen no shouboutai": "enen-no-shouboutai",
    "oshi no ko": "oshi-no-ko",
    "[oshi no ko]": "oshi-no-ko",
    "to your eternity": "fumetsu-no-anata-e",
    "fumetsu no anata e": "fumetsu-no-anata-e",
    "classroom of the elite": "youkoso-jitsuryoku-shijou-shugi-no-kyoushitsu-e-tv",
    "konosuba": "kono-subarashii-sekai-ni-shukufuku-wo",
    "dororo": "dororo",
    "dragon ball z": "dragon-ball-z",
    "dragon ball super": "dragon-ball-super",
    "dragon ball": "dragon-ball",
    "gintama": "gintama",
    "dandadan": "dandadan",
    "blue lock": "blue-lock",
    "kaiju no 8": "kaijuu-8-gou",
    "kaiju no. 8": "kaijuu-8-gou",
    "re:zero": "re-zero-kara-hajimeru-isekai-seikatsu",
    "re zero": "re-zero-kara-hajimeru-isekai-seikatsu",
    "that time i got reincarnated as a slime": "tensei-shitara-slime-datta-ken",
    "slime": "tensei-shitara-slime-datta-ken",
    "tensura": "tensei-shitara-slime-datta-ken",
    "mushoku tensei": "mushoku-tensei-isekai-ittara-honki-dasu",
    "jobless reincarnation": "mushoku-tensei-isekai-ittara-honki-dasu",
    "violet evergarden": "violet-evergarden",
    "horimiya": "horimiya",
    "kaguya sama": "kaguya-sama-wa-kokurasetai-tensai-tachi-no-renai-zunousen",
    "kaguya-sama": "kaguya-sama-wa-kokurasetai-tensai-tachi-no-renai-zunousen",
    "love is war": "kaguya-sama-wa-kokurasetai-tensai-tachi-no-renai-zunousen",
    "tokyo ghoul": "tokyo-ghoul",
    "sword art online": "sword-art-online",
    "sao": "sword-art-online",
    "steins gate": "steins-gate",
    "steins;gate": "steins-gate",
    "code geass": "code-geass-hangyaku-no-lelouch",
    "neon genesis evangelion": "neon-genesis-evangelion",
    "evangelion": "neon-genesis-evangelion",
    "akame ga kill": "akame-ga-kill",
    "tokyo revengers": "tokyo-revengers",
    "parasyte": "kiseijuu-sei-no-kakuritsu",
    "fairy tail": "fairy-tail",
    "overlord": "overlord",
    "noragami": "noragami",
    "haikyuu": "haikyuu",
    "haikyu": "haikyuu",
}


class AnitakuProvider:
    """Gogoanime/Anitaku scraper - reliable free streaming provider"""
    
    BASE_URL = "https://anitaku.to"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
        })
    
    def search(self, query: str) -> List[Dict]:
        """Search for anime"""
        try:
            url = f"{self.BASE_URL}/search.html?keyword={requests.utils.quote(query)}"
            resp = self.session.get(url, timeout=15)
            
            if resp.status_code != 200:
                logger.warning(f"Anitaku search failed: {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = []
            
            for item in soup.select('ul.items li'):
                name_elem = item.select_one('.name a')
                img_elem = item.select_one('.img img')
                released_elem = item.select_one('.released')
                
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    href = name_elem.get('href', '')
                    anime_id = href.split('/')[-1] if '/' in href else href
                    
                    results.append({
                        'id': anime_id,
                        'name': name,
                        'image': img_elem.get('src', '') if img_elem else '',
                        'released': released_elem.get_text(strip=True) if released_elem else ''
                    })
            
            # Sort: exact matches first, main series over movies
            query_lower = query.lower()
            def sort_key(x):
                name_lower = x['name'].lower()
                is_movie = 'movie' in name_lower or 'film' in name_lower or 'special' in name_lower
                if name_lower == query_lower:
                    return (0, 0, 0)
                elif query_lower in name_lower and not is_movie:
                    return (0, 1, len(name_lower))
                elif query_lower in name_lower:
                    return (1, 0, len(name_lower))
                else:
                    return (2, 0, len(name_lower))
            
            results.sort(key=sort_key)
            return results[:15]
            
        except Exception as e:
            logger.error(f"Anitaku search error: {e}")
            return []
    
    def get_episodes(self, anime_id: str) -> List[Dict]:
        """Get episode list for an anime"""
        try:
            url = f"{self.BASE_URL}/category/{anime_id}"
            resp = self.session.get(url, timeout=15)
            
            if resp.status_code != 200:
                logger.warning(f"Anitaku category failed for {anime_id}: {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find episode ranges from pagination
            ep_pages = soup.select('#episode_page li a')
            episodes = []
            
            if ep_pages:
                for page in ep_pages:
                    text = page.get_text(strip=True)
                    if '-' in text:
                        parts = text.split('-')
                        try:
                            start = int(parts[0])
                            end = int(parts[1])
                            for ep in range(start, end + 1):
                                episodes.append({'number': ep, 'id': str(ep)})
                        except ValueError:
                            pass
            
            # Deduplicate and sort
            seen = set()
            unique_eps = []
            for ep in episodes:
                if ep['number'] not in seen:
                    seen.add(ep['number'])
                    unique_eps.append(ep)
            
            unique_eps.sort(key=lambda x: x['number'])
            return unique_eps
            
        except Exception as e:
            logger.error(f"Anitaku episodes error: {e}")
            return []
    
    def get_stream_url(self, anime_id: str, episode: int) -> Optional[Dict]:
        """Get stream URL for an episode"""
        try:
            url = f"{self.BASE_URL}/{anime_id}-episode-{episode}"
            resp = self.session.get(url, timeout=15)
            
            if resp.status_code != 200:
                logger.warning(f"Anitaku episode page failed: {resp.status_code}")
                return None
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Get streaming servers
            servers = soup.select('.anime_muti_link ul li a')
            
            # Priority order for servers
            preferred_keywords = ['vidstream', 'gogo', 'vibe', 'otaku']
            
            for keyword in preferred_keywords:
                for server in servers:
                    video_url = server.get('data-video', '')
                    if video_url and keyword in video_url.lower():
                        return {
                            'url': video_url,
                            'referrer': self.BASE_URL,
                            'resolution': 1080
                        }
            
            # Return first available if no preferred server found
            for server in servers:
                video_url = server.get('data-video', '')
                if video_url:
                    return {
                        'url': video_url,
                        'referrer': self.BASE_URL,
                        'resolution': 1080
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Anitaku stream error: {e}")
            return None


class ProviderService:
    """Main provider service with Anitaku backend"""
    
    def __init__(self):
        self.anitaku = AnitakuProvider()
        self.provider = self.anitaku  # For compatibility
        self.provider_name = "anitaku"
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour
        logger.info("✅ ProviderService initialized with Anitaku (Gogoanime) provider")
    
    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache:
            return False
        _, timestamp = self._cache[key]
        return (time.time() - timestamp) < self._cache_ttl
    
    def get_provider_id_by_anilist(self, anilist_id: int) -> Optional[str]:
        """Get Anitaku ID from AniList ID (instant)"""
        return ANILIST_TO_ANITAKU.get(anilist_id)
    
    def get_provider_id_by_title(self, title: str) -> Optional[str]:
        """Get Anitaku ID from title (instant)"""
        title_lower = title.lower().strip()
        if title_lower in TITLE_TO_ANITAKU:
            return TITLE_TO_ANITAKU[title_lower]
        # Partial match
        for key, provider_id in TITLE_TO_ANITAKU.items():
            if key in title_lower or title_lower in key:
                return provider_id
        return None
    
    def search_anime(self, query: str, language: str = "sub") -> List[Dict]:
        """Search for anime"""
        cache_key = f"search:{query.lower()}:{language}"
        
        if self._is_cache_valid(cache_key):
            logger.info(f"Cache hit for search: {query}")
            return self._cache[cache_key][0]
        
        # Try mapped ID first (instant)
        query_lower = query.lower().strip()
        mapped_id = self.get_provider_id_by_title(query)
        
        if mapped_id:
            eps = self.anitaku.get_episodes(mapped_id)
            if eps:
                logger.info(f"Mapped '{query}' -> '{mapped_id}' ({len(eps)} eps)")
                result = [{'id': mapped_id, 'name': query, 'languages': ['sub', 'dub']}]
                self._cache[cache_key] = (result, time.time())
                return result
        
        # Search provider
        results = self.anitaku.search(query)
        formatted = [{'id': r['id'], 'name': r['name'], 'languages': ['sub', 'dub']} for r in results]
        self._cache[cache_key] = (formatted, time.time())
        return formatted
    
    def get_episodes(self, anime_id: str, language: str = "sub") -> List[Dict]:
        """Get episodes for anime"""
        cache_key = f"episodes:{anime_id}:{language}"
        
        if self._is_cache_valid(cache_key):
            logger.info(f"Cache hit for episodes: {anime_id}")
            return self._cache[cache_key][0]
        
        # For dub, try with -dub suffix
        actual_id = anime_id
        if language == "dub":
            dub_id = f"{anime_id}-dub"
            eps = self.anitaku.get_episodes(dub_id)
            if eps:
                actual_id = dub_id
            else:
                eps = self.anitaku.get_episodes(anime_id)
        else:
            eps = self.anitaku.get_episodes(anime_id)
        
        self._cache[cache_key] = (eps, time.time())
        return eps
    
    def get_stream_url(self, anime_id: str, episode_number: int, language: str = "sub") -> Dict:
        """Get stream URL for episode"""
        cache_key = f"stream:{anime_id}:{episode_number}:{language}"
        
        # Check cache (10 min TTL for streams)
        if cache_key in self._cache:
            cached, timestamp = self._cache[cache_key]
            if (time.time() - timestamp) < 600:
                logger.info(f"Cache hit for stream: {anime_id} ep {episode_number}")
                return cached
        
        # For dub, try with -dub suffix
        actual_id = anime_id
        if language == "dub":
            dub_id = f"{anime_id}-dub"
            eps = self.anitaku.get_episodes(dub_id)
            if eps:
                actual_id = dub_id
        
        stream = self.anitaku.get_stream_url(actual_id, episode_number)
        
        if not stream:
            raise ValueError(f"No stream found for {anime_id} episode {episode_number}")
        
        self._cache[cache_key] = (stream, time.time())
        return stream
    
    def check_availability(self, anime_id: str, language: str = "sub") -> bool:
        """Check if anime is available"""
        try:
            eps = self.get_episodes(anime_id, language)
            return len(eps) > 0
        except:
            return False


# Global provider instance
provider_service = ProviderService()
