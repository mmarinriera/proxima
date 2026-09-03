from typing import Annotated
from typing import Any

from pydantic import AliasChoices
from pydantic import BaseModel
from pydantic import BeforeValidator
from pydantic import Field

# Clients data models


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


def _clean_scraped_string(value: Any) -> Any:
    if isinstance(value, str):
        value = value.replace("\u00a0", " ").replace("N/A", "").strip()
        return value or "0"
    return value


class FluvialItem(BaseModel):
    name: Annotated[str, BeforeValidator(_clean_scraped_string)]
    size: Annotated[str, BeforeValidator(_clean_scraped_string)]
    date: Annotated[str, BeforeValidator(_clean_scraped_string)]
    seeders: Annotated[int, BeforeValidator(_clean_scraped_string)]
    leechers: Annotated[int, BeforeValidator(_clean_scraped_string)]
    url: str
    category: str = ""
    uploader: str = ""
    hash: str = ""
    magnet: str = ""


# API data models


class DiscoverQuery(BaseModel):
    genres: list[str] | None = None
    year_from: int | None = None
    year_to: int | None = None
    min_rating: float | None = None
    min_votes: int | None = None
    sort_by: str = "vote_average.desc"
    n_results: int = 20


class FluvialSearchQuery(BaseModel):
    site: str
    query: str
    n_results: int = 20
    sort: bool = True


class TMDBGenresResponse(BaseModel):
    genres: list[str]


class TMDBDiscoverResponse(BaseModel):
    n_results: int
    items_list: list[TMDBItem]


class FluvialSearchResponse(BaseModel):
    n_results: int
    items_list: list[FluvialItem]
