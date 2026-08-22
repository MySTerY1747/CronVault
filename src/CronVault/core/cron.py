#  cron.py
#  Handles crontab file manipulation, with self-healing logic

import logging
import re
from CronVault.core.constants import CRON_JOB_COMMENT, CONFIG_LOCATION
from CronVault.core.config import get_backup_frequency_from_config
from pathlib import Path
from crontab import CronTab, CronItem


def ensure_single_cron_job(
    cronvault_jobs: list[CronItem], backup_check_frequency: int
) -> bool:
    job_exists = False

    #  only keep one active job, with correct backup check frequency
    logging.info(f"Iterating through {len(cronvault_jobs)} cron job(s)")
    for job in cronvault_jobs:
        if job.is_enabled() and job.is_valid():
            if job_exists:
                job.delete()
                continue

            prefix = f"{CRON_JOB_COMMENT}"
            if not job.comment.startswith(prefix):
                logging.error("Invalid CronVault job found. Deleting")
                job.delete()
                continue

            try:
                interval = int(job.comment.removeprefix(prefix))
            except ValueError:
                logging.error("Invalid CronVault job found. Deleting.")
                job.delete()
                continue

            if interval == backup_check_frequency:
                logging.info("Job already exists with proper frequency.")
                job_exists = True
            else:
                #  pyright thinks `minute` is an int
                job.minute.every(backup_check_frequency)  #  pyright: ignore
                job.comment = f"{CRON_JOB_COMMENT} {backup_check_frequency}"
                job_exists = True
    return job_exists


def add_cron_job(config_path: Path = Path(CONFIG_LOCATION).expanduser()) -> None:
    try:
        logging.info("Checking whether cron job exists")
        backup_check_frequency: int = get_backup_frequency_from_config(config_path)
        logging.info("Reading user crontab")
        cron = CronTab(user=True)
        cronvault_jobs = list(cron.find_comment(re.compile(f"{CRON_JOB_COMMENT}")))

        job_exists = ensure_single_cron_job(cronvault_jobs, backup_check_frequency)

        if not job_exists:
            logging.info("No cron job found. Creating now")
            job = cron.new(
                command="cronvault backup -a",
                comment=f"{CRON_JOB_COMMENT} {backup_check_frequency}",
            )
            job.minute.every(backup_check_frequency)  #  pyright: ignore
        cron.write()
    except OSError as e:
        logging.exception(f"Got OSError while going through Cron jobs: {e}")
        raise


if __name__ == "__main__":
    pass
