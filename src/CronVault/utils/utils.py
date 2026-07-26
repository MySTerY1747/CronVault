#  utils.py
#  small functions that don't belong with the rest of the code

import os
import json
import re
import logging
import pathvalidate
import send2trash
from datetime import datetime
import pytimeparse
import shutil
from pathlib import Path
from typing import Any
from colorama import Fore, Style
from jsonschema import ValidationError, validate, FormatChecker
from .json_schema import SCHEMA

CONFIG_LOCATION: str = "~/.config/CronVault/"
MAX_NAME_ATTEMPTS: int = 101
MAX_DELETE_OLD_BACKUP_ATTEMPTS: int = 10
CRONVAULT_MARKER_FILENAME: str = ".cronvault_marker.json"


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
        raise


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

    if os.path.exists(os.path.expanduser(folder_path)):
        return os.path.expanduser(folder_path)
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
    base_path = base_path.expanduser()
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


def get_all_backups(file_path: Path = Path(CONFIG_LOCATION)) -> list[dict[str, Any]]:
    configs: list[dict[str, Any]] = []

    try:
        filenames = file_path.expanduser().glob("*.json")

        #  look into paralelizing for loop in the future
        logging.info("Iterating through list of config files")
        for config in filenames:
            logging.info(f"Opening file {config}")
            with open(config) as f:
                try:
                    contents = json.load(f)
                    validate(
                        instance=contents, schema=SCHEMA, format_checker=FormatChecker()
                    )
                    configs.append(contents)
                except (json.JSONDecodeError, ValidationError) as e:
                    logging.error(
                        f"Error with config file {config} when trying to read JSON. Skipping file. For more detail use --verbose"
                    )
                    logging.info(f"{e}")
                    continue

    except OSError as e:
        logging.exception(f"Error when trying to read file: {e}")
        raise

    return configs


