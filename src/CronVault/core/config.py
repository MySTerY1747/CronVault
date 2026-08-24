#  config.py
#  Functions for config creation, loading, writing, and duplicate checking

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import logging
import send2trash
import json
from CronVault.core.constants import (
    CONFIG_LOCATION,
    MAX_NAME_ATTEMPTS,
    NAME_DEFAULT,
    CONFIG_FILE_NAME,
    DEFAULT_BACKUP_CHECK_INTERVAL_MINUTES,
)
from CronVault.cli.arguments import create_arguments
from CronVault.cli.parse_functions import parse_name
from CronVault.core.config_json_schema import SCHEMA
from typing import Any
from colorama import Fore, Style
from jsonschema import validate, FormatChecker, ValidationError


@dataclass
class BackupConfig:
    name: str
    path: Path
    destination: Path
    time_period: int
    name_format: str
    max_backup_size: int
    status: str = "active"
    total_backup_count: int = 0
    last_known_backup: datetime | None = None
    engine: str = "copy"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BackupConfig":
        try:
            return cls(
                name=data["name"],
                path=Path(data["path"]),
                destination=Path(data["destination"]),
                time_period=data["time_period"],
                name_format=data.get("name_format") or data["naming_format"],
                max_backup_size=data["max_backup_size"],
                status=data.get("status", "active"),
                total_backup_count=data.get("total_backup_count", 0),
                engine=data.get("engine", "copy"),
                last_known_backup=(
                    datetime.fromisoformat(data["last_known_backup"])
                    if data.get("last_known_backup")
                    else None
                ),
            )
        except KeyError:
            logging.error(
                f"Could not convert dictionary {data} to BackupConfig. Missing one or more properties:"
            )
            raise

    @classmethod
    def from_file(cls, file_path: Path) -> "BackupConfig":
        try:
            if not file_path.exists():
                logging.error(f"Config filepath not found: {file_path}")
                raise FileNotFoundError(f"Config filepath not found: {file_path}")
            config_file = json.loads(file_path.read_text())
            validate(
                instance=config_file, schema=SCHEMA, format_checker=FormatChecker()
            )
            return cls.from_dict(config_file)
        except (json.JSONDecodeError, ValidationError):
            logging.error(
                f'Config file in "{file_path}" is malformed or corrupted. View details with --verbose'
            )
            raise
        except IOError:
            logging.error(
                f"Encountered IOError while trying to read config file {file_path}"
            )
            raise

    @classmethod
    def from_name(
        cls, name: str, file_path: Path = Path(CONFIG_LOCATION).expanduser()
    ) -> "BackupConfig":
        config_filepath = file_path / f"{name}.json"
        return cls.from_file(config_filepath)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": str(self.path),
            "destination": str(self.destination),
            "time_period": self.time_period,
            "name_format": self.name_format,
            "max_backup_size": self.max_backup_size,
            "status": self.status,
            "total_backup_count": self.total_backup_count,
            "engine": self.engine,
            "last_known_backup": (
                self.last_known_backup.isoformat() if self.last_known_backup else None
            ),
        }

    def write_to_config_file(
        self, file_path: Path = Path(CONFIG_LOCATION).expanduser()
    ) -> None:
        try:
            file_path = file_path / f"{self.name}.json"
            file_path.write_text(json.dumps(self.to_dict()))
        except OSError:
            logging.error(
                f"Encountered error while trying to write config to {file_path}"
            )
            raise
        logging.info(f"Successfully wrote config {self.name} to {file_path}")

    def is_due(self) -> bool:
        if self.last_known_backup is None:
            return True

        return datetime.now() - self.last_known_backup >= timedelta(
            seconds=self.time_period
        )

    def record_successful_backup(
        self, file_path: Path = Path(CONFIG_LOCATION).expanduser()
    ) -> None:
        self.last_known_backup = datetime.now()
        self.total_backup_count += 1
        self.write_to_config_file(file_path)

    def is_active(self) -> bool:
        return self.status == "active"
        #  currently treating *all* other values as inactive

    def get_destination_name(self) -> str:
        #  if more engines added in the future, consider match statement
        backup_name = datetime.strftime(datetime.now(), self.name_format)
        if self.engine == "zip":
            backup_name += ".zip"

        return backup_name


def get_default_backup_name(
    directory: str, config_path: Path = Path(CONFIG_LOCATION).expanduser()
) -> str:
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
        name_to_try: str = last_path_elm if count == 0 else f"{last_path_elm}_{count}"
        logging.info(f"Checking if name {name_to_try} is unique")
        if not is_name_duplicate(name_to_try, config_path):
            logging.info(f"Name {name_to_try} is unique. Returning it.")
            return name_to_try
        count += 1
    return ""


