#  utils.py
#  small functions that don't belong with the rest of the code

import json
import re
import logging
import pathvalidate
import send2trash
from datetime import datetime
import shutil
from pathlib import Path
from typing import Any
from colorama import Fore, Style
from jsonschema import ValidationError, validate, FormatChecker

from .json_schema import SCHEMA
from .arguments import create_arguments
from .parse_functions import parse_name, NAME_DEFAULT, CONFIG_LOCATION
from crontab import CronTab, CronItem

CONFIG_FILE_NAME: str = "CronVault.conf"
MAX_NAME_ATTEMPTS: int = 101
MAX_DELETE_OLD_BACKUP_ATTEMPTS: int = 10
CRONVAULT_MARKER_FILENAME: str = ".cronvault_marker.json"
DEFAULT_BACKUP_CHECK_INTERVAL_MINUTES: int = 10  #  run check every 10 minutes
CRON_JOB_COMMENT: str = "Automated CronVault check. Minute frequency:"


def get_default_backup_name(directory: str) -> str:
    """Return appropriate default name when user has not set it. By default set to last element of the path. Appended with `_num` until it's unique

    Args:
        directory: (str) directory returned by parse_path for the `-p` CLI arg
    Returns:
        (str) last elm of directory, appended if necessary until unique
    """
    if not isinstance(directory, str) or len(directory) < 1:
        raise ValueError(f"Invalid directory path: {directory}")

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


def get_config_path(
    name: str, base_path: Path = Path(CONFIG_LOCATION).expanduser()
) -> Path:
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
    #  and option to zip by default
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
        logging.error(f"Encountered OSError while performing backup. Aborting... {e}")
        if destination:
            was_cleaned = cleanup_failed_backup(destination)
            if was_cleaned:
                logging.info("Successfully cleaned failed backup")
            else:
                logging.info("Failed to clean up. Exiting.")
            return False
        raise


def generate_default_config(
    file_path: Path = Path(CONFIG_LOCATION).expanduser(),
) -> None:
    config = {"backup_frequency_minutes": DEFAULT_BACKUP_CHECK_INTERVAL_MINUTES}
    file_path.mkdir(parents=True, exist_ok=True)
    config_filepath = file_path / CONFIG_FILE_NAME
    config_filepath.write_text(json.dumps(config))


def get_backup_frequency_from_config(config_dir: Path) -> int:
    config_file_path = config_dir / CONFIG_FILE_NAME
    if not config_file_path.exists():
        logging.info("No config file found. Creating now")
        generate_default_config(config_dir)
    config = json.loads(config_file_path.read_text())
    frequency = config.get("backup_frequency_minutes", None)
    if not isinstance(frequency, int) or frequency <= 0:
        #  only need a single property, no need for entire JSON schema (yet)
        logging.error(
            f"Corrupted/invalid config file: {config_file_path}. 'backup_frequency_minutes' property is missing or invalid"
        )
        raise ValueError(
            f"Corrupted/invalid config file: {config_file_path}. 'backup_frequency_minutes' property is missing or invalid"
        )
    return config["backup_frequency_minutes"]


def ensure_single_cron_job(
    cronvault_jobs: list[CronItem], backup_check_frequency: int
) -> bool:
    job_exists = False

    #  only keep one active job, with correct backup check frequency
    logging.info(f"Iterating through {len(cronvault_jobs)} cron job(s)")
    for job in cronvault_jobs:
        if job.is_enabled() and job.is_valid():
            if job_exists:
                job.delete()
                continue

            prefix = f"{CRON_JOB_COMMENT}"
            if not job.comment.startswith(prefix):
                logging.error("Invalid CronVault job found. Deleting")
                job.delete()
                continue

            try:
                interval = int(job.comment.removeprefix(prefix))
            except ValueError:
                logging.error("Invalid CronVault job found. Deleting.")
                job.delete()
                continue

            if interval == backup_check_frequency:
                logging.info("Job already exists with proper frequency.")
                job_exists = True
            else:
                #  pyright thinks `minute` is an int
                job.minute.every(backup_check_frequency)  #  pyright: ignore
                job.comment = f"{CRON_JOB_COMMENT} {backup_check_frequency}"
                job_exists = True
    return job_exists


def add_cron_job(config_path: Path = Path(CONFIG_LOCATION).expanduser()) -> None:
    try:
        logging.info("Checking whether cron job exists")
        backup_check_frequency: int = get_backup_frequency_from_config(config_path)
        logging.info("Reading user crontab")
        cron = CronTab(user=True)
        cronvault_jobs = list(cron.find_comment(re.compile(f"{CRON_JOB_COMMENT}")))

        job_exists = ensure_single_cron_job(cronvault_jobs, backup_check_frequency)

        if not job_exists:
            logging.info("No cron job found. Creating now")
            job = cron.new(
                command="cronvault backup -a",
                comment=f"{CRON_JOB_COMMENT} {backup_check_frequency}",
            )
            job.minute.every(backup_check_frequency)  #  pyright: ignore
        cron.write()
    except OSError as e:
        logging.exception(f"Got OSError while going through Cron jobs: {e}")
        raise


def fill_missing_create_args(args: dict[str, Any]) -> None:
    if args["name"] == NAME_DEFAULT:
        logging.info("No name specified. Setting it based on directory")
        args["name"] = get_default_backup_name(args["path"])
        logging.info(f"Backup name now set to {args['name']}")

    if args["naming_format"] == NAME_DEFAULT:
        logging.info("No naming format specified. Setting it based on name")
        args["naming_format"] = f"{args['name']} %Y-%m-%d_%H-%M-%S"
        logging.info(f"Backup naming scheme now set to {args['naming_format']}")


def interactive_config_creator(args: dict[str, Any]) -> None:
    print(Fore.CYAN + Style.BRIGHT + "Interactive Config Creator:")
    print(Fore.LIGHTWHITE_EX + Style.DIM + "Skipping any arguments already given")
    print("=" * 40 + "\n")

    for argument in create_arguments:
        arg_value = args.get(argument.name)
        if arg_value is not None:
            continue

        print(Fore.LIGHTBLUE_EX + Style.BRIGHT + argument.prompt, end="")
        user_input = input()
        user_input = argument.parser(user_input)
        args[argument.name] = user_input
        logging.info(f"Input for {argument.name} received and parsed: {user_input}")
        print("=" * 40 + "\n")


def create_backup_from_args(args_dict: dict[str, Any]) -> None:
    required_args = ("path", "destination", "time_period")

    if not all([args_dict.get(argument) is not None for argument in required_args]):
        interactive_config_creator(args_dict)
    fill_missing_create_args(args_dict)

    file_path = get_config_path(args_dict["name"])
    contents = convert_user_args_json(
        args_dict["name"],
        args_dict["max_backup_size"],
        args_dict["path"],
        args_dict["naming_format"],
        args_dict["destination"],
        args_dict["time_period"],
    )
    write_file(file_path, contents)
    logging.info("Successfully wrote backup configuration file")


if __name__ == "__main__":
    pass
