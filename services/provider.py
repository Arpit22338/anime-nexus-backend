"""
Multi-Provider Anime Streaming Service
Uses AniNeko (formerly Gogoanime/Anitaku) as primary - reliable free streaming
"""
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import logging
import time
import re

logger = logging.getLogger(__name__)


# AniList ID -> AniNeko slug mapping for popular anime
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
    170890: "jigokuraku-2nd-season",
    145064: "jujutsu-kaisen-2nd-season",
    127230: "jujutsu-kaisen-tv",

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
    98707: "kaguya-sama-wa-kokurasetai-tensai-tachi-no-renai-zunousen",
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


class AniNekoProvider:
    """AniNeko scraper (formerly Gogoanime/Anitaku) - reliable free streaming"""

    BASE_URL = "https://anineko.to"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def search(self, query: str) -> List[Dict]:
        """Search for anime on AniNeko"""
        try:
            url = f"{self.BASE_URL}/browser?keyword={requests.utils.quote(query)}"
            resp = self.session.get(url, timeout=15)

            if resp.status_code != 200:
                logger.warning(f"AniNeko search failed: {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')
            results = []
            seen_slugs = set()

            for link in soup.select('a[href^="/watch/"]'):
                href = link.get('href', '')
                # Skip episode links and duplicates
                if '/ep-' in href:
                    continue

                slug = href.replace('/watch/', '').strip('/')
                if not slug or slug in seen_slugs:
                    continue
                seen_slugs.add(slug)

                name = link.get_text(strip=True)
                if not name:
                    # Try to find text in child elements
                    name_elem = link.select_one('h3, .title, strong, span')
                    name = name_elem.get_text(strip=True) if name_elem else slug.replace('-', ' ').title()

                img_elem = link.select_one('img')
                image = img_elem.get('src', '') if img_elem else ''

                results.append({
                    'id': slug,
                    'name': name,
                    'image': image,
                })

            # Sort: exact matches first
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
            logger.error(f"AniNeko search error: {e}")
            return []

    def get_episodes(self, anime_id: str) -> List[Dict]:
        """Get episode list for an anime"""
        try:
            url = f"{self.BASE_URL}/watch/{anime_id}"
            resp = self.session.get(url, timeout=15)

            if resp.status_code != 200:
                logger.warning(f"AniNeko anime page failed for {anime_id}: {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')
            episodes = []
            seen = set()

            for link in soup.select(f'a[href*="/watch/{anime_id}/ep-"]'):
                href = link.get('href', '')
                match = re.search(r'/ep-(\d+)', href)
                if match:
                    ep_num = int(match.group(1))
                    if ep_num not in seen:
                        seen.add(ep_num)
                        episodes.append({'number': ep_num, 'id': str(ep_num)})

            episodes.sort(key=lambda x: x['number'])
            return episodes

        except Exception as e:
            logger.error(f"AniNeko episodes error: {e}")
            return []

    def get_stream_url(self, anime_id: str, episode: int, language: str = "sub") -> Optional[Dict]:
        """Get stream URL for an episode, properly selecting SUB or DUB servers"""
        try:
            url = f"{self.BASE_URL}/watch/{anime_id}/ep-{episode}"
            resp = self.session.get(url, timeout=15)

            if resp.status_code != 200:
                logger.warning(f"AniNeko episode page failed: {resp.status_code}")
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Group servers by language panel
            # Panels have structure: div.nv-server-panel > div.nv-server-panel-head > strong (label)
            # followed by button.server-video[data-video]
            panels = soup.select('div.nv-server-panel')

            dub_servers = []
            sub_servers = []
            hardsub_servers = []

            for panel in panels:
                header = panel.select_one('.nv-server-panel-head strong')
                panel_type = header.get_text(strip=True).lower() if header else ''

                buttons = panel.select('button.server-video[data-video]')
                server_urls = [btn.get('data-video', '') for btn in buttons if btn.get('data-video')]

                if 'dub' in panel_type:
                    dub_servers.extend(server_urls)
                elif 'sort sub' in panel_type or 'soft sub' in panel_type:
                    sub_servers.extend(server_urls)
                elif 'hard sub' in panel_type or 'hsub' in panel_type:
                    hardsub_servers.extend(server_urls)
                else:
                    sub_servers.extend(server_urls)

            # If panel parsing didn't work, fall back to all data-video buttons
            if not dub_servers and not sub_servers and not hardsub_servers:
                all_buttons = soup.select('button.server-video[data-video]')
                sub_servers = [btn.get('data-video', '') for btn in all_buttons if btn.get('data-video')]

            # Select servers based on language preference
            if language == "dub":
                candidates = dub_servers or sub_servers or hardsub_servers
            else:
                candidates = sub_servers or hardsub_servers or dub_servers

            if not candidates:
                return None

            # Prefer vibeplayer/otaku servers
            preferred_keywords = ['vibeplayer', 'otaku', 'vibe']
            for keyword in preferred_keywords:
                for server_url in candidates:
                    if keyword in server_url.lower():
                        return {
                            'url': server_url,
                            'referrer': self.BASE_URL,
                            'resolution': 1080
                        }

            # Return first available
            return {
                'url': candidates[0],
                'referrer': self.BASE_URL,
                'resolution': 1080
            }

        except Exception as e:
            logger.error(f"AniNeko stream error: {e}")
            return None


class ProviderService:
    """Main provider service with AniNeko backend"""

    def __init__(self):
        self.anineko = AniNekoProvider()
        self.provider = self.anineko
        self.provider_name = "anineko"
        self._cache = {}
        self._cache_ttl = 3600
        logger.info("ProviderService initialized with AniNeko provider")

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache:
            return False
        _, timestamp = self._cache[key]
        return (time.time() - timestamp) < self._cache_ttl

    def get_provider_id_by_anilist(self, anilist_id: int) -> Optional[str]:
        """Get AniNeko slug from AniList ID (instant)"""
        return ANILIST_TO_ANITAKU.get(anilist_id)

    def get_provider_id_by_title(self, title: str) -> Optional[str]:
        """Get AniNeko slug from title (instant)"""
        title_lower = title.lower().strip()
        if title_lower in TITLE_TO_ANITAKU:
            return TITLE_TO_ANITAKU[title_lower]
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

        mapped_id = self.get_provider_id_by_title(query)

        if mapped_id:
            eps = self.anineko.get_episodes(mapped_id)
            if eps:
                logger.info(f"Mapped '{query}' -> '{mapped_id}' ({len(eps)} eps)")
                result = [{'id': mapped_id, 'name': query, 'languages': ['sub', 'dub']}]
                self._cache[cache_key] = (result, time.time())
                return result

        results = self.anineko.search(query)
        formatted = [{'id': r['id'], 'name': r['name'], 'languages': ['sub', 'dub']} for r in results]
        self._cache[cache_key] = (formatted, time.time())
        return formatted

    def get_episodes(self, anime_id: str, language: str = "sub") -> List[Dict]:
        """Get episodes for anime (same slug for SUB/DUB on AniNeko)"""
        cache_key = f"episodes:{anime_id}"

        if self._is_cache_valid(cache_key):
            logger.info(f"Cache hit for episodes: {anime_id}")
            return self._cache[cache_key][0]

        eps = self.anineko.get_episodes(anime_id)
        self._cache[cache_key] = (eps, time.time())
        return eps

    def get_stream_url(self, anime_id: str, episode_number: int, language: str = "sub") -> Dict:
        """Get stream URL for episode with proper SUB/DUB selection"""
        cache_key = f"stream:{anime_id}:{episode_number}:{language}"

        if cache_key in self._cache:
            cached, timestamp = self._cache[cache_key]
            if (time.time() - timestamp) < 600:
                logger.info(f"Cache hit for stream: {anime_id} ep {episode_number}")
                return cached

        stream = self.anineko.get_stream_url(anime_id, episode_number, language)

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
