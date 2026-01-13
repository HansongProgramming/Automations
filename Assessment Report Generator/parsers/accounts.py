from bs4 import BeautifulSoup
from datetime import datetime
import re


def _clean_value(value):
    if not value:
        return None
    value = value.strip()
    return None if value in ["N/A", "£N/A"] else value


def _find_field(text, label):
    """
    Extracts the value immediately following a label.
    """
    pattern = rf"{re.escape(label)}\s+([^\s]+)"
    match = re.search(pattern, text)
    return _clean_value(match.group(1)) if match else None


def extract_accounts(soup):
    accounts = []

    # Each account block starts with "Account from <LENDER>"
    for header in soup.find_all(string=lambda x: x and "Account from" in x):
        section = header.find_parent("table")
        if not section:
            continue

        text = section.get_text(" ", strip=True)

        lender = (
            header.replace("Account from", "")
            .split("(")[0]
            .strip()
        )

        credit_limit = _find_field(text, "Credit Limit")
        loan_value = _find_field(text, "Loan Value")
        default_date = _find_field(text, "Default Date")
        settled_date = _find_field(text, "Settled Date")
        start_date = _find_field(text, "Agreement Start Date")

        # Normalize dates
        def parse_date(d):
            try:
                return datetime.strptime(d, "%d/%m/%Y")
            except:
                return None

        payment_history_match = re.search(
            r"Payment History(.+)", text
        )

        payment_history = payment_history_match.group(1) if payment_history_match else ""

        accounts.append({
            "lender": lender,

            # Financials
            "credit_limit": credit_limit,
            "loan_value": loan_value,

            # Dates
            "agreement_start_date": parse_date(start_date),
            "default_date": parse_date(default_date),
            "settled_date": parse_date(settled_date),

            # Raw markers (used by multiple indicators)
            "payment_history": payment_history,

            # Convenience flags (DO NOT score directly)
            "has_default_marker": " D " in f" {payment_history} ",
            "has_ap_marker": " I " in f" {payment_history} ",
        })

    return accounts