def filter_configs_active(configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    logging.info("Filtering through configs to get active ones")
    filtered_list: list[dict[str, Any]] = []

    for config in configs:
        if config.get("status", None) == "active":
            filtered_list.append(config)

    return filtered_list


def filter_configs_inactive(configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    logging.info("Filtering through configs to get inactive ones")
    filtered_list: list[dict[str, Any]] = []

    for config in configs:
        if config.get("status", None) == "inactive":
            filtered_list.append(config)

    return filtered_list


def print_configs(configs: list[dict[str, Any]]) -> None:
    """Prints all active configs with proper highlighting and color support"""
    logging.info("Printing configs")

    print(Fore.CYAN + Style.BRIGHT + "CONFIGS:")
    print("=" * 40 + "\n")

    if len(configs) == 0:
        return
    max_width = max(len(config["name"]) for config in configs)
    for config in configs:
        is_active: bool = config["status"] == "active"
        print(f"• {config['name']:<{max_width}}: ", end="")
        print((Fore.GREEN if is_active else Fore.RED) + f"{config['status']}")


def change_backup_status(
    name: str, status: str, file_path: Path = Path(CONFIG_LOCATION).expanduser()
) -> None:
    if status not in ("active", "inactive"):
        logging.error(f'"{status}" is not a valid config status. Exiting')
        return
    logging.info(f"Changing activity status of config {name} to {status}")

    file_path = file_path / f"{name}.json"
    try:
        if file_path.exists():
            config = json.loads(file_path.read_text())
            validate(instance=config, schema=SCHEMA, format_checker=FormatChecker())
            config["status"] = status
            file_path.write_text(json.dumps(config))
            logging.info("Successfully changed file contents")
        else:
            logging.error(f"No such config found: {name}. Exiting")
    except (json.JSONDecodeError, ValidationError) as e:
        logging.error(
            f'Config file "{name}" is malformed or corrupted. View details with --verbose'
        )
        logging.debug(e)
    except IOError:
        logging.error(f"Encountered IOError while trying to edit config file {name}")
        raise


def delete_backup(
    name: str, file_path: Path = Path(CONFIG_LOCATION).expanduser()
) -> None:
    logging.info(f'Attempting to delete backup "{name}"')
    file_path = file_path / f"{name}.json"
    try:
        if file_path.exists():
            send2trash.send2trash(file_path)
            logging.info("Successfully deleted file")
        else:
            logging.error(f"No such config found: {name}. Exiting")
    except OSError:
        logging.error(f"Encountered IOError while trying to delete config file {name}")
        raise


def get_directory_size(path: Path) -> int:
    return sum(
        f.stat(follow_symlinks=False).st_size for f in path.rglob("*") if f.is_file()
    )


def run_backup_if_needed(
    name: str,
    skip_checks: bool = False,
    file_path: Path = Path(CONFIG_LOCATION).expanduser(),
) -> None:
    logging.info(f'Attempting to backup "{name}"')
    file_path = file_path / f"{name}.json"
    try:
        if file_path.exists():
            config = json.loads(file_path.read_text())
            validate(instance=config, schema=SCHEMA, format_checker=FormatChecker())

            previous_backup = config["last_known_backup"]
            if previous_backup is None:
                previous_backup = datetime.fromisoformat("1970-01-01")
            else:
                previous_backup = datetime.fromisoformat(previous_backup)

            time_period_elapsed = (
                datetime.now() - previous_backup
            ).total_seconds() >= config["time_period"]

            is_active: bool = config["status"] == "active"

            was_performed = False
            if skip_checks or (time_period_elapsed and is_active):
                was_performed = perform_backup(config)
            if (not skip_checks) and (not time_period_elapsed):
                logging.info("Skipping backup: time period has not yet elapsed")
            elif (not skip_checks) and (not is_active):
                logging.info("Skipping backup: not currently active")

            # TODO: Separate out this if statement into a `record_backup` function
            if was_performed:
                config["last_known_backup"] = datetime.now().isoformat()
                config["total_backup_count"] += 1
                file_path.write_text(json.dumps(config))

                logging.info(
                    f"Successfully backed up {name}, and wrote changes to config"
                )
        else:
            logging.error(f"No such config found: {name}. Exiting")
    except (json.JSONDecodeError, ValidationError) as e:
        logging.error(
            f'Config file "{name}" is malformed or corrupted. View details with --verbose'
        )
        logging.debug(e)
    except OSError:
        logging.error(f"Encountered OSError while trying to access config file {name}")
        raise


def find_oldest_backup(file_path: Path) -> Path | None:
    """
    Finds oldest CronVault backup in `file_path`. Skips other directories
    """
    result: Path | None = None
    logging.info(f"Finding oldest backup in {file_path}")
    try:
        if len(list(file_path.iterdir())) == 0:
            return None

        creation_dates = {}

        #  use marker to ensure backup is from CronVault
        for subdirectory in file_path.iterdir():
            backup_marker = subdirectory / CRONVAULT_MARKER_FILENAME
            if backup_marker.exists():
                #  use recorded timestamp instead of stat().st_birthtime
                #  to ensure consistency and reliability across OSs
                try:
                    backup_date = json.loads(backup_marker.read_text())[
                        "backup_datetime"
                    ]
                    creation_dates[backup_date] = subdirectory
                except (json.JSONDecodeError, KeyError):
                    logging.error(f"CronVault marker for backup {file_path} corrupted.")
                    continue

        if creation_dates:
            oldest_backup_time = min(
                creation_dates
            )  #  should work thanks to ISO format
            result = creation_dates[oldest_backup_time]
            logging.info(f"Oldest directory in {file_path} is {result}")
            return result

    except OSError:
        logging.error(f"Error while trying to access backups in {file_path}. Aborting")
        raise

    logging.info(f"Found no CronVault backups in path {file_path}")
    return result


def generate_cronvault_marker(folder_path: Path, backup_folder_path: Path) -> str:
    marker = {
        "original_folder": str(folder_path),
        "backup_datetime": datetime.now().isoformat(),
        "backup_folder_path": str(backup_folder_path),
    }
    return json.dumps(marker)


def get_device_free_space(backup_folder_path: Path) -> int:
    _, _, free = shutil.disk_usage(backup_folder_path)
    return free


def cleanup_failed_backup(backup_folder_path: Path) -> bool:
    """
    Moves the given path to the system trash.

    WARNING:
    This permanently removes the backup from CronVault's perspective.
    """
    logging.info(f"Attempting to clean failed backup {backup_folder_path}")
    if not backup_folder_path.exists():
        return True
    try:
        send2trash.send2trash(backup_folder_path)
        return True
    except (OSError, IOError):
        logging.error("Unable to clean failed backup.")
    return False


def perform_backup(config: dict[str, Any], path_override: Path | None = None) -> bool:
    """config must be valid and already checked"""
    #  in the future, add notification support
    logging.info(f"Performing backup for config {config['name']}")
    folder_path = Path(config["path"])
    backup_folder_path = (
        Path(path_override) if path_override else Path(config["destination"])
    )
    max_storage_limit = config["max_backup_size"]
    destination: Path | None = None

    try:
        backup_name = datetime.strftime(datetime.now(), config["name_format"])
        destination = backup_folder_path / backup_name

        if not pathvalidate.is_valid_filepath(destination, platform="auto"):
            logging.error(
                f"Error: filepath {destination} is not valid. Backup cannot be performed. Exiting"
            )
            return False

        folder_path_size = get_directory_size(folder_path)
        free_device_space = get_device_free_space(backup_folder_path)
        for _ in range(MAX_DELETE_OLD_BACKUP_ATTEMPTS):
            exceeds_storage_limit: bool = (
                folder_path_size + get_directory_size(backup_folder_path)
                #  backup folder size should be checked on every iteration, as we are sending to trash
            ) > max_storage_limit or (folder_path_size > free_device_space)
            if not exceeds_storage_limit:
                logging.info("Enough space to perform backup. Proceeding.")
                break

            oldest_backup = find_oldest_backup(backup_folder_path)
            if oldest_backup is None:
                logging.error(
                    f"Not enough space in {backup_folder_path} to back up {folder_path}. Exiting"
                )
                return False

            #  probably smarter idea to send backup to trash than immediately delete
            logging.info(
                f"Not enough storage space to backup. Sending oldest backup: {oldest_backup} to trash"
            )
            send2trash.send2trash(oldest_backup)
            #  maybe good idea to ask user before deleting
            #  but that eliminates automation

        else:
            logging.error(
                "Reached maximum number of older backup deletion attempts. User intervention requried."
            )
            return False

        if destination.exists():
            logging.error(f"Destination path {destination} already exists. Aborting...")
            return False

        destination.mkdir()

        #  `copy_into` was introduced in Python 3.14. This line should work, but pyright isn't picking it up for some reason...
        logging.info(f"Copying contents of {folder_path} to {destination}...")
        folder_path.copy_into(destination, preserve_metadata=True)  # pyright: ignore
        logging.info("Copying complete")
        cronvault_marker = destination / CRONVAULT_MARKER_FILENAME
        cronvault_marker.write_text(
            generate_cronvault_marker(folder_path, backup_folder_path)
        )
        logging.info(f"Wrote CronVault marker to {cronvault_marker}")
        return True
    except PermissionError as e:
        logging.error(
            f"WARNING: Certain files were skipped due to permission errors {e}"
        )
        if destination:
            cleanup_failed_backup(destination)
        return False
    except OSError as e:
        logging.error(
            f"Encountered OSError while performing backup. Aborting... \n\n {e}"
        )
        if destination:
            was_cleaned = cleanup_failed_backup(destination)
            if was_cleaned:
                logging.info("Successfully cleaned failed backup")
            else:
                logging.info("Failed to clean up. Exiting.")
            return False
        raise


if __name__ == "__main__":
    pass
