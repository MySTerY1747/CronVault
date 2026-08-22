#  config_json_schema.py
#  contains the JSON schema used to validate configs

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "name",
        "max_backup_size",
        "path",
        "name_format",
        "destination",
        "time_period",
        "last_known_backup",
        "total_backup_count",
        "status",
    ],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "max_backup_size": {"type": "integer", "minimum": 0},
        "path": {"type": "string", "minLength": 1},
        "name_format": {"type": "string", "minLength": 1},
        "destination": {"type": "string", "minLength": 1},
        "time_period": {
            "type": "integer",
            "minimum": 1,
            "description": "Backup interval in seconds.",
        },
        "last_known_backup": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "ISO-formatted timestamp of the last successful backup, or null if none.",
        },
        "total_backup_count": {"type": "integer", "minimum": 0},
        "status": {"type": "string", "enum": ["inactive", "active"]},
    },
}

if __name__ == "__main__":
    pass
