def evaluate_ap_marker(accounts):
    return any(" I " in a["payment_history"] for a in accounts)
