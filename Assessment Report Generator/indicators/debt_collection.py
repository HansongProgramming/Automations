DEBT_KEYWORDS = [
    "PORTFOLIO",
    "RECOVER",
    "RECOVERY",
    "COLLECTION",
    "CREDIT MANAGEMENT",
    "DEBT",
    "HOLDINGS",
    "FINANCE",
]

KNOWN_ORIGINATORS = [
    "BARCLAY",
    "CAPITAL ONE",
    "VANQUIS",
    "NEWDAY",
    "AQUA",
    "JAJA",
    "ZABLE",
    "HSBC",
    "LLOYDS",
    "NATWEST",
    "MONZO",
]

def evaluate_debt_collection(accounts):
    for a in accounts:
        lender = a["lender"].upper()
        history = a["payment_history"]

        # 1. Transfer marker
        if " X " in f" {history} ":
            return True

        # 2. Explicit collection language
        if any(k in lender for k in DEBT_KEYWORDS):
            return True

        # 3. Default + non-originator
        if a["default_date"] and not any(o in lender for o in KNOWN_ORIGINATORS):
            return True

    return False
