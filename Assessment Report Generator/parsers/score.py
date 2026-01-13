INDICATOR_WEIGHTS = {
    "active_ccj": 40,
    "multiple_ccjs": 50,
    "active_default": 30,
    "debt_collection": 25,
    "ap_marker": 20,
    "arrears_last_6_months": 20,
    "credit_utilisation_over_80": 15,
    "rapid_borrowing_acceleration": 15,
    "repeat_lending": 25,
}


def calculate_score(results: dict) -> int:
    score = 0
    for indicator, triggered in results.items():
        if triggered:
            score += INDICATOR_WEIGHTS.get(indicator, 0)
    return score
