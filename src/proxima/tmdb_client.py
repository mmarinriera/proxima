import logging
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Annotated
from typing import Any
from typing import Self

import httpx
from hishel import AsyncSqliteStorage
from hishel import CacheOptions
from hishel import SpecificationPolicy
from hishel import SyncSqliteStorage
from hishel.httpx import AsyncCacheClient
from hishel.httpx import SyncCacheClient
from pydantic import AliasChoices
from pydantic import BaseModel
from pydantic import Field

logger = logging.getLogger(__name__)

BASE_URL = "https://api.themoviedb.org/3"
MAX_N_RESULTS = 100
DEFAULT_CACHE_TTL = 60 * 30  # 30min
DEFAULT_CACHE_PATH = ".cache/hishel/tmdb_cache.db"
LONG_TTL = 3600 * 24

TIME_FIELD_MOVIE = "primary_release_date"
TIME_FIELD_TV = "first_air_date"

GENRE_QUERY_PARAMS = {"language": "en-US"}

DEFAULT_CACHE_POLICY = SpecificationPolicy(cache_options=CacheOptions(shared=False))


class GenreError(Exception):
    """Invalid TMDB genre."""


class MediaCategory(str, Enum):
    movie = "movie"
    tv = "tv"


class TMDBItem(BaseModel):
    backdrop_path: str | None
    genre_ids: list[int]
    id: int
    original_language: str
    original_title: Annotated[str, Field(validation_alias=AliasChoices("original_title", "original_name"))]
    overview: str
    popularity: float
    poster_path: str | None
    release_date: str
    release_date: Annotated[str, Field(validation_alias=AliasChoices("release_date", "first_air_date"))]
    title: Annotated[str, Field(validation_alias=AliasChoices("title", "name"))]
    vote_average: float
    vote_count: int
    genres: Annotated[list[str], Field(default_factory=list)]
    adult: bool = False
    video: bool = False


class GenresManager:
    def __init__(self, api_token: str) -> None:
        self.api_token = api_token
        self.genres = {
            MediaCategory.movie: self._query_genres(MediaCategory.movie),
            MediaCategory.tv: self._query_genres(MediaCategory.tv),
        }

        self.genres_encoder = {
            MediaCategory.movie: {g["name"].lower(): g["id"] for g in self.genres[MediaCategory.movie]},
            MediaCategory.tv: {g["name"].lower(): g["id"] for g in self.genres[MediaCategory.tv]},
        }

        self.genres_decoder = {
            MediaCategory.movie: {g["id"]: g["name"] for g in self.genres[MediaCategory.movie]},
            MediaCategory.tv: {g["id"]: g["name"] for g in self.genres[MediaCategory.tv]},
        }

    def _query_genres(self, category: MediaCategory) -> list[dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "accept": "application/json",
        }
        response = httpx.get(url=f"{BASE_URL}/genre/{category.value}/list", params=GENRE_QUERY_PARAMS, headers=headers)
        response.raise_for_status()
        data: dict[str, list[dict[str, Any]]] = response.json()

        return data["genres"]

    def get_genres(self, category: MediaCategory) -> list[str]:
        """Get list of TMDB coded genres from a media category."""
        return [item["name"] for item in self.genres[category]]

    def encode_genres(self, category: MediaCategory, input_genres: list[str]) -> list[int]:
        genres_encoder: dict[str, int] = self.genres_encoder[category]
        try:
            encoded = [genres_encoder[name.lower()] for name in input_genres]
        except KeyError as e:
            raise GenreError(f"Invalid input genre: {e}.")
        return encoded

    def decode_genres(self, category: MediaCategory, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        genres_decoder: dict[int, str] = self.genres_decoder[category]
        try:
            for item in results:
                item["genres"] = [genres_decoder[gid] for gid in item["genre_ids"]]
        except KeyError as e:
            raise GenreError(f"Unknown genre while processing results: {e}.")
        return results


@dataclass
class QueryParams:
    category: MediaCategory
    genres_manager: GenresManager
    n_results: int
    genres: list[str] | None = None
    year_from: int | None = None
    year_to: int | None = None
    min_rating: float | None = None
    min_votes: int | None = None
    sort_by: str = "vote_average.desc"
    language: str = "en-US"
    include_adult: bool = False
    include_video: bool = False
    _n_results: int = field(init=False, repr=False)

    @property
    def n_results(self) -> int:
        if self._n_results > MAX_N_RESULTS:
            logger.warning(
                f"Max number of results queried at once is {MAX_N_RESULTS}. Capped query to {MAX_N_RESULTS}.",
            )
            return MAX_N_RESULTS
        return self._n_results

    @n_results.setter
    def n_results(self, val: int) -> None:
        self._n_results = val

    def parse(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "language": self.language,
            "include_adult": self.include_adult,
            "include_video": self.include_video,
            "sort_by": self.sort_by,
        }

        if self.genres is not None:
            params["with_genres"] = "|".join(
                [str(g) for g in self.genres_manager.encode_genres(category=self.category, input_genres=self.genres)]
            )
            logger.debug(f"genres param {params['with_genres']}")

        time_field = TIME_FIELD_MOVIE if self.category == MediaCategory.movie else TIME_FIELD_TV

        if self.year_from is not None:
            params[f"{time_field}.gte"] = f"{self.year_from}-01-01"

        if self.year_to is not None:
            params[f"{time_field}.lte"] = f"{self.year_to}-12-31"

        if self.min_rating is not None:
            params["vote_average.gte"] = self.min_rating

        if self.min_votes is not None:
            params["vote_count.gte"] = self.min_votes

        return params


class TMDBClient:
    def __init__(self, tmdb_api_token: str, cache_storage_path: str = DEFAULT_CACHE_PATH):
        self.api_token = tmdb_api_token

        self.client = SyncCacheClient(
            storage=SyncSqliteStorage(database_path=cache_storage_path, default_ttl=DEFAULT_CACHE_TTL),
            policy=DEFAULT_CACHE_POLICY,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "accept": "application/json",
            },
        )

        self.genres_manager = GenresManager(tmdb_api_token)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_details: object) -> None:
        self.client.close()

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self.client.get(
            url=f"{BASE_URL}{endpoint}",
            params=params,
            extensions=extensions,
            timeout=10,
        )
        logger.debug(f"url endpoint '{endpoint}'")
        logger.debug(f"status_code: {response.status_code}")
        logger.debug(f"request params: {params}")
        logger.debug(f"response extensions {response.extensions}")

        response.raise_for_status()
        return response.json()

    def _aggregate_results(self, url: str, params: dict[str, Any], n_results: int) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page = 0
        while len(results) < n_results:
            page += 1
            params["page"] = page
            logger.debug(f"querying page {page}")

            data = self._get(url, params)
            results.extend(data["results"])

            if page == 1 and data["total_results"] < n_results:
                logger.warning(f"Only {data['total_results']} results are available.")
                n_results = data["total_results"]

            logger.debug(f"results so far {len(results)}")
            if data["total_pages"] == page:
                break

        return results[:n_results]

    def get_genres(self, category: MediaCategory) -> list[str]:
        """Get list of TMDB coded genres from a media category."""
        return self.genres_manager.get_genres(category)

    def discover(
        self,
        category: MediaCategory,
        genres: list[str] | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        min_rating: float | None = None,
        min_votes: int | None = None,
        sort_by: str = "vote_average.desc",
        n_results: int = 20,
    ) -> list[TMDBItem]:
        """Query list of media items from TMDB."""
        params = QueryParams(
            category=category,
            genres_manager=self.genres_manager,
            n_results=n_results,  # ty: ignore[unknown-argument]
            genres=genres,
            year_from=year_from,
            year_to=year_to,
            min_rating=min_rating,
            min_votes=min_votes,
            sort_by=sort_by,
        )

        data = self._aggregate_results(
            url=f"/discover/{category.value}", params=params.parse(), n_results=params.n_results
        )
        data = self.genres_manager.decode_genres(category=category, results=data)

        return [TMDBItem.model_validate(item) for item in data]


