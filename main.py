"""
Anime Streaming Backend API
FastAPI backend for personal anime streaming application
"""
from fastapi import FastAPI, HTTPException, Query, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
import logging
import httpx

from services.anilist import AniListService
from services.provider import provider_service
from services.movies import movie_service

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

# Create API router with /api prefix
api = APIRouter(prefix="/api")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "name": "Anime Stream API",
        "version": "1.0.0",
        "provider": "gogoanime",
        "provider_status": "ready"
    }


@api.get("/search")
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


@api.get("/anime/{anime_id}")
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


@api.get("/episodes/{anime_name}")
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


@api.get("/stream/{anime_name}/{episode_number}")
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
        
        # Get stream data (now returns dict with url, referrer, resolution)
        stream_data = provider_service.get_stream_url(
            anime["id"],
            episode_number,
            language
        )
        
        if not stream_data:
            raise HTTPException(
                status_code=404,
                detail=f"Stream not found for episode {episode_number}"
            )
        
        return {
            "success": True,
            "anime": anime,
            "episode": episode_number,
            "language": language,
            "stream_url": stream_data["url"],
            "referrer": stream_data["referrer"],
            "resolution": stream_data["resolution"]
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/stream-by-id/{anime_id}/{episode_number}")
async def get_stream_by_id(
    anime_id: str,
    episode_number: int,
    language: str = Query("sub", regex="^(sub|dub)$")
):
    """
    Get stream URL using anime ID directly (no search needed)
    
    Args:
        anime_id: Provider anime ID
        episode_number: Episode number (1-indexed)
        language: 'sub' or 'dub'
    """
    try:
        # Get stream data directly using ID
        stream_data = provider_service.get_stream_url(
            anime_id,
            episode_number,
            language
        )
        
        if not stream_data:
            raise HTTPException(
                status_code=404,
                detail=f"Stream not found for episode {episode_number}"
            )
        
        return {
            "success": True,
            "anime_id": anime_id,
            "episode": episode_number,
            "language": language,
            "stream_url": stream_data["url"],
            "referrer": stream_data["referrer"],
            "resolution": stream_data["resolution"]
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get stream by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/proxy")
async def proxy_stream(
    url: str = Query(..., description="Video URL to proxy"),
    referer: str = Query("https://allanime.day", description="Referrer header")
):
    """
    Proxy video stream to bypass referrer restrictions
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Referer": referer,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                follow_redirects=True,
                timeout=30.0
            )
            
            return StreamingResponse(
                iter([response.content]),
                media_type=response.headers.get("content-type", "video/mp4"),
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": response.headers.get("content-length", "0")
                }
            )
    except Exception as e:
        logger.error(f"Proxy failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/providers")
async def list_available_providers():
    """List available streaming providers"""
    return {
        "success": True,
        "providers": ["gogoanime", "animex"],
        "current": "gogoanime",
        "status": "ready"
    }


@api.get("/episodes-by-id/{anime_id}")
async def get_episodes_by_id(
    anime_id: str,
    language: str = Query("sub", regex="^(sub|dub)$")
):
    """
    Get episodes using provider ID directly (faster, no search)
    
    Args:
        anime_id: Provider's anime identifier
        language: 'sub' or 'dub'
    """
    try:
        episodes = provider_service.get_episodes(anime_id, language)
        return {
            "success": True,
            "anime_id": anime_id,
            "language": language,
            "episodes": episodes,
            "episode_count": len(episodes)
        }
    except Exception as e:
        logger.error(f"Failed to get episodes by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/lookup/{anilist_id}")
async def lookup_provider_id(anilist_id: int):
    """
    Get provider ID from AniList ID (instant lookup from mapping)
    
    Args:
        anilist_id: AniList anime ID
    """
    # Map AniList ID to MAL ID for streaming
    provider_id = str(anilist_id)  # Use AniList ID directly
    
    return {
        "success": True,
        "anilist_id": anilist_id,
        "provider_id": provider_id,
        "mapped": True
    }


@api.get("/trending")
async def get_trending():
    """Get trending anime from AniList"""
    try:
        trending = await anilist.get_trending()
        return {
            "success": True,
            "trending": trending
        }
    except Exception as e:
        logger.error(f"Failed to get trending: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HENTAI/ADULT ANIME ROUTES ====================
# Disabled - requires separate adult content service

@api.get("/hentai/search")
async def search_hentai(q: str = Query(..., description="Hentai search query")):
    """Search for hentai anime - Currently disabled"""
    return {
        "success": False,
        "error": "Hentai service temporarily unavailable",
        "results": []
    }


@api.get("/hentai/{provider}/{anime_id}")
async def get_hentai_episodes(provider: str, anime_id: str):
    """Get hentai episodes - Currently disabled"""
    return {
        "success": False,
        "error": "Hentai service temporarily unavailable",
        "episodes": []
    }


@api.get("/hentai/stream/{provider}/{anime_id}/{episode}")
async def get_hentai_stream(provider: str, anime_id: str, episode: int = 1):
    """Get hentai stream URL - Currently disabled"""
    return {
        "success": False,
        "error": "Hentai service temporarily unavailable"
    }


# ============ MOVIES API ============
@api.get("/movies/search")
async def search_movies(q: str = Query(..., description="Search query")):
    """Search movies/TV shows"""
    try:
        results = movie_service.search_movies(q)
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Movie search error: {e}")
        return {"success": False, "results": [], "error": str(e)}


@api.get("/movies/popular")
async def get_popular_movies(category: str = Query("all", description="movies, tv, or all")):
    """Get popular movies/TV shows"""
    try:
        if category == "movies":
            movies = movie_service.get_popular_movies('movies')
        elif category == "tv":
            movies = movie_service.get_popular_movies('tv')
        else:
            movies = movie_service.get_popular_movies('popular')
        return {"success": True, "movies": movies}
    except Exception as e:
        logger.error(f"Popular movies error: {e}")
        return {"success": False, "movies": []}


@api.get("/movies/{movie_id}")
async def get_movie_details(movie_id: int):
    """Get movie details and streaming sources"""
    try:
        stream_result = movie_service.get_movie_stream(movie_id)
        
        # Get metadata
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://api.tvmaze.com/shows/{movie_id}")
        
        if resp.status_code == 200:
            show = resp.json()
            return {
                "success": True,
                "id": show.get('id'),
                "title": show.get('name'),
                "summary": show.get('summary', '').replace('<p>', '').replace('</p>', '') if show.get('summary') else '',
                "image": show.get('image', {}).get('original') or show.get('image', {}).get('medium') if show.get('image') else '',
                "rating": show.get('rating', {}).get('average'),
                "year": show.get('premiered', '')[:4] if show.get('premiered') else '',
                "genres": show.get('genres', []),
                "runtime": show.get('runtime'),
                "sources": stream_result.get('sources', [])
            }
        
        return {"success": True, "sources": stream_result.get('sources', [])}
    except Exception as e:
        logger.error(f"Movie details error: {e}")
        return {"success": False, "error": str(e)}


@api.get("/movies/stream/{movie_id}")
async def get_movie_stream(movie_id: int):
    """Get movie streaming embeds"""
    try:
        stream_result = movie_service.get_movie_stream(movie_id)
        return stream_result
    except Exception as e:
        logger.error(f"Movie stream error: {e}")
        return {"success": False, "sources": []}


@api.get("/tv/stream/{tv_id}/{season}/{episode}")
async def get_tv_stream(tv_id: int, season: int, episode: int):
    """Get TV episode streaming embeds"""
    try:
        stream_result = movie_service.get_tv_stream(tv_id, season, episode)
        return stream_result
    except Exception as e:
        logger.error(f"TV stream error: {e}")
        return {"success": False, "sources": []}


# Include the API router
app.include_router(api)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
