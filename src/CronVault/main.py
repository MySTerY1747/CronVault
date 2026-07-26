#  main.py
#  entry point to the program

import logging
import argparse
from logging import Logger
from typing import Callable

from utils.utils import (
    change_backup_status,
    convert_user_args_json,
    delete_backup,
    get_all_backups,
    get_config_path,
    parse_name,
    parse_size,
    parse_path,
    parse_name_format,
    get_default_backup_name,
    parse_time_period,
    print_configs,
    run_backup_if_needed,
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
    parser_activate = subparsers.add_parser(
        "activate", help="Activate a backup config file"
    )
    parser_activate.add_argument("name", type=str)
    parser_deactivate = subparsers.add_parser(
        "deactivate", help="Deactivate a backup config file"
    )
    parser_deactivate.add_argument("name", type=str)
    parser_delete = subparsers.add_parser("delete", help="Delete a backup config file")
    parser_delete.add_argument("name", type=str)
    parser_backup = subparsers.add_parser(
        "backup", help="Backup a configured directory"
    )
    parser_backup.add_argument(
        "names", nargs="*", metavar="NAME", help="Names of backup configs"
    )
    parser_backup.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Check all active configs, and perform the ones currently due",
    )
    parser_backup.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Manually perform backup(s) now, even if not due",
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

    def handle_activate():
        change_backup_status(args.name, "active")

    def handle_deactivate():
        change_backup_status(args.name, "inactive")

    def handle_delete():
        delete_backup(args.name)

    def handle_backup():
        if args.all and args.names:
            parser.error("cannot specify backup names together with --all")
        if not args.all and not args.names:
            parser.error("must specify either --all or at least one backup name")

        if args.all:
            configs = filter_configs_active(get_all_backups())
            for config in configs:
                run_backup_if_needed(config["name"], skip_checks=args.force)
        else:
            for name in args.names:
                run_backup_if_needed(name, skip_checks=args.force)

    handler_functions: dict[str | None, Callable] = {
        "create": handle_create,
        "list": handle_list,
        "activate": handle_activate,
        "deactivate": handle_deactivate,
        "delete": handle_delete,
        "backup": handle_backup,
        None: exit,
    }

    handler_functions[args.command]()

    logging.info("Handler function complete. Exiting...")

    # TODO: Add integration test for `create` and `backup`
    # TODO: add watchdog cron job on startup, and create associated function
    # TODO: Add walkthrough functionality for `create` command
    # TODO: Refactor into multiple files. Consider using an object instead of dictionaries