class AsyncTMDBClient:
    def __init__(self, tmdb_api_token: str, cache_storage_path: str = DEFAULT_CACHE_PATH):
        self.api_token = tmdb_api_token

        self.client = AsyncCacheClient(
            storage=AsyncSqliteStorage(database_path=cache_storage_path, default_ttl=DEFAULT_CACHE_TTL),
            policy=DEFAULT_CACHE_POLICY,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "accept": "application/json",
            },
        )

        self.genres_manager = GenresManager(tmdb_api_token)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_details: object) -> None:
        await self.client.aclose()

    async def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self.client.get(
            url=f"{BASE_URL}{endpoint}",
            params=params,
            extensions=extensions,
            timeout=10,
        )
        logger.debug(f"url endpoint '{endpoint}'")
        logger.debug(f"status_code: {response.status_code}")
        logger.debug(f"request params: {params}")
        logger.debug(f"response extensions {response.extensions}")

        response.raise_for_status()
        return response.json()

    async def _aggregate_results(self, url: str, params: dict[str, Any], n_results: int) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page = 0
        while len(results) < n_results:
            page += 1
            params["page"] = page
            logger.debug(f"querying page {page}")

            data = await self._get(url, params)
            results.extend(data["results"])

            if page == 1 and data["total_results"] < n_results:
                logger.warning(f"Only {data['total_results']} results are available.")
                n_results = data["total_results"]

            logger.debug(f"results so far {len(results)}")
            if data["total_pages"] == page:
                break

        return results[:n_results]

    async def get_genres(self, category: MediaCategory) -> list[str]:
        """Get list of TMDB coded genres from a media category."""
        return self.genres_manager.get_genres(category)

    async def discover(
        self,
        category: MediaCategory,
        genres: list[str] | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        min_rating: float | None = None,
        min_votes: int | None = None,
        sort_by: str = "vote_average.desc",
        n_results: int = 20,
    ) -> list[TMDBItem]:
        """Query list of media items from TMDB."""
        params = QueryParams(
            category=category,
            genres_manager=self.genres_manager,
            n_results=n_results,  # ty: ignore[unknown-argument]
            genres=genres,
            year_from=year_from,
            year_to=year_to,
            min_rating=min_rating,
            min_votes=min_votes,
            sort_by=sort_by,
        )

        data = await self._aggregate_results(
            url=f"/discover/{category.value}", params=params.parse(), n_results=params.n_results
        )
        data = self.genres_manager.decode_genres(category=category, results=data)

        return [TMDBItem.model_validate(item) for item in data]
