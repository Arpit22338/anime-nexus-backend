"""
AniList GraphQL Service
Handles anime metadata from AniList API
"""
import httpx
from typing import Optional, Dict, List

ANILIST_API = "https://graphql.anilist.co"


class AniListService:
    """Service for interacting with AniList GraphQL API"""
    
    def __init__(self):
        self.api_url = ANILIST_API
    
    async def search_anime(self, query: str, limit: int = 15) -> List[Dict]:
        """
        Search for anime on AniList
        
        Args:
            query: Search query string
            limit: Maximum results to return
            
        Returns:
            List of anime with id, title, episodes, etc.
        """
        graphql_query = """
        query ($search: String, $perPage: Int) {
            Page(page: 1, perPage: $perPage) {
                media(type: ANIME, search: $search) {
                    id
                    idMal
                    title {
                        romaji
                        english
                        native
                    }
                    episodes
                    coverImage {
                        large
                        extraLarge
                    }
                    description
                    status
                    averageScore
                    format
                    season
                    seasonYear
                }
            }
        }
        """
        
        variables = {
            "search": query,
            "perPage": limit
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                json={"query": graphql_query, "variables": variables},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            return data["data"]["Page"]["media"]
    
    async def get_anime_details(self, anime_id: int) -> Optional[Dict]:
        """
        Get detailed information about a specific anime
        
        Args:
            anime_id: AniList anime ID
            
        Returns:
            Detailed anime information
        """
        graphql_query = """
        query ($id: Int) {
            Media(id: $id, type: ANIME) {
                id
                idMal
                title {
                    romaji
                    english
                    native
                }
                description
                episodes
                coverImage {
                    large
                    extraLarge
                }
                bannerImage
                status
                averageScore
                genres
                format
                season
                seasonYear
                studios {
                    nodes {
                        name
                    }
                }
            }
        }
        """
        
        variables = {"id": anime_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                json={"query": graphql_query, "variables": variables},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            return data["data"]["Media"]
    
    @staticmethod
    def get_best_title(anime: Dict) -> str:
        """
        Extract the best title for searching providers
        
        Args:
            anime: Anime object from AniList
            
        Returns:
            Best title string (romaji or english)
        """
        title = anime.get("title", {})
        return title.get("romaji") or title.get("english") or title.get("native", "")
    
    async def get_trending(self) -> List[Dict]:
        """Get trending anime from AniList"""
        graphql_query = """
        query {
            Page(page: 1, perPage: 20) {
                media(type: ANIME, sort: TRENDING_DESC) {
                    id
                    idMal
                    title {
                        romaji
                        english
                    }
                    episodes
                    coverImage {
                        large
                        extraLarge
                    }
                    description
                    averageScore
                    format
                }
            }
        }
        """
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    self.api_url,
                    json={"query": graphql_query}
                )
                
                if resp.status_code != 200:
                    return []
                
                data = resp.json()
                media = data.get("data", {}).get("Page", {}).get("media", [])
                
                results = []
                for anime in media:
                    results.append({
                        "id": anime.get("id"),
                        "mal_id": anime.get("idMal"),
                        "title": anime.get("title", {}).get("romaji") or anime.get("title", {}).get("english", ""),
                        "episodes": anime.get("episodes"),
                        "image": anime.get("coverImage", {}).get("large") or anime.get("coverImage", {}).get("extraLarge"),
                        "score": anime.get("averageScore"),
                        "format": anime.get("format")
                    })
                
                return results
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Trending error: {e}")
            return []
