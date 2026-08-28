from __future__ import annotations

import os
from typing import Any

import httpx


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_token: str | None = None):
        self.api_token = api_token or os.environ["TMDB_API_TOKEN"]

        self.session = httpx.Client()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_token}",
                "accept": "application/json",
            }
        )

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self.session.get(
            f"{self.BASE_URL}{endpoint}",
            params=params,
            timeout=10,
        )

        response.raise_for_status()
        return response.json()

    def discover_movies(
        self,
        *,
        genre: int | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        min_rating: float | None = None,
        min_votes: int | None = None,
        sort_by: str = "vote_average.desc",
        page: int = 1,
    ) -> dict[str, Any]:

        params: dict[str, Any] = {
            "language": "en-US",
            "include_adult": False,
            "include_video": False,
            "sort_by": sort_by,
            "page": page,
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

        return self._get("/discover/movie", params)

    def discover_tv(
        self,
        *,
        genre: int | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        min_rating: float | None = None,
        min_votes: int | None = None,
        sort_by: str = "vote_average.desc",
        page: int = 1,
    ) -> dict[str, Any]:

        params: dict[str, Any] = {
            "language": "en-US",
            "include_adult": False,
            "sort_by": sort_by,
            "page": page,
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

        return self._get("/discover/tv", params)
