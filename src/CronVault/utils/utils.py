#  utils.py
#  small functions that don't belong with the rest of the code

import os
import json
import re
import logging
from datetime import datetime
import pytimeparse
from pathlib import Path

CONFIG_LOCATION: str = "~/.config/CronVault/"
MAX_NAME_ATTEMPTS: int = 101


def parse_name(name: str) -> str:
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
    raise (OSError)


def parse_size(value: str) -> int:
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

    if os.path.exists(folder_path):
        return folder_path
    else:
        logging.exception(f"Path not found: {folder_path}")
        raise OSError(f"Path not found: {folder_path}")


def parse_name_format(name_format: str) -> str:
    """parses the name format CLI argument. Checks whether it is a valid name format to be used with strftime

    Args:
        name_format: (str) naming format that the backups will follow, uses strftime

    Returns:
        (str) the output name format, or OSError
    """
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


def get_default_backup_name(directory: str) -> str:
    """Return appropriate default name when user has not set it. By default set to last element of the path. Appended with `_num` until it's unique

    Args:
        directory: (str) directory returned by parse_path for the `-p` CLI arg
    Returns:
        (str) last elm of directory, appended if necessary until unique
    """
    assert type(directory) is str and len(directory) > 0

    #  directory arg has gone through parse_path. assuming it's valid
    directory_path = Path(directory)
    last_path_elm = directory_path.name
    count: int = 0
    while count < MAX_NAME_ATTEMPTS:
        try:
            name_to_try: str = (
                last_path_elm if count == 0 else last_path_elm + f"_{count}"
            )
            if parse_name(name_to_try) == name_to_try:
                return name_to_try
        except ValueError:
            count += 1
    return ""


def convert_user_args_json(
    name: str,
    max_backup_size: int,
    path: str,
    name_format: str,
    destination: str,
    time_period: int,
) -> str:
    """Convert user backup args to JSON, to then be passed to a write function

    Args:
        name: name for the unique backup
        max_backup_size: maximum backup size
        path: path to back up
        name_format: naming scheme to follow
        destination: path in whic backups are stored
        time_period: time period in seconds

    Output:
        (str) JSON-formatted object representing user args, ready to be written
    """
    #  all args have gone through the parsers first
    #  so no type checking required
    args_json = json.dumps(
        {
            "name": name,
            "max_backup_size": max_backup_size,
            "path": path,
            "name_format": name_format,
            "destination": destination,
            "time_period": time_period,
            "last_known_backup": None,
            "total_backup_count": 0,
            "status": "active",
        }
    )
    logging.info("Converted user args to JSON")
    return args_json


def get_config_path(name: str, base_path: Path = Path(CONFIG_LOCATION)) -> Path:
    """Takes an optional base config path (default is `~/.config/CronVault/`), ensures it exists, and that the file `{base_path}/{name}.json` is not already present

    Args:
        name: `str` the name of the file that will be stored
        base_path: `Path` the initial path to which the name is added. Default is `~/.config/CronVault/`

    Returns:
        `Path` the path to write the data (if successful). Otherwise raises an error
    """
    if not (base_path.is_dir()):
        base_path.mkdir()

    file_path: Path = base_path / f"{name}.json"
    if file_path.exists():
        logging.error(f"File {file_path} already exists.")
        raise ValueError(f"File {file_path} already exists.")

    return file_path


def write_file(file_path: Path, contents: str) -> None:
    try:
        with open(file_path, "w") as f:
            f.write(contents)
    except OSError as e:
        logging.exception(f"Error writing file {file_path}: {e}")
        raise OSError(f"Error writing file {file_path}: {e}")

    logging.info(f"File {file_path} successfully written")


if __name__ == "__main__":
    pass
