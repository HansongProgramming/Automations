from bs4 import BeautifulSoup

from parsers.ccj import extract_ccjs
from parsers.accounts import extract_accounts

from indicators.ccj import evaluate_ccjs
from indicators.defaults import evaluate_defaults
from indicators.debt_collection import evaluate_debt_collection
from indicators.ap_marker import evaluate_ap_marker
from indicators.arrears import evaluate_recent_arrears
from indicators.utilisation import evaluate_credit_utilisation
from indicators.borrowing_velocity import evaluate_rapid_borrowing
from indicators.repeat_lending import evaluate_repeat_lending
from indicators.score import calculate_score

def run_assessment(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    ccjs = extract_ccjs(soup)
    accounts = extract_accounts(soup)

    flags = {
        **evaluate_ccjs(ccjs),
        "active_default": evaluate_defaults(accounts),
        "debt_collection": evaluate_debt_collection(accounts),
        "ap_marker": evaluate_ap_marker(accounts),
        "arrears": evaluate_recent_arrears(accounts),
        "utilisation": evaluate_credit_utilisation(accounts),
        "rapid_borrowing": evaluate_rapid_borrowing(accounts),
        "repeat_lending": evaluate_repeat_lending(accounts),
    }

    score, traffic = calculate_score(flags)

    return {
        "flags": flags,
        "score": score,
        "traffic_light": traffic
    }

if __name__ == "__main__":
    result = run_assessment("RICHARD DAVIES Credit File.html")
    print(result)
