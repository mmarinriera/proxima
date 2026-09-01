import logging
import os
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich import print

from proxima import console
from proxima import get_version
from proxima import set_logging_level
from proxima.fluvial_client import FluvialClient
from proxima.tmdb_client import GenreError
from proxima.tmdb_client import MediaCategory
from proxima.tmdb_client import TMDBClient

proxima = typer.Typer()

logger = logging.getLogger(__name__)

TMDB_DEFAULT_OUTPUT_FIELDS = ["title", "genres", "vote_average", "overview"]

FLUVIAL_DEFAULT_SITE = "piratebay"
FLUVIAL_DEFAULT_OUTPUT_FIELDS = ["name", "seeders", "magnet"]


def _load_env(ctx: typer.Context) -> None:
    load_dotenv(".env")
    tmdb_api_key = os.getenv("TMDB_API_TOKEN")
    if tmdb_api_key is None:
        logger.critical("TMDB API key not found")
        raise typer.Exit(1)

    ctx.obj["tmdb_api_token"] = tmdb_api_key

    fluvial_api_url = os.getenv("FLUVIAL_API_URL")
    if fluvial_api_url is None:
        logger.critical("Fluvial API URL not found")
        raise typer.Exit(1)

    ctx.obj["fluvial_api_url"] = fluvial_api_url


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
def tmdb_genres(ctx: typer.Context, category: MediaCategory) -> None:
    """TMDB movie genres"""
    with TMDBClient(tmdb_api_token=ctx.obj["tmdb_api_token"]) as tmdb:
        data = tmdb.get_genres(category=category)
    console.print_genres(data, category.value)


@proxima.command()
def tmdb_discover(
    ctx: typer.Context,
    category: MediaCategory,
    genres: Annotated[list[str] | None, typer.Option("-g", "--genre")] = None,
    year_from: Annotated[int | None, typer.Option("--from")] = None,
    year_to: Annotated[int | None, typer.Option("--until")] = None,
    min_votes: int = 1000,
    n_results: int = 50,
    output: Annotated[list[str], typer.Option("-o")] = TMDB_DEFAULT_OUTPUT_FIELDS,
) -> None:
    """
    TMDB discover
    """
    with TMDBClient(tmdb_api_token=ctx.obj["tmdb_api_token"]) as tmdb:
        try:
            data = tmdb.discover(
                category=category,
                genres=genres,
                year_from=year_from,
                year_to=year_to,
                min_votes=min_votes,
                n_results=n_results,
            )
        except GenreError as e:
            logger.critical(f"{e} Aborting")
            raise typer.Exit(1)

    console.print_item_list(data, output)


@proxima.command()
def fluvial_search(
    ctx: typer.Context,
    search_query: Annotated[str, typer.Argument(help="Search query.")],
    site: Annotated[str, typer.Option("-s", "--site", help="Search site.")] = FLUVIAL_DEFAULT_SITE,
    n_results: Annotated[int, typer.Option("-n", "--n-results", help="Number of results returned.")] = 50,
    output: Annotated[
        list[str], typer.Option("-o", "--output", help="Specify search result fields to be shown.")
    ] = FLUVIAL_DEFAULT_OUTPUT_FIELDS,
) -> None:
    """
    Search query on Fluvial API
    """
    with FluvialClient(fluvial_api_url=ctx.obj["fluvial_api_url"]) as fluvial:
        try:
            data = fluvial.search(
                site=site,
                query=search_query,
                n_results=n_results,
            )
        except ValueError as e:
            logger.critical(f"{e} Aborting.")
            raise typer.Exit(1)

    console.print_item_list(data, output)
