import logging
import os
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich import print

from proxima import get_version
from proxima import set_logging_level
from proxima.tmdb_client import TMDBClient

proxima = typer.Typer()

logger = logging.getLogger(__name__)


def _load_api_key() -> str:
    load_dotenv(".env")
    api_key = os.getenv("TMDB_API_TOKEN")
    if api_key is None:
        logger.critical("API key not found")
        raise typer.Exit(1)
    return api_key


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
    """Weather forecast app"""
    ctx.ensure_object(dict)

    if debug_mode:
        set_logging_level(level=logging.DEBUG)

    ctx.obj["debug"] = debug_mode
    ctx.obj["api_token"] = _load_api_key()


def _parse_output(data: list[dict[str, str]], output: list[str] | None = None) -> list[dict[str, str]]:
    if not output:
        return data

    parsed_data = []
    for item in data:
        parsed_data.append({o: item[o] for o in output})
    return parsed_data


def _print_output(data: list[dict[str, str]], output: list[str] | None = None) -> None:
    parsed_data = _parse_output(data=data, output=output)
    for idx, item in enumerate(parsed_data):
        print(f"- {idx + 1}: -------")
        print(item)
    print(f"Showed {len(data)} results.")


@proxima.command()
def discover_movies(
    ctx: typer.Context,
    year_from: Annotated[int | None, typer.Option("--from")] = None,
    year_to: Annotated[int | None, typer.Option("--until")] = None,
    min_votes: int = 1000,
    n_results: int = 50,
) -> None:
    """
    TMDB discover movies
    """
    tmdb = TMDBClient(api_token=ctx.obj["api_token"])

    data = tmdb.discover_movies(year_from=year_from, year_to=year_to, min_votes=min_votes, n_results=n_results)
    _print_output(data, ["title", "vote_average", "overview"])


@proxima.command()
def discover_tv(
    ctx: typer.Context,
    year_from: Annotated[int | None, typer.Option("--from")] = None,
    year_to: Annotated[int | None, typer.Option("--until")] = None,
    min_votes: int = 1000,
    n_results: int = 50,
) -> None:
    """
    TMDB discover tv series
    """
    tmdb = TMDBClient(api_token=ctx.obj["api_token"])

    data = tmdb.discover_tv(year_from=year_from, year_to=year_to, min_votes=min_votes, n_results=n_results)
    _print_output(data, ["name", "vote_average", "overview"])
