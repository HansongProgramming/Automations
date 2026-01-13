def evaluate_recent_arrears(accounts):
    for a in accounts:
        if any(code in a["payment_history"] for code in ["1", "2", "3", "4", "5", "6", "A", "B"]):
            return True
    return False
