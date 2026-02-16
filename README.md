# CronVault

Flexible Python-based backup tool to automate folder backups using Cron jobs.

The current aim of this project simple:

CLI tool that allows the user to specify:

- A folder
- A time interval
- A naming scheme
- Maximum backup size

The tool will create a JSON file with the relevant details in the user's `~/.config` directory, and add a cron job that runs in the specified interval, running the script using that JSON file.

Optional features:

- Notification support for backups, both on success and/or failure
