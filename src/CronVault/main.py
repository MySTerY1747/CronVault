#  main.py
#  entry point to the program

import logging
import argparse
from logging import Logger

from utils.utils import parse_name, parse_size, parse_path

NAME_DEFAULT: str = "NoName"  #  TODO: Change this to last elm of folder name

FIFTY_GB: int = 53_687_091_200  #  50GB

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CronVault - Flexible Python-based backup automation tool via cron jobs"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="increase logging verbosity"
    )
    parser.add_argument(
        "-n",
        "--name",
        type=parse_name,
        default=NAME_DEFAULT,
        help="Unique name to identify this backup",
    )
    parser.add_argument(
        "-m",
        "--max-backup-size",
        type=parse_size,
        help="Maximum total size of backups before overwriting old ones (e.g. 10MB, 4GB, 500K)",
        default=FIFTY_GB,
    )
    parser.add_argument(
        "-p",
        "--path",
        type=parse_path,
        help="Specifies the directory path to back up",
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
