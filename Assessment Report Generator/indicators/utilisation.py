def evaluate_credit_utilisation(accounts):
    for a in accounts:
        try:
            limit = float(a["credit_limit"].replace("£", ""))
            balance = float(a.get("loan_value", 0))
            if limit > 0 and balance / limit > 0.8:
                return True
        except:
            pass
    return False
