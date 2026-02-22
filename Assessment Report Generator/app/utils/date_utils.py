"""Centralized date/time utilities for consistent formatting across the application."""

from datetime import datetime

SHEETS_TIMESTAMP_FORMAT = "%d/%m/%Y - %H:%M:%S"


def format_sheets_timestamp(dt: datetime | None = None) -> str:
    """Return a timestamp string in DD/MM/YYYY - HH:MM:SS format.

    Args:
        dt: A datetime object to format. Defaults to the current local time.

    Returns:
        Formatted timestamp string, e.g. "22/02/2026 - 14:30:45".
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(SHEETS_TIMESTAMP_FORMAT)
