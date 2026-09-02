import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from fastapi import FastAPI
from fastapi import Query
from fastapi import Request
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from proxima.data import DiscoverQuery
from proxima.data import TMDBDiscoverResponse
from proxima.data import TMDBGenresResponse
from proxima.tmdb_client import AsyncTMDBClient
from proxima.tmdb_client import MediaCategory

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    TMDB_API_TOKEN: str
    TMDB_CACHE_STORAGE_PATH: str
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncTMDBClient(
        tmdb_api_token=settings.TMDB_API_TOKEN,
        cache_storage_path=settings.TMDB_CACHE_STORAGE_PATH,
    ) as client:
        app.state.tmdb = client
        yield


app = FastAPI(lifespan=lifespan)


def get_tmdb_client(request: Request) -> AsyncTMDBClient:
    return request.app.state.tmdb


@app.get("/tmdb/genres/{category}")
async def tmdb_genres(
    category: MediaCategory,
    client: Annotated[AsyncTMDBClient, Depends(get_tmdb_client)],
) -> TMDBGenresResponse:

    result = await client.get_genres(category=category)
    return TMDBGenresResponse(genres=result)


@app.get("/tmdb/discover/{category}")
async def tmdb_discover(
    category: MediaCategory,
    discover_query: Annotated[DiscoverQuery, Query()],
    client: Annotated[AsyncTMDBClient, Depends(get_tmdb_client)],
) -> TMDBDiscoverResponse:

    result = await client.discover(category=category, **discover_query.model_dump())
    return TMDBDiscoverResponse(n_results=len(result), items_list=result)
