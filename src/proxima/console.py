import itertools
import logging

import typer
from rich.columns import Columns
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from proxima.data import TMDBItem

logger = logging.getLogger(__name__)


COLOR_PALETTE = [
    38,  # "deep_sky_blue2"
    141,  # "medium_purple1"
    3,  # "yellow"
    202,  # "orange_red1"
    36,  # "dark_cyan"
    162,  # "deep_pink3"
    229,  # "wheat1"
    225,  # "thistle1"
    122,  # "aquamarine1"
]

PAD = (0, 1)
CONSOLE = Console()


def print_genres(genres_list: list[str], category: str) -> None:
    """
    Prints the available genre categories in TMDB to the console.

    Args:
        genres_list: List of genre categories.
        category: Media category they belong to.

    """
    columns = Columns(
        [Text(genre, style=f"color({ci})") for ci, genre in zip(itertools.cycle(COLOR_PALETTE), genres_list)],
        padding=(1, 4),
        align="left",
    )
    CONSOLE.print(Panel(columns, title=f"TMDB {category} genres", title_align="left", padding=(1, 1)))


def print_item_list(
    item_list: list[TMDBItem],
    fields: list[str],
) -> None:
    """
    Prints a list of TMDB items to the console, showing the provided fields.

    Args:
        item_list: The list to be printed.
        fields: List of TMDBItem fields to print.

    """
    fields_not_found = [f for f in fields if not hasattr(item_list[0], f)]
    if fields_not_found:
        joined = "', '".join(fields_not_found)
        logger.critical(f"Fields '{joined}' not found in TMDB item.")
        raise typer.Exit(1)

    for idx, item in enumerate(item_list):
        grid = Table.grid(expand=True)
        grid.add_column()
        grid.add_column(overflow="fold", ratio=1)
        for color, key in zip(itertools.cycle(COLOR_PALETTE), fields):
            content = getattr(item, key)
            if isinstance(content, list):
                content = ", ".join(content)
            grid.add_row(
                Padding(Text(f"{key.replace('_', ' ').capitalize()}:", style=f"bold color({color})"), pad=PAD),
                Padding(Text(str(content), style=f"color({color})"), pad=PAD),
            )

        CONSOLE.print(Panel(grid, title=f"{idx + 1}", title_align="left"))
