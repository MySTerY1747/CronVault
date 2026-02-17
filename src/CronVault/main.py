#  main.py
#  entry point to the program

import logging
import argparse
from logging import Logger

NAME_DEFAULT: str = "NoName"
CONFIG_LOCATION: str = "~/.config/CronVault/"

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
        type=str,
        default=NAME_DEFAULT,
        help="Unique name to identify this backup",
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    LOGGER: Logger = logging.getLogger()
    logging.info("Finished parsing command-line arguments")
