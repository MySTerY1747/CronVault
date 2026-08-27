# CronVault

Automated local directory backups with self-healing cron scheduling, automatic storage quotas, and pluggable engines.

![CronVault Demo](assets/demo.gif)

---

## Overview

Writing custom shell scripts for backups usually means managing crontabs manually, dealing with unhandled permissions, and risking disk-fill crashes.

**CronVault** manages your backups declaratively. Define snapshot rules once—setting storage quotas, execution intervals, and formats—and CronVault handles scheduling, metadata tracking, and automatic retention pruning in the background.

### Key Features

* **Pluggable Backup Engines:** Choose how snapshots are stored (`copy`, `zip`, or `rsync`).
* **Natural Scheduling:** Define intervals using human syntax (`"12 hours"`, `"3 days"`, `"1w 2d"`).
* **Storage Quotas & Auto-Pruning:** Set size limits per backup task. When limits are exceeded, CronVault safely moves older snapshots to the trash via `send2trash`.
* **Self-Healing Cron Automation:** Every command verifies and ensures the background cron runner is active and healthy.
* **Declarative Configurations:** Backups are stored as isolated JSON configurations in `~/.config/CronVault/`.
* **Interactive or Flag-Driven:** Create tasks interactively via wizard or directly through CLI flags.

---

## Installation

### Via pip / pipx (Recommended)

```bash
pipx install cronvault
# or
pip install cronvault

```

### From Source

```bash
git clone https://github.com/yourusername/CronVault.git
cd CronVault
pip install .

```

*Requirements:* Python 3.10+ (tested on Linux & macOS).

---

## Quickstart

### 1. Create a Backup Configuration

You can launch the interactive setup wizard:

```bash
cronvault create

```

Or pass all flags in a single command:

```bash
cronvault create \
  --name "notes" \
  --path "~/Documents/Notes" \
  --destination "~/Backups/Notes" \
  --time-period "1 day" \
  --max-backup-size "10GB" \
  --engine zip

```

### 2. View Configured Backups

```bash
# List all backup configs and their status
cronvault list

# List only active tasks
cronvault list --active

```

### 3. Run or Force Backups

CronVault automatically checks and executes due tasks via cron. To trigger runs manually:

```bash
# Check all active tasks and run whichever are currently due
cronvault backup --all

# Run a specific backup immediately, ignoring the schedule interval
cronvault backup notes --force

```

---

## Backup Engines

CronVault supports three engines for snapshot creation:

| Engine | Identifier | Description | Marker Strategy |
| --- | --- | --- | --- |
| **Directory Copy** | `copy` *(default)* | Fast recursive folder snapshot preserving metadata. | `.cronvault_marker.json` inside destination directory |
| **ZIP Archive** | `zip` | Compressed `.zip` archives with relative folder trees preserved. | Embedded directly inside the ZIP root |
| **Rsync** | `rsync` | Uses system `rsync -a` for efficient local folder syncs. | `.cronvault_marker.json` inside destination directory |

---

## CLI Reference

### `cronvault create`

| Flag | Shorthand | Description | Default |
| --- | --- | --- | --- |
| `--name` | `-n` | Unique name for the backup configuration. | Derived from folder name |
| `--path` | `-p` | Source directory path to back up. | *Required (or interactive)* |
| `--destination` | `-d` | Target directory where snapshots are stored. | Current working directory |
| `--time-period` | `-t` | Interval between backups (e.g., `12h`, `5 days`, `1w`). | *Required (or interactive)* |
| `--max-backup-size` | `-m` | Storage limit (e.g., `500MB`, `10GB`). Older backups are pruned if exceeded. | `50GB` |
| `--engine` | `-e` | Backup mechanism (`copy`, `zip`, `rsync`). | `copy` |
| `--naming-format` | `-f` | `strftime` naming pattern for snapshot folders/archives. | `{name} %Y-%m-%d_%H-%M-%S` |

### Other Commands

```bash
# Task Management
cronvault activate <name>      # Enable automatic backups for a task
cronvault deactivate <name>    # Pause backups for a task without deleting config
cronvault delete <name>        # Remove a backup configuration

# Execution
cronvault backup <name...>     # Run specified backup(s) if due
cronvault backup -a            # Check and run all active backups
cronvault backup -f <name>     # Force backup execution immediately

# Options
cronvault -v, --verbose        # Enable verbose debug logging

```

---

## Storage & Configuration Architecture

Configurations live in `~/.config/CronVault/`:

```text
~/.config/CronVault/
├── notes.json            # Task definition & runtime state
├── projects.json
└── ...

```

Each snapshot created contains a small metadata marker (`.cronvault_marker.json`). This ensures CronVault only manages and prunes files it generated, preventing accidental deletion of unrelated data in your destination folders.

---

## Development & Testing

Clone the repository and install test dependencies:

```bash
git clone https://github.com/yourusername/CronVault.git
cd CronVault
pip install -e ".[dev]"

```

Run tests with coverage:

```bash
pytest

```

---

## License

This project is licensed under the [Apache License](LICENSE).
