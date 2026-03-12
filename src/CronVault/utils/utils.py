#  utils.py
#  small functions that don't belong with the rest of the code

import os
import re
import logging

CONFIG_LOCATION: str = "~/.config/CronVault/"


def parse_name(name: str) -> bool:
    assert (type(name) is str) and (len(name) >= 1)
    config_folder: str = os.path.expanduser(CONFIG_LOCATION)
    try:
        if not os.path.exists(config_folder):
            logging.info("Config directory does not exist. Creating now.")
            os.makedirs(config_folder)
        backups: list[str] | None = os.listdir(config_folder)
        #  i know we can return directly here
        #  but here this is done for readability
        if (backups is None) or (name in backups):
            return False
        return True
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


def parse_path(folder_path: str) -> bool:
    #  check type and length
    #  check proper formatting
    #  check if path exists
    #  make sure to mock in tests
    assert (type(folder_path) is str) and (len(folder_path) > 0)
    pattern = r"^(.+)\/([^\/]+)$"
    match = re.fullmatch(pattern, folder_path)
    if not match:
        logging.exception(f"Invalid path: {folder_path}")
        raise OSError(f"Invalid path: {folder_path}")

    return os.path.exists(folder_path)


if __name__ == "__main__":
    pass