def get_all_backups(
    file_path: Path = Path(CONFIG_LOCATION).expanduser(),
) -> list[BackupConfig]:
    configs: list[BackupConfig] = []

    filenames = file_path.glob("*.json")

    #  look into paralelizing for loop in the future
    logging.info("Iterating through list of config files")
    for config in filenames:
        try:
            logging.info(f"Opening file {config}")
            configs.append(BackupConfig.from_file(config))
        except (json.JSONDecodeError, ValidationError, OSError):
            logging.error(
                f"Error with config file {config} when trying to read JSON. Skipping file. For more detail use --verbose"
            )
            continue

    return configs


def filter_configs_active(configs: list[BackupConfig]) -> list[BackupConfig]:
    logging.info("Filtering through configs to get active ones")
    filtered_list: list[BackupConfig] = []

    for config in configs:
        if config.status == "active":
            filtered_list.append(config)

    return filtered_list


def filter_configs_inactive(configs: list[BackupConfig]) -> list[BackupConfig]:
    logging.info("Filtering through configs to get inactive ones")
    filtered_list: list[BackupConfig] = []

    for config in configs:
        if config.status == "inactive":
            filtered_list.append(config)

    return filtered_list


def print_configs(configs: list[BackupConfig]) -> None:
    """Prints all active configs with proper highlighting and color support"""
    logging.info("Printing configs")

    print(Fore.CYAN + Style.BRIGHT + "CONFIGS:")
    print("=" * 40 + "\n")

    if len(configs) == 0:
        return
    max_width = max(len(config.name) for config in configs)
    for config in configs:
        is_active: bool = config.status == "active"
        print(f"• {config.name:<{max_width}}: ", end="")
        print((Fore.GREEN if is_active else Fore.RED) + f"{config.status}")


def change_backup_status(
    name: str, status: str, file_path: Path = Path(CONFIG_LOCATION).expanduser()
) -> None:
    if status not in ("active", "inactive"):
        logging.error(f'"{status}" is not a valid config status. Exiting')
        return
    logging.info(f"Changing activity status of config {name} to {status}")

    try:
        config = BackupConfig.from_name(name, file_path)
        config.status = status
        config.write_to_config_file(file_path)
        logging.info("Successfully changed file contents")
    except FileNotFoundError:
        #  If the file is missing, just log it and return. Don't crash
        logging.error(f"File not found in {file_path}. Skipping")
        return
    except (json.JSONDecodeError, ValidationError):
        #  If the file is malformed, just log it and return. Don't crash
        logging.error(f"File in {file_path} is broken or corrupted. Skipping")
        return


def delete_backup(
    name: str, file_path: Path = Path(CONFIG_LOCATION).expanduser()
) -> None:
    #  This function is so simple, that using BackupConfig would add unneeded complexity
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


def is_name_duplicate(
    name: str, config_path: Path = Path(CONFIG_LOCATION).expanduser()
) -> bool:
    try:
        potential_path = config_path / f"{name}.json"
        if not config_path.exists():
            logging.info("Config directory does not exist. Creating now.")
            config_path.mkdir(parents=True)

        if potential_path.exists():
            logging.info(f"Unique name already in use: {name}")
            return True
    except (OSError, FileNotFoundError) as e:
        logging.exception(f"Error raised while checking config folder: {e}")
        raise
    logging.info(f"Name {name} is unique. {potential_path} does not exist.")
    return False


def fill_missing_create_args(
    args: dict[str, Any], config_path: Path = Path(CONFIG_LOCATION).expanduser()
) -> None:
    if args["name"] is None or args["name"] == NAME_DEFAULT:
        logging.info("No name specified. Setting it based on directory")
        args["name"] = get_default_backup_name(args["path"], config_path)
        logging.info(f"Backup name now set to {args['name']}")

    if args["naming_format"] is None or args["naming_format"] == NAME_DEFAULT:
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


def create_backup_from_args(
    args_dict: dict[str, Any], config_path: Path = Path(CONFIG_LOCATION).expanduser()
) -> None:
    required_args = ("path", "destination", "time_period")

    if not all([args_dict.get(argument) is not None for argument in required_args]):
        logging.info(
            "One or more required arguments missing. Starting interactive config creator"
        )
        interactive_config_creator(args_dict)

    using_default_name_format = args_dict["naming_format"] in {NAME_DEFAULT, None}
    fill_missing_create_args(args_dict, config_path)
    while is_name_duplicate(args_dict["name"], config_path):
        args_dict["name"] = parse_name(
            input(
                "Name already taken. Try a new name (or press Enter to use default from path): "
            )
        )
        if using_default_name_format:
            args_dict["naming_format"] = NAME_DEFAULT
            fill_missing_create_args(args_dict, config_path)

    config = BackupConfig.from_dict(args_dict)
    if (config_path / f"{args_dict['name']}.json").exists():
        logging.error("Config already exists, exiting...")
        return
    config.write_to_config_file(config_path)
    logging.info("Successfully wrote backup configuration file")


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


if __name__ == "__main__":
    pass
