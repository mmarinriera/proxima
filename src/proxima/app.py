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
from proxima.data import FluvialSearchQuery
from proxima.data import FluvialSearchResponse
from proxima.data import TMDBDiscoverResponse
from proxima.data import TMDBGenresResponse
from proxima.fluvial_client import AsyncFluvialClient
from proxima.tmdb_client import AsyncTMDBClient
from proxima.tmdb_client import GenreError
from proxima.tmdb_client import MediaCategory

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    TMDB_API_TOKEN: str
    TMDB_CACHE_STORAGE_PATH: str
    FLUVIAL_API_URL: str
    FLUVIAL_CACHE_STORAGE_PATH: str
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with (
        AsyncTMDBClient(
            tmdb_api_token=settings.TMDB_API_TOKEN,
            cache_storage_path=settings.TMDB_CACHE_STORAGE_PATH,
        ) as tmdb,
        AsyncFluvialClient(
            fluvial_api_url=settings.FLUVIAL_API_URL,
            cache_storage_path=settings.FLUVIAL_CACHE_STORAGE_PATH,
        ) as fluvial,
    ):
        app.state.tmdb = tmdb
        app.state.fluvial = fluvial

        yield


app = FastAPI(lifespan=lifespan)


# Exception handlers
@app.exception_handler(ConnectError)
async def connect_error_exception_handler(request: Request, exc: ConnectError):
    service = "TMDB" if "tmdb" in str(request.url) else "Fluvial"
    return JSONResponse(
        status_code=442,
        content={"message": f"Service is not available: {service}."},
    )


@app.exception_handler(GenreError)
async def genre_error_exception_handler(request: Request, exc: GenreError):
    return JSONResponse(
        status_code=443,
        content={"message": f"{exc}"},
    )


@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=444,
        content={"message": f"{exc}"},
    )


# Dependencies
def get_tmdb_client(request: Request) -> AsyncTMDBClient:
    return request.app.state.tmdb


def get_fluvial_client(request: Request) -> AsyncFluvialClient:
    return request.app.state.fluvial


# Path operations
@app.get("/tmdb/genres/{category}")
async def tmdb_genres(
    category: MediaCategory,
    tmdb: Annotated[AsyncTMDBClient, Depends(get_tmdb_client)],
) -> TMDBGenresResponse:

    result = await tmdb.get_genres(category=category)
    return TMDBGenresResponse(genres=result)


@app.get("/tmdb/discover/{category}")
async def tmdb_discover(
    category: MediaCategory,
    discover_query: Annotated[DiscoverQuery, Query()],
    tmdb: Annotated[AsyncTMDBClient, Depends(get_tmdb_client)],
) -> TMDBDiscoverResponse:

    result = await tmdb.discover(category=category, **discover_query.model_dump())
    return TMDBDiscoverResponse(n_results=len(result), items_list=result)


@app.get("/fluvial/search")
async def fluvial_search(
    search_query: Annotated[FluvialSearchQuery, Query()],
    fluvial: Annotated[AsyncFluvialClient, Depends(get_fluvial_client)],
) -> FluvialSearchResponse:

    result = await fluvial.search(**search_query.model_dump())
    return FluvialSearchResponse(n_results=len(result), items_list=result)
