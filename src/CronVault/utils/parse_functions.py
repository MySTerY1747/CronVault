#  parse_functions.py
#  functions to parse CLI arguments

import os
import logging
import re
import pytimeparse
from datetime import datetime


NAME_DEFAULT: str = "NoName"
FIFTY_GB: int = 53_687_091_200  #  50GB
CONFIG_LOCATION: str = "~/.config/CronVault/"


def parse_name(name: str) -> str:
    if not name:
        return NAME_DEFAULT
    assert (type(name) is str) and (len(name) >= 1)
    config_folder: str = os.path.expanduser(CONFIG_LOCATION)
    try:
        if not os.path.exists(config_folder):
            logging.info("Config directory does not exist. Creating now.")
            os.makedirs(config_folder)
        backups: list[str] | None = os.listdir(config_folder)
        if (
            (backups is None)
            or (name in backups)
            or (name in map(lambda x: x.replace(".json", ""), backups))
        ):
            logging.exception(f"Error: unique name already in use: {name}")
            raise ValueError(f"Error: unique name already in use {name}")
        return name
    except (OSError, FileNotFoundError) as e:
        logging.exception(f"Issue finding config folder: {e}")
        raise


def parse_size(value: str | None) -> int:
    if not value:
        return FIFTY_GB
    assert type(value) is str and len(value) >= 1
    pattern = r"^(\d+)([KMGTP]?B?)?$"
    match = re.fullmatch(pattern, value.strip().upper())
    if not match:
        logging.exception("Invalid size")
        raise ValueError(f"Invalid size: {value}")

    number, unit = match.groups()
    number = int(number)
    multipliers = {
        None: 1,
        "B": 1,
        "K": 1024,
        "KB": 1024,
        "M": 1024**2,
        "MB": 1024**2,
        "G": 1024**3,
        "GB": 1024**3,
        "T": 1024**4,
        "TB": 1024**4,
    }
    return number * multipliers.get(unit, 1)


def parse_path(folder_path: str) -> str:
    assert (type(folder_path) is str) and (len(folder_path) > 0)
    pattern = r"^(.+)\/([^\/]+)$"
    match = re.fullmatch(pattern, folder_path)
    if not match:
        logging.exception(f"Invalid path: {folder_path}")
        raise OSError(f"Invalid path: {folder_path}")

    if os.path.exists(os.path.expanduser(folder_path)):
        return os.path.expanduser(folder_path)
    else:
        logging.exception(f"Path not found: {folder_path}")
        raise OSError(f"Path not found: {folder_path}")


def parse_name_format(name_format: str | None) -> str:
    """parses the name format CLI argument. Checks whether it is a valid name format to be used with strftime

    Args:
        name_format: (str) naming format that the backups will follow, uses strftime

    Returns:
        (str) the output name format, or OSError
    """
    if not name_format:
        return NAME_DEFAULT
    assert len(name_format) < 200
    assert datetime.now().strftime(name_format)

    #  ensure valid output filename
    return re.sub(r"[^A-Za-z0-9.%_-]", "_", name_format)


def parse_time_period(time_period: str) -> int:
    if type(time_period) is not str or len(time_period) < 1:
        logging.exception(f"Invalid string time period: {time_period}")
        raise ValueError(f"Invalid string time period: {time_period}")

    total_seconds: int | float | None = pytimeparse.timeparse.timeparse(time_period)
    if total_seconds is None:
        logging.exception(f"Invalid time period: {time_period}")
        raise ValueError(f"Invalid time period: {time_period}")

    return int(total_seconds)
