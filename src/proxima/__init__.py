import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

VERSION = "0.1.0"
LOG_CONSOLE = Console(stderr=True)


def get_version() -> str:
    return VERSION


def get_resource(file_name: str) -> Path:
    """Returns file path from application resource file"""
    return Path(__file__).parent / "resources" / file_name


def _init_logging() -> None:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = RichHandler(console=LOG_CONSOLE, omit_repeated_times=False)
    logger.addHandler(handler)


def set_logging_level(level: int = logging.DEBUG) -> None:
    """
    Set the logging level for the whole package.

    Args:
        level: Logging level.

    """
    logger = logging.getLogger(__name__)
    logger.setLevel(level)


_init_logging()
