"""Lightweight failure-only structured error logger.

Appends one JSON record per line (JSONL) to a local file on the VPS.
Only failures are written — successful operations are never logged here.
"""

import json
import os

from app.utils.date_utils import format_sheets_timestamp

LOG_DIR  = os.getenv("ERROR_LOG_DIR", "logs")
LOG_PATH = os.path.join(LOG_DIR, "errors.jsonl")


def log_failure(client_name: str, error: str, url: str = "") -> None:
    """Append a single failure record to the local error log.

    Args:
        client_name: Display name of the client being processed.
        error:       Error message or exception string.
        url:         Credit report URL that was being processed (if known).
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    record = {
        "timestamp":   format_sheets_timestamp(),
        "client_name": client_name,
        "url":         url,
        "error":       error,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
