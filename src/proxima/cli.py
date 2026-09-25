import logging
import os
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich import print

from proxima import console
from proxima import get_version
from proxima import set_logging_level
from proxima.data import SortCriteria
from proxima.tmdb_client import GenreError
from proxima.tmdb_client import MediaCategory
from proxima.tmdb_client import TMDBClient

proxima = typer.Typer()

logger = logging.getLogger(__name__)

TMDB_DEFAULT_OUTPUT_FIELDS = ["title", "genres", "vote_average", "overview"]


def _load_env(ctx: typer.Context) -> None:
    load_dotenv(".env")
    tmdb_api_key = os.getenv("TMDB_API_TOKEN")
    if tmdb_api_key is None:
        logger.critical("TMDB API key not found")
        raise typer.Exit(1)

    ctx.obj["tmdb_api_token"] = tmdb_api_key


def version_callback(value: bool) -> None:
    if value:
        print(get_version())
        raise typer.Exit()


@proxima.callback()
def cli_callback(
    ctx: typer.Context,
    version: Annotated[
        bool, typer.Option("-v", "--version", callback=version_callback, is_eager=True, help="Show version and exit.")
    ] = False,
    debug_mode: Annotated[bool, typer.Option("-d", "--debug", help="Enable DEBUG logging.")] = False,
) -> None:
    """TMDB API client"""
    ctx.ensure_object(dict)

    if debug_mode:
        set_logging_level(level=logging.DEBUG)

    ctx.obj["debug"] = debug_mode

    _load_env(ctx)


@proxima.command()
def genres(ctx: typer.Context, category: MediaCategory) -> None:
    """Query TMDB genre categories."""
    with TMDBClient(tmdb_api_token=ctx.obj["tmdb_api_token"]) as tmdb:
        data = tmdb.get_genres(category=category)
    console.print_genres(data, category.value)


@proxima.command()
def discover(
    ctx: typer.Context,
    category: MediaCategory,
    genres: Annotated[list[str] | None, typer.Option("-g", "--genre")] = None,
    year_from: Annotated[int | None, typer.Option("--from")] = None,
    year_to: Annotated[int | None, typer.Option("--until")] = None,
    min_votes: int = 100,
    sort_by: Annotated[SortCriteria, typer.Option("-s", "--sort-by")] = SortCriteria.vote_average,
    ascending: Annotated[bool, typer.Option("-a", "--ascending")] = False,
    n_results: int = 20,
    output: Annotated[list[str], typer.Option("-o")] = TMDB_DEFAULT_OUTPUT_FIELDS,
) -> None:
    """
    Query TMDB discover lists.
    """
    with TMDBClient(tmdb_api_token=ctx.obj["tmdb_api_token"]) as tmdb:
        try:
            data = tmdb.discover(
                category=category,
                genres=genres,
                year_from=year_from,
                year_to=year_to,
                min_votes=min_votes,
                sort_by=sort_by,
                ascending=ascending,
                n_results=n_results,
            )
        except GenreError as e:
            logger.critical(f"{e} Aborting")
            raise typer.Exit(1)

    console.print_item_list(data, output)
