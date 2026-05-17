"""
Comprehensive Movie Service - Working Embed Sources
Tested and working: vidsrc.to, vidpop.xyz, multiembed.mov
"""
import requests
import logging

logger = logging.getLogger(__name__)


class MovieService:
    """Comprehensive movie service with multiple working embed sources"""
    
    def __init__(self):
        self._cache = {}
        self._cache_ttl = 1800
        
        # WORKING embed sources (tested 2024)
        self.MOVIE_EMBEDS = [
            ("VidSrc.to", "https://vidsrc.to/embed/movie/{tmdb_id}"),
            ("VidPop", "https://www.vidpop.xyz/embed/?id={tmdb_id}"),
            ("SuperEmbed", "https://multiembed.mov/?video_id={tmdb_id}&tmdb=1"),
        ]
        
        self.TV_EMBEDS = [
            ("VidSrc.to", "https://vidsrc.to/embed/tv/{tmdb_id}/{season}/{episode}"),
            ("VidPop", "https://www.vidpop.xyz/embed/?id={tmdb_id}&season={season}&episode={episode}"),
            ("SuperEmbed", "https://multiembed.mov/?video_id={tmdb_id}&tmdb=1&s={season}&e={episode}"),
        ]
        
        logger.info("MovieService: VidSrc + VidPop + SuperEmbed ready")
    
    def search_movies(self, query: str, year: int = None) -> list:
        """Search movies via TVMaze"""
        try:
            url = f"https://api.tvmaze.com/search/shows?q={query}"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return []
            
            results = []
            for item in resp.json()[:20]:
                show = item.get('show', {})
                show_id = show.get('id', 0)
                runtime = show.get('runtime', 0)
                
                results.append({
                    'id': show_id,
                    'title': show.get('name'),
                    'year': show.get('premiered', '')[:4] if show.get('premiered') else '',
                    'image': show.get('image', {}).get('medium') if show.get('image') else '',
                    'rating': show.get('rating', {}).get('average'),
                    'summary': show.get('summary', '').replace('<p>', '').replace('</p>', '')[:150] if show.get('summary') else '',
                    'type': 'movie' if runtime and runtime > 60 else 'tv',
                    'genres': show.get('genres', [])[:3],
                })
            
            return results[:20]
        except Exception as e:
            logger.error(f"Movie search error: {e}")
            return []
    
    def get_movie_stream(self, tmdb_id: int) -> dict:
        """Get streaming embed URLs for movie"""
        cache_key = f"movie_stream:{tmdb_id}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        sources = []
        
        for name, template in self.MOVIE_EMBEDS:
            embed_url = template.format(tmdb_id=tmdb_id)
            sources.append({
                'name': name,
                'embed_url': embed_url,
                'type': 'iframe'
            })
        
        result = {
            'success': len(sources) > 0,
            'movie_id': tmdb_id,
            'sources': sources
        }
        
        self._cache[cache_key] = result
        return result
    
    def get_tv_stream(self, tmdb_id: int, season: int, episode: int) -> dict:
        """Get streaming embed URLs for TV episode"""
        cache_key = f"tv_stream:{tmdb_id}:{season}:{episode}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        sources = []
        
        for name, template in self.TV_EMBEDS:
            embed_url = template.format(tmdb_id=tmdb_id, season=season, episode=episode)
            sources.append({
                'name': name,
                'embed_url': embed_url,
                'type': 'iframe'
            })
        
        result = {
            'success': len(sources) > 0,
            'tv_id': tmdb_id,
            'season': season,
            'episode': episode,
            'sources': sources
        }
        
        self._cache[cache_key] = result
        return result
    
    def get_popular_movies(self, category: str = 'popular') -> list:
        """Get popular movies/TV shows"""
        try:
            url = f"https://api.tvmaze.com/shows?page=1"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code != 200:
                return []
            
            shows = resp.json()[:50]
            results = []
            
            for show in shows:
                show_id = show.get('id', 0)
                runtime = show.get('runtime', 0)
                
                if category == 'movies' and runtime and runtime > 60:
                    is_movie = True
                elif category == 'tv':
                    is_movie = False
                else:
                    is_movie = runtime and runtime > 60
                
                if is_movie:
                    results.append({
                        'id': show_id,
                        'title': show.get('name'),
                        'year': show.get('premiered', '')[:4] if show.get('premiered') else '',
                        'image': show.get('image', {}).get('medium') if show.get('image') else '',
                        'rating': show.get('rating', {}).get('average'),
                        'type': 'movie'
                    })
            
            return results[:30]
        except Exception as e:
            logger.error(f"Popular movies error: {e}")
            return []


movie_service = MovieService()