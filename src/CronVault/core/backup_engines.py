#  backup_engines.py
#  contains implementations and mappings for the different available backup engines

import logging
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Callable

from CronVault.core.constants import CRONVAULT_MARKER_FILENAME


def copy_engine(source: Path, destination: Path, marker_content: str) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    logging.info(
        f"Copying contents of {source} to {destination} using standard folder copy engine"
    )
    source.copy_into(destination, preserve_metadata=True)  # pyright: ignore
    logging.info("Copying complete")
    cronvault_marker_path = destination / CRONVAULT_MARKER_FILENAME
    cronvault_marker_path.write_text(marker_content)
    logging.info(f"Wrote CronVault marker to {cronvault_marker_path}")


def zip_engine(source: Path, destination: Path, marker_content: str) -> None:
    logging.info(f"Creating ZIP archive from {source} to {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in source.rglob("*"):
            if item.is_file():
                archive.write(item, arcname=item.relative_to(source))

        archive.writestr(CRONVAULT_MARKER_FILENAME, marker_content)


def rsync_engine(source: Path, destination: Path, marker_content: str) -> None:
    if shutil.which("rsync") is None:
        logging.error("No rsync library found on the system")
        raise FileNotFoundError(
            "rsync binary is required for the rsync engine, but was not found in $PATH"
        )

    destination.mkdir(parents=True, exist_ok=True)
    logging.info(f"Executing rsync from {source} to {destination}")
    source_str = (
        str(source).rstrip("/") + "/"
    )  #  ensure source ends in trailing slash to copy directory contents
    dest_str = str(destination).rstrip("/") + "/"
    cmd = ["rsync", "-a", "--delete", source_str, dest_str]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logging.error(f"Rsync failed with code {result.returncode}: {result.stderr}")
        raise RuntimeError(f"Rsync execution failed: {result.stderr.strip()}")

    logging.info("Rsync completed successfully")
    marker_path = destination / CRONVAULT_MARKER_FILENAME
    marker_path.write_text(marker_content)
    logging.info(f"Wrote CronVault marker to {marker_path}")


ENGINE_REGISTRY: dict[str, Callable[[Path, Path, str], None]] = {
    "copy": copy_engine,
    "zip": zip_engine,
    "rsync": rsync_engine,
}
