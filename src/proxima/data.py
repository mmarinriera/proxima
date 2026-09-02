from pydantic import BaseModel

from proxima.tmdb_client import TMDBItem


class DiscoverQuery(BaseModel):
    genres: list[str] | None = None
    year_from: int | None = None
    year_to: int | None = None
    min_rating: float | None = None
    min_votes: int | None = None
    sort_by: str = "vote_average.desc"
    n_results: int = 20


class TMDBGenresResponse(BaseModel):
    genres: list[str]


class TMDBDiscoverResponse(BaseModel):
    n_results: int
    items_list: list[TMDBItem]
