import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from fastapi import FastAPI
from fastapi import Query
from fastapi import Request
from fastapi.responses import JSONResponse
from httpx import ConnectError
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from proxima.data import DiscoverQuery
from proxima.data import TMDBDiscoverResponse
from proxima.data import TMDBGenresResponse
from proxima.tmdb_client import AsyncTMDBClient
from proxima.tmdb_client import GenreError
from proxima.tmdb_client import MediaCategory

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    TMDB_API_TOKEN: str
    TMDB_CACHE_STORAGE_PATH: str = ".cache/tmdb_cache.db"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with (
        AsyncTMDBClient(
            tmdb_api_token=settings.TMDB_API_TOKEN,
            cache_storage_path=settings.TMDB_CACHE_STORAGE_PATH,
        ) as tmdb,
    ):
        app.state.tmdb = tmdb

        yield


app = FastAPI(lifespan=lifespan)


# Exception handlers
@app.exception_handler(ConnectError)
async def connect_error_exception_handler(request: Request, exc: ConnectError):
    return JSONResponse(
        status_code=442,
        content={"message": "TMDB API is not available."},
    )


@app.exception_handler(GenreError)
async def genre_error_exception_handler(request: Request, exc: GenreError):
    return JSONResponse(
        status_code=443,
        content={"message": f"{exc}"},
    )


# Dependencies
def get_tmdb_client(request: Request) -> AsyncTMDBClient:
    return request.app.state.tmdb


# Path operations
@app.get("/tmdb/genres/{category}")
async def tmdb_genres(
    category: MediaCategory,
    tmdb: Annotated[AsyncTMDBClient, Depends(get_tmdb_client)],
) -> TMDBGenresResponse:
    """Show the TMDBgenre categories for movies or TV shows."""
    result = await tmdb.get_genres(category=category)
    return TMDBGenresResponse(genres=result)


@app.get("/tmdb/discover/{category}")
async def tmdb_discover(
    category: MediaCategory,
    discover_query: Annotated[DiscoverQuery, Query()],
    tmdb: Annotated[AsyncTMDBClient, Depends(get_tmdb_client)],
) -> TMDBDiscoverResponse:
    """TMDB Discover lists for movies and TV shows."""
    result = await tmdb.discover(category=category, **discover_query.model_dump())
    return TMDBDiscoverResponse(n_results=len(result), items_list=result)
