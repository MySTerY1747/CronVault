#  conftest.py
#  Shared pytest fixtures
import pytest


@pytest.fixture
def generate_test_configs() -> list[dict[str, object]]:
    return [
        {
            "name": "documents",
            "max_backup_size": 50_000_000_000,
            "path": "/home/stef/Documents",
            "name_format": "%Y-%m-%d_%H-%M",
            "destination": "/mnt/backups/documents",
            "time_period": 3600,
            "last_known_backup": 1721832000,
            "total_backup_count": 12,
            "status": "active",
        },
        {
            "name": "photos",
            "max_backup_size": 100_000_000_000,
            "path": "/home/stef/Pictures",
            "name_format": "%Y-%m-%d",
            "destination": "/mnt/backups/photos",
            "time_period": 86400,
            "last_known_backup": 1721745600,
            "total_backup_count": 48,
            "status": "inactive",
        },
        {
            "name": "projects",
            "max_backup_size": 20_000_000_000,
            "path": "/home/stef/Projects",
            "name_format": "%Y%m%d_%H%M%S",
            "destination": "/mnt/backups/projects",
            "time_period": 7200,
            "last_known_backup": 1721835600,
            "total_backup_count": 5,
            "status": "active",
        },
        {
            "name": "music",
            "max_backup_size": 30_000_000_000,
            "path": "/home/stef/Music",
            "name_format": "%Y-%m-%d_%H-%M-%S",
            "destination": "/mnt/backups/music",
            "time_period": 43200,
            "last_known_backup": None,
            "total_backup_count": 0,
            "status": "inactive",
        },
        {
            "name": "notes",
            "max_backup_size": 5_000_000_000,
            "path": "/home/stef/Notes",
            "name_format": "%Y-%m-%d",
            "destination": "/mnt/backups/notes",
            "time_period": 1800,
            "last_known_backup": 1721836500,
            "total_backup_count": 27,
            "status": "active",
        },
    ]
