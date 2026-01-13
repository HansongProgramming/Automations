POINTS = {
    "active_ccj": 40,
    "multiple_ccjs": 50,
    "active_default": 30,
    "debt_collection": 25,
    "ap_marker": 20,
    "arrears": 20,
    "utilisation": 15,
    "rapid_borrowing": 15,
    "repeat_lending": 25,
}

def calculate_score(flags):
    score = sum(POINTS[k] for k, v in flags.items() if v)

    if score >= 70:
        traffic = "GREEN"
    elif score >= 40:
        traffic = "AMBER"
    else:
        traffic = "RED"

    return score, traffic
