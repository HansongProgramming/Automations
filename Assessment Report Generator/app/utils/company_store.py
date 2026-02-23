"""Persistent company branding configuration store.

Data is kept in data/companies.json at the project root.
Each company maps 1-to-1 with a Google Sheets tab (sheet_name == company name).
"""

import json
import os
from typing import Optional, Dict, Any

from app.utils.date_utils import format_sheets_timestamp

# Project root is two levels above this file (app/utils/company_store.py → app/ → project root)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_STORE_PATH   = os.path.join(_PROJECT_ROOT, 'data', 'companies.json')

# Logo files live inside the static tree so FastAPI can serve them
LOGO_DIR = os.path.join(_PROJECT_ROOT, 'app', 'static', 'uploads', 'logos')


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load() -> Dict[str, Any]:
    if not os.path.exists(_STORE_PATH):
        return {}
    with open(_STORE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def _persist(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_STORE_PATH), exist_ok=True)
    with open(_STORE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_company(company_name: str) -> Optional[Dict[str, Any]]:
    """Return the stored config for *company_name*, or None if unknown."""
    return _load().get(company_name)


def save_company(
    company_name:    str,
    footer_message:  str = '',
    logo_path:       str = '',
) -> Dict[str, Any]:
    """Create or update a company record and return the saved config.

    If *logo_path* or *footer_message* is empty the existing value is kept,
    allowing partial updates (e.g. only refreshing the footer).
    """
    data     = _load()
    existing = data.get(company_name, {})

    data[company_name] = {
        'name':           company_name,
        'logo_path':      logo_path      or existing.get('logo_path', ''),
        'footer_message': footer_message or existing.get('footer_message', ''),
        'sheet_name':     company_name,
        'created_at':     existing.get('created_at', format_sheets_timestamp()),
        'updated_at':     format_sheets_timestamp(),
    }
    _persist(data)
    return data[company_name]
