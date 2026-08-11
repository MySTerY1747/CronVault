#  main.py
#  entry point to the program

import logging
import argparse
from logging import Logger
from typing import Callable

from utils.utils import (
    add_cron_job,
    change_backup_status,
    delete_backup,
    get_all_backups,
    print_configs,
    run_backup_if_needed,
    filter_configs_active,
    filter_configs_inactive,
    create_backup_from_args,
)
from utils.parse_functions import (
    parse_name,
    parse_size,
    parse_name_format,
    parse_path,
    parse_time_period,
)
import colorama

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
        default=None,
        help="Unique name to identify this backup",
    )
    parser_create.add_argument(
        "-m",
        "--max-backup-size",
        type=parse_size,
        help="Maximum total size of backups before overwriting old ones (e.g. 10MB, 4GB, 500K)",
        default=None,
    )
    parser_create.add_argument(
        "-p",
        "--path",
        type=parse_path,
        help="Specifies the directory path to back up",
    )
    parser_create.add_argument(
        "-d",
        "--destination",
        type=parse_path,
        help="Specifies the destination directory where backups will be stored",
    )
    parser_create.add_argument(
        "-f",
        "--naming-format",
        type=parse_name_format,
        help="Naming scheme for backups. Uses strftime syntax",
        required=False,
        default=None,
    )
    parser_create.add_argument(
        "-t",
        "--time-period",
        type=parse_time_period,
        help='Time period between backups. Uses natural syntax: "5 days", "15d10h", "1w 3d 2h 32m", "172 hours", etc.',
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
        create_backup_from_args(vars(args))

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

    add_cron_job()
    logging.info("Calling handler function")
    handler_functions[args.command]()

    logging.info("Handler function complete. Exiting...")

    # TODO: Add integration test for `create`
    # TODO: Refactor into multiple files. Consider using an object instead of dictionaries
