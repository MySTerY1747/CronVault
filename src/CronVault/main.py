#  main.py
#  entry point to the program

import logging
import argparse
from logging import Logger
from typing import Callable

from utils.utils import (
    convert_user_args_json,
    get_all_backups,
    get_config_path,
    parse_name,
    parse_size,
    parse_path,
    parse_name_format,
    get_default_backup_name,
    parse_time_period,
    print_configs,
    write_file,
    filter_configs_active,
    filter_configs_inactive,
)
import colorama

NAME_DEFAULT: str = "NoName"

FIFTY_GB: int = 53_687_091_200  #  50GB

if __name__ == "__main__":
    colorama.init(autoreset=True)

    parser = argparse.ArgumentParser(
        description="CronVault - Flexible Python-based backup automation tool via cron jobs"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="increase logging verbosity"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    parser_list = subparsers.add_parser("list", help="List configs")
    parser_list_group = parser_list.add_mutually_exclusive_group()
    parser_list_group.add_argument(
        "-a", "--active", action="store_true", help="Only list active backup configs"
    )
    parser_list_group.add_argument(
        "-i",
        "--inactive",
        action="store_true",
        help="Only list inactive backup configs",
    )
    parser_create = subparsers.add_parser("create", help="Create new backup configs")
    parser_create.add_argument(
        "-n",
        "--name",
        type=parse_name,
        default=NAME_DEFAULT,
        help="Unique name to identify this backup",
    )
    parser_create.add_argument(
        "-m",
        "--max-backup-size",
        type=parse_size,
        help="Maximum total size of backups before overwriting old ones (e.g. 10MB, 4GB, 500K)",
        default=FIFTY_GB,
    )
    parser_create.add_argument(
        "-p",
        "--path",
        type=parse_path,
        help="Specifies the directory path to back up",
        required=True,
    )
    parser_create.add_argument(
        "-d",
        "--destination",
        type=parse_path,
        help="Specifies the destination directory where backups will be stored",
        required=True,
    )
    parser_create.add_argument(
        "-f",
        "--naming-format",
        type=parse_name_format,
        help="Naming scheme for backups. Uses strftime syntax",
        required=False,
        default=NAME_DEFAULT,
    )
    parser_create.add_argument(
        "-t",
        "--time-period",
        type=parse_time_period,
        help='Time period between backups. Uses natural syntax: "5 days", "15d10h", "1w 3d 2h 32m", "172 hours", etc.',
        required=True,
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    LOGGER: Logger = logging.getLogger()
    logging.info("Finished parsing command-line arguments")
    logging.info("Checking command-line arguments")
    logging.info(args)

    def handle_create():
        if args.name == NAME_DEFAULT:
            logging.info("No name specified. Setting it based on directory")
            args.name = get_default_backup_name(args.path)
            logging.info(f"Backup name now set to {args.name}")

        if args.naming_format == NAME_DEFAULT:
            logging.info("No naming format specified. Setting it based on name")
            args.naming_format = f"{args.name} %Y-%m-%M"
            logging.info(f"Backup naming scheme now set to {args.naming_format}")

        file_path = get_config_path(args.name)
        contents = convert_user_args_json(
            args.name,
            args.max_backup_size,
            args.path,
            args.naming_format,
            args.destination,
            args.time_period,
        )  #  change this to use dictionary unpacking in the future
        write_file(file_path, contents)
        logging.info("Successfully wrote backup configuration file")

    def handle_list():
        backup_configs = get_all_backups()
        if args.active:
            backup_configs = filter_configs_active(backup_configs)
        elif args.inactive:
            backup_configs = filter_configs_inactive(backup_configs)

        print_configs(backup_configs)

    handler_functions: dict[str | None, Callable] = {
        "create": handle_create,
        "list": handle_list,
        None: exit,
    }

    handler_functions[args.command]()

    logging.info("Handler function complete. Exiting...")

    # TODO: Add integration test for `create`
    # TODO: Change parser logic to support the different commands: create ✅, list, backup, activate, deactivate
    # TODO: function to actually perform the backup
    # TODO: add watchdog cron job on startup, and create associated function
    # TODO: add functions to list, deactivate (stop), activate (start), remove, and manually run backup jobs
