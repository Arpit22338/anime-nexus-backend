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
