import logging
from typing import Annotated

import typer
from rich import print

from proxima import get_version
from proxima import set_logging_level

proxima = typer.Typer()

logger = logging.getLogger(__name__)


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


@proxima.command()
def hello(name: str) -> None:
    """
    Hello there!
    """
    print(f"Hello there! {name}.")
