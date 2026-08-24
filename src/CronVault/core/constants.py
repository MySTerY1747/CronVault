#  constants.py
#  Contains all the constants used throughout the application

CONFIG_FILE_NAME: str = "CronVault.conf"
MAX_NAME_ATTEMPTS: int = 101
MAX_DELETE_OLD_BACKUP_ATTEMPTS: int = 10
CRONVAULT_MARKER_FILENAME: str = ".cronvault_marker.json"
DEFAULT_BACKUP_CHECK_INTERVAL_MINUTES: int = 10  #  run check every 10 minutes
CRON_JOB_COMMENT: str = "Automated CronVault check. Minute frequency:"
NAME_DEFAULT: str = "NoName"
FIFTY_GB: int = 53_687_091_200  #  50GB
CONFIG_LOCATION: str = "~/.config/CronVault/"
DEFAULT_BACKUP_ENGINE = "copy"
SUPPORTED_ENGINES = ("copy", "zip", "rsync")

if __name__ == "__main__":
    pass
