#  backup_engines.py
#  contains implementations and mappings for the different available backup engines

import logging
from pathlib import Path
from typing import Callable
from CronVault.core.constants import CRONVAULT_MARKER_FILENAME


def copy_engine(source: Path, destination: Path, marker_content: str) -> None:
    destination.mkdir()
    logging.info(
        f"Copying contents of {source} to {destination} using standard folder copy engine"
    )
    source.copy_into(destination, preserve_metadata=True)  # pyright: ignore
    logging.info("Copying complete")
    cronvault_marker_path = destination / CRONVAULT_MARKER_FILENAME
    cronvault_marker_path.write_text(marker_content)
    logging.info(f"Wrote CronVault marker to {cronvault_marker_path}")


def zip_engine(source: Path, destination: Path, marker_content: str) -> None:
    pass


def rsync_engine(source: Path, destination: Path, marker_content: str) -> None:
    pass


ENGINE_REGISTRY: dict[str, Callable[[Path, Path, str], None]] = {
    "copy": copy_engine,
    "zip": zip_engine,
    "rsync": rsync_engine,
}
