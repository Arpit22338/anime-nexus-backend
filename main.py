"""
Anime Streaming Backend API
FastAPI backend for personal anime streaming application
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from services.anilist import AniListService
from services.provider import provider_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Anime Stream API",
    description="Backend API for anime streaming using AniList + anipy-api",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
anilist = AniListService()


@app.get("/")
async def root():
    """Health check endpoint"""
    provider_status = "ready" if provider_service.provider else "unavailable"
    return {
        "status": "online",
        "name": "Anime Stream API",
        "version": "1.0.0",
        "provider": provider_service.provider_name or "not initialized",
        "provider_status": provider_status
    }


@app.get("/search")
async def search_anime(
    q: str = Query(..., description="Anime name to search"),
    limit: int = Query(15, ge=1, le=50, description="Max results")
):
    """
    Search for anime using AniList
    
    Returns anime metadata including title, episodes, etc.
    """
    try:
        results = await anilist.search_anime(q, limit)
        return {
            "success": True,
            "query": q,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/anime/{anime_id}")
async def get_anime_details(anime_id: int):
    """
    Get detailed information about a specific anime from AniList
    
    Args:
        anime_id: AniList anime ID
    """
    try:
        anime = await anilist.get_anime_details(anime_id)
        
        if not anime:
            raise HTTPException(status_code=404, detail="Anime not found")
        
        return {
            "success": True,
            "anime": anime
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get anime details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/episodes/{anime_name}")
async def get_episodes(
    anime_name: str,
    language: str = Query("sub", regex="^(sub|dub)$")
):
    """
    Get episode list for an anime using the streaming provider
    
    Args:
        anime_name: Name of the anime (searches provider)
        language: 'sub' or 'dub'
    """
    try:
        # Search provider for this anime
        search_results = provider_service.search_anime(anime_name, language)
        
        if not search_results:
            raise HTTPException(
                status_code=404,
                detail=f"Anime '{anime_name}' not found in streaming provider"
            )
        
        # Use first result
        anime = search_results[0]
        
        # Get episodes
        episodes = provider_service.get_episodes(anime["id"], language)
        
        return {
            "success": True,
            "anime": anime,
            "language": language,
            "episodes": episodes,
            "episode_count": len(episodes)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get episodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stream/{anime_name}/{episode_number}")
async def get_stream(
    anime_name: str,
    episode_number: int,
    language: str = Query("sub", regex="^(sub|dub)$")
):
    """
    Get stream URL for a specific episode
    
    Args:
        anime_name: Name of the anime
        episode_number: Episode number (1-indexed)
        language: 'sub' or 'dub'
    """
    try:
        # Search provider for this anime
        search_results = provider_service.search_anime(anime_name, language)
        
        if not search_results:
            raise HTTPException(
                status_code=404,
                detail=f"Anime '{anime_name}' not found in streaming provider"
            )
        
        # Use first result
        anime = search_results[0]
        
        # Get stream URL
        stream_url = provider_service.get_stream_url(
            anime["id"],
            episode_number,
            language
        )
        
        if not stream_url:
            raise HTTPException(
                status_code=404,
                detail=f"Stream not found for episode {episode_number}"
            )
        
        return {
            "success": True,
            "anime": anime,
            "episode": episode_number,
            "language": language,
            "stream_url": stream_url
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/providers")
async def list_providers():
    """List available streaming providers"""
    from anipy_api.provider import list_providers
    
    try:
        providers = list(list_providers())
        return {
            "success": True,
            "providers": providers,
            "current": provider_service.provider_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
