#  arguments.py
#  Data for arguments


from dataclasses import dataclass
from typing import Callable

from CronVault.cli.parse_functions import (
    parse_engine,
    parse_name,
    parse_name_format,
    parse_path,
    parse_size,
    parse_time_period,
)


@dataclass
class Argument:
    """Class to hold a name, prompt, and parser function for arguments"""

    name: str
    prompt: str
    parser: Callable


create_arguments: list[Argument] = [
    Argument(
        "path",
        "• Path of the folder to back up (or press Enter to use current working directory): ",
        parse_path,
    ),
    Argument(
        "destination",
        "• Destination path for backups (or press Enter to use current working directory): ",
        parse_path,
    ),
    Argument(
        "time_period",
        "• Time interval between backups (e.g. 5D, 1M, 5 hours): ",
        parse_time_period,
    ),
    Argument(
        "max_backup_size",
        "• Maximum backup size: e.g. 100GB, 100MB (or press Enter to use default 50GB): ",
        parse_size,
    ),
    Argument(
        "naming_format",
        "• Naming format for backups, strftime syntax. (or press Enter to use default {name} %Y-%m-%d_%H-%M-%S): ",
        parse_name_format,
    ),
    Argument(
        "engine",
        "• Backup engine to use for backups: copy, zip, rsync. (or press Enter to use default: copy): ",
        parse_engine,
    ),
    Argument(
        "name",
        "• Name to identify this backup (or press Enter to use default name from path): ",
        parse_name,
    ),
]

if __name__ == "__main__":
    pass
