#  parse_functions.py
#  functions to parse CLI arguments

import logging
import re
import pytimeparse
from datetime import datetime
from pathlib import Path


NAME_DEFAULT: str = "NoName"
FIFTY_GB: int = 53_687_091_200  #  50GB
CONFIG_LOCATION: str = "~/.config/CronVault/"


def parse_name(name: str) -> str:
    if not name:
        return NAME_DEFAULT
    if not isinstance(name, str) or not name:
        raise ValueError(f"Invalid config name: {name}")
    return name


def parse_size(value: str | None) -> int:
    if not value:
        return FIFTY_GB
    if not isinstance(value, str) or len(value) < 1:
        raise ValueError(f"Invalid size: {value}")
    pattern = r"^(\d+)([KMGTP]?B?)?$"
    match = re.fullmatch(pattern, value.strip().upper())
    if not match:
        logging.error("Invalid size")
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
    path: Path = Path(folder_path).expanduser().resolve()

    if not path.exists():
        logging.exception(f"Path not found: {folder_path}")
        raise OSError(f"Path not found: {folder_path}")
    if not path.is_dir():
        logging.exception(f"Path is not a directory: {folder_path}")
        raise NotADirectoryError(f"Path is not a directory: {folder_path}")

    return str(path)


def parse_name_format(name_format: str | None) -> str:
    """parses the name format CLI argument. Checks whether it is a valid name format to be used with strftime

    Args:
        name_format: (str) naming format that the backups will follow, uses strftime

    Returns:
        (str) the output name format, or OSError
    """
    if not name_format:
        return NAME_DEFAULT
    if len(name_format) > 200:
        raise ValueError("Name format too long. Maximum character limit is 200")
    example_output_name = datetime.now().strftime(name_format)
    if len(example_output_name) < 1:
        raise ValueError(
            f"Invalid format: {name_format} expands to {example_output_name}"
        )

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
