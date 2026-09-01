import logging
from enum import Enum
from typing import Annotated
from typing import Any
from typing import Self

from hishel import CacheOptions
from hishel import SpecificationPolicy
from hishel import SyncSqliteStorage
from hishel.httpx import SyncCacheClient
from pydantic import BaseModel
from pydantic import Field

logger = logging.getLogger(__name__)

MAX_N_RESULTS = 100
DEFAULT_CACHE_TTL = 60 * 30  # 30min
DEFAULT_CACHE_PATH = ".cache/hishel/hishel_cache.db"

TIME_FIELD_MOVIE = "primary_release_date"
TIME_FIELD_TV = "first_air_date"


policy = SpecificationPolicy(
    cache_options=CacheOptions(
        shared=False,
    ),
)


class GenreError(Exception):
    """Invalid TMDB genre."""


class MediaCategory(Enum):
    movie = "movie"
    tv = "tv"


class TMDBItem(BaseModel):
    backdrop_path: str
    genre_ids: list[int]
    id: int
    original_language: str
    original_title: str
    overview: str
    popularity: float
    poster_path: str
    release_date: str
    title: str
    vote_average: float
    vote_count: int
    genres: Annotated[list[str], Field(default_factory=list)]


class MovieItem(TMDBItem):
    adult: bool
    backdrop_path: str
    genre_ids: list[int]
    id: int
    original_language: str
    original_title: str
    overview: str
    popularity: float
    poster_path: str
    release_date: str
    title: str
    video: bool
    vote_average: float
    vote_count: int
    genres: Annotated[list[str], Field(default_factory=list)]


class TVItem(TMDBItem):
    backdrop_path: str
    genre_ids: list[int]
    id: int
    origin_country: list[str]
    original_language: str
    original_title: Annotated[str, Field(alias="original_name")]
    overview: str
    popularity: float
    poster_path: str
    release_date: Annotated[str, Field(alias="first_air_date")]
    title: Annotated[str, Field(alias="name")]
    vote_average: float
    vote_count: int
    genres: Annotated[list[str], Field(default_factory=list)]


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, tmdb_api_token: str):
        self.api_token = tmdb_api_token

        self.client = SyncCacheClient(
            storage=SyncSqliteStorage(database_path=DEFAULT_CACHE_PATH, default_ttl=DEFAULT_CACHE_TTL),
            policy=policy,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "accept": "application/json",
            },
        )

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
            url=f"{self.BASE_URL}{endpoint}",
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
        if n_results > MAX_N_RESULTS:
            logger.warning(
                f"Max number of results queried at once is {MAX_N_RESULTS}. Capped query to {MAX_N_RESULTS}.",
            )
            n_results = MAX_N_RESULTS

        results: list[dict[str, Any]] = []
        page = 0
        while len(results) < n_results:
            page += 1
            params["page"] = page
            logger.debug(f"querying page {page}")
            data = self._get(url, params)

            if page == 1 and data["total_results"] < n_results:
                logger.warning(f"Only {data['total_results']} results are available.")
                n_results = data["total_results"]

            results.extend(data["results"])
            logger.debug(f"results so far {len(results)}")
            if data["total_pages"] == page:
                break

        return results[:n_results]

    def _query_genres(self, category: MediaCategory) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "language": "en-US",
        }
        extensions: dict[str, Any] = {
            "hishel_ttl": 3600 * 24,  # Set long ttl for a request that rarely changes
        }
        data: dict[str, list[dict[str, Any]]] = self._get(
            endpoint=f"/genre/{category.value}/list", params=params, extensions=extensions
        )

        return data["genres"]

    def _encode_genres(self, category: MediaCategory, input_genres: list[str]) -> list[int]:
        tmdb_genres = self._query_genres(category=category)
        genres_encoder: dict[str, int] = {g["name"].lower(): g["id"] for g in tmdb_genres}
        try:
            encoded = [genres_encoder[name.lower()] for name in input_genres]
        except KeyError as e:
            raise GenreError(f"Invalid input genre: {e}.")
        return encoded

    def _decode_genres(self, category: MediaCategory, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tmdb_genres = self._query_genres(category=category)
        genres_decoder: dict[int, str] = {g["id"]: g["name"] for g in tmdb_genres}
        try:
            for item in results:
                item["genres"] = [genres_decoder[gid] for gid in item["genre_ids"]]
        except KeyError as e:
            raise GenreError(f"Unknown genre while processing results: {e}.")
        return results

    def get_genres(self, category: MediaCategory) -> list[str]:
        """Get list of TMDB coded genres from a media category."""
        return [item["name"] for item in self._query_genres(category=category)]

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
        params: dict[str, Any] = {
            "language": "en-US",
            "include_adult": False,
            "include_video": False,
            "sort_by": sort_by,
        }

        if genres is not None:
            params["with_genres"] = "|".join(
                [str(g) for g in self._encode_genres(category=category, input_genres=genres)]
            )
            logger.debug(f"genres param {params['with_genres']}")

        time_field = TIME_FIELD_MOVIE if category == MediaCategory.movie else TIME_FIELD_TV

        if year_from is not None:
            params[f"{time_field}.gte"] = f"{year_from}-01-01"

        if year_to is not None:
            params[f"{time_field}.lte"] = f"{year_to}-12-31"

        if min_rating is not None:
            params["vote_average.gte"] = min_rating

        if min_votes is not None:
            params["vote_count.gte"] = min_votes

        data = self._aggregate_results(url=f"/discover/{category.value}", params=params, n_results=n_results)
        data = self._decode_genres(category=category, results=data)

        item_cls = MovieItem if category == MediaCategory.movie else TVItem

        return [item_cls.model_validate(item) for item in data]
