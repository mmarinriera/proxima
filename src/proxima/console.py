import itertools
from typing import Any

from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

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


def print_item_list(
    item_list: list[dict[str, Any]],
    fields: list[str] | None = None,
) -> None:
    if fields is None:
        fields = list(item_list[0].keys())

    for idx, item in enumerate(item_list):
        grid = Table.grid(expand=True)
        grid.add_column()
        grid.add_column()
        for ci, key in zip(itertools.cycle(COLOR_PALETTE), fields):
            grid.add_row(
                Padding(Text(f"{key}:", style=f"bold color({ci})"), pad=PAD),
                Padding(Text(str(item[key]), style=f"color({ci})"), pad=PAD),
            )

        CONSOLE.print(Panel(grid, title=f"{idx + 1}", title_align="left"))
