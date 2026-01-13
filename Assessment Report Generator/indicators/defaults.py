def evaluate_defaults(accounts):
    """
    Active default = default occurred AND not settled
    """

    for a in accounts:
        default_date = a.get("default_date")
        settled_date = a.get("settled_date")
        history = a.get("payment_history", "")

        # Case 1: Explicit default date with no settlement
        if default_date and not settled_date:
            return True

        # Case 2: 'D' marker without later 'S'
        if "D" in history and "S" not in history:
            return True

    return False
