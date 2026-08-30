import logging
import os
from typing import Any

from hishel import CacheOptions
from hishel import SpecificationPolicy
from hishel import SyncSqliteStorage
from hishel.httpx import SyncCacheClient

logger = logging.getLogger(__name__)

MAX_N_RESULTS = 100
DEFAULT_CACHE_TTL = 3600 * 24  # 24h
DEFAULT_CACHE_PATH = ".cache/hishel/hishel_cache.db"

policy = SpecificationPolicy(
    cache_options=CacheOptions(
        shared=False,
    )
)

storage = SyncSqliteStorage(database_path=DEFAULT_CACHE_PATH, default_ttl=DEFAULT_CACHE_TTL)


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_token: str | None = None):
        self.api_token = api_token or os.environ["TMDB_API_TOKEN"]

        self.session = SyncCacheClient(
            storage=SyncSqliteStorage(database_path=".cache/hishel/hishel_cache.db", default_ttl=DEFAULT_CACHE_TTL),
            policy=policy,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "accept": "application/json",
            },
        )

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self.session.get(
            url=f"{self.BASE_URL}{endpoint}",
            params=params,
            timeout=10,
        )
        logger.debug(f"from cache: {response.extensions['hishel_from_cache']}")

        response.raise_for_status()
        return response.json()

    def _aggregate_results(self, url: str, params: dict[str, Any], n_results: int) -> list[dict[str, str]]:
        if n_results > MAX_N_RESULTS:
            logger.warning(
                f"Max number of results queried at once is {MAX_N_RESULTS}. Capped query to {MAX_N_RESULTS}."
            )
            n_results = MAX_N_RESULTS
        results = []
        page = 0
        while len(results) < n_results:
            page += 1
            params["page"] = page
            logger.debug(f"querying page {page}")
            data = self._get(url, params)

            if page == 1 and data["total_results"] < n_results:
                logger.warning(f"Only {data['total_results']} are available.")
                n_results = data["total_results"]

            results.extend(data["results"])
            logger.debug(f"results so far {len(results)}")
            if data["total_pages"] == page:
                break

        return results[:n_results]

    def discover_movies(
        self,
        *,
        genre: int | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        min_rating: float | None = None,
        min_votes: int | None = None,
        sort_by: str = "vote_average.desc",
        n_results: int = 20,
    ) -> list[dict[str, str]]:

        params: dict[str, Any] = {
            "language": "en-US",
            "include_adult": False,
            "include_video": False,
            "sort_by": sort_by,
        }

        if genre is not None:
            params["with_genres"] = genre

        if year_from is not None:
            params["primary_release_date.gte"] = f"{year_from}-01-01"

        if year_to is not None:
            params["primary_release_date.lte"] = f"{year_to}-12-31"

        if min_rating is not None:
            params["vote_average.gte"] = min_rating

        if min_votes is not None:
            params["vote_count.gte"] = min_votes

        return self._aggregate_results(url="/discover/movie", params=params, n_results=n_results)

    def discover_tv(
        self,
        *,
        genre: int | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        min_rating: float | None = None,
        min_votes: int | None = None,
        sort_by: str = "vote_average.desc",
        n_results: int = 20,
    ) -> list[dict[str, str]]:

        params: dict[str, Any] = {
            "language": "en-US",
            "include_adult": False,
            "sort_by": sort_by,
        }

        if genre is not None:
            params["with_genres"] = genre

        if year_from is not None:
            params["first_air_date.gte"] = f"{year_from}-01-01"

        if year_to is not None:
            params["first_air_date.lte"] = f"{year_to}-12-31"

        if min_rating is not None:
            params["vote_average.gte"] = min_rating

        if min_votes is not None:
            params["vote_count.gte"] = min_votes

        return self._aggregate_results(url="/discover/tv", params=params, n_results=n_results)
