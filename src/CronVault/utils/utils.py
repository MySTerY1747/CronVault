#  utils.py
#  small functions that don't belong with the rest of the code

import os
import logging
from CronVault.main import CONFIG_LOCATION


def check_if_name_unique(name: str) -> bool:
    try:
        config_folder: str = os.path.expanduser(CONFIG_LOCATION)
        backups: list[str] | None = os.listdir(config_folder)
        #  i know we can return directly here
        #  but here this is done for readability
        print(f"{backups=}, {name=}")
        if (backups is None) or (name in backups):
            return False
        return True
    except (OSError, FileNotFoundError) as e:
        logging.exception("Issue finding config folder")
        print(e)
    raise (OSError)


if __name__ == "__main__":
    pass
