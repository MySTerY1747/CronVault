#  backup.py
#  functions for backup execution, directory copying, and cleanup

import send2trash
import logging
import json
import shutil
import pathvalidate
from datetime import datetime
from pathlib import Path
from CronVault.core.config import BackupConfig
from CronVault.core.constants import (
    CONFIG_LOCATION,
    CRONVAULT_MARKER_FILENAME,
    MAX_DELETE_OLD_BACKUP_ATTEMPTS,
)
from jsonschema import ValidationError


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
    config_file_path = file_path / f"{name}.json"
    try:
        if config_file_path.exists():
            config = BackupConfig.from_file(config_file_path)

            time_period_elapsed = config.is_due()
            is_active = config.is_active()

            was_performed = False
            if skip_checks or (time_period_elapsed and is_active):
                was_performed = perform_backup(config)
            if (not skip_checks) and (not time_period_elapsed):
                logging.info("Skipping backup: time period has not yet elapsed")
            elif (not skip_checks) and (not is_active):
                logging.info("Skipping backup: not currently active")

            if was_performed:
                config.record_successful_backup(file_path)

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


def perform_backup(config: BackupConfig, path_override: Path | None = None) -> bool:
    #  in the future, add notification support
    #  and option to zip by default
    logging.info(f"Performing backup for config {config.name}")
    backup_folder_path = Path(path_override) if path_override else config.destination
    destination: Path | None = None

    try:
        destination_ending = config.get_destination_name()
        destination = (
            config.destination / destination_ending
            if path_override is None
            else path_override / destination_ending
        )

        if not pathvalidate.is_valid_filepath(destination, platform="auto"):
            logging.error(
                f"Error: filepath {destination} is not valid. Backup cannot be performed. Exiting"
            )
            return False

        folder_path_size = get_directory_size(config.path)
        free_device_space = get_device_free_space(backup_folder_path)
        for _ in range(MAX_DELETE_OLD_BACKUP_ATTEMPTS):
            exceeds_storage_limit: bool = (
                folder_path_size + get_directory_size(backup_folder_path)
                #  backup folder size should be checked on every iteration, as we are sending to trash
            ) > config.max_backup_size or (folder_path_size > free_device_space)
            if not exceeds_storage_limit:
                logging.info("Enough space to perform backup. Proceeding.")
                break

            oldest_backup = find_oldest_backup(backup_folder_path)
            if oldest_backup is None:
                logging.error(
                    f"Not enough space in {backup_folder_path} to back up {config.path}. Exiting"
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
        logging.info(f"Copying contents of {config.path} to {destination}...")
        config.path.copy_into(destination, preserve_metadata=True)  # pyright: ignore
        logging.info("Copying complete")
        cronvault_marker = destination / CRONVAULT_MARKER_FILENAME
        cronvault_marker.write_text(
            generate_cronvault_marker(config.path, backup_folder_path)
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


if __name__ == "__main__":
    pass
