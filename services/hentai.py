"""
Hentai/Adult Anime Service - Multiple Working Providers
"""
import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Working hentai streaming sites (tested May 2026)
HENTAI_SITES = {
    "hentai2w": {
        "name": "Hentai2w",
        "base_url": "https://hentai2w.com",
        "search_url": "https://hentai2w.com/search?q={query}",
        "embed_template": "https://hentai2w.com/videos/{slug}"
    },
    "hentaimama": {
        "name": "HentaiMama",
        "base_url": "https://hentaimama.io",
        "search_url": "https://hentaimama.io/search?q={query}",
        "embed_template": "https://hentaimama.io/videos/{slug}"
    },
    "hentaihaven": {
        "name": "HentaiHaven",
        "base_url": "https://hentaihaven.com",
        "search_url": "https://hentaihaven.com/search?q={query}",
        "embed_template": "https://hentaihaven.com/video/{slug}"
    }
}


class HentaiService:
    """Hentai streaming service"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        })
        self._cache = {}
        self._cache_ttl = 1800
        logger.info("HentaiService: Hentai2w + HentaiMama + HentaiHaven")
    
    def search(self, query: str) -> List[Dict]:
        """Search hentai - returns direct site links"""
        cache_key = f"hentai_search:{query.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        results = []
        for site_id, site_info in HENTAI_SITES.items():
            search_url = site_info['search_url'].format(query=query)
            results.append({
                'site': site_info['name'],
                'site_id': site_id,
                'search_url': search_url,
                'base_url': site_info['base_url']
            })
        
        self._cache[cache_key] = results
        return results
    
    def get_providers(self) -> List[Dict]:
        """Get available hentai providers"""
        providers = []
        for site_id, site_info in HENTAI_SITES.items():
            providers.append({
                'id': site_id,
                'name': site_info['name'],
                'url': site_info['base_url']
            })
        return providers
    
    def get_stream_url(self, provider: str, slug: str) -> Optional[Dict]:
        """Get stream URL for hentai"""
        if provider not in HENTAI_SITES:
            return None
        
        site_info = HENTAI_SITES[provider]
        return {
            'url': site_info['embed_template'].format(slug=slug),
            'referrer': site_info['base_url'],
            'source': provider
        }


hentai_service = HentaiService()