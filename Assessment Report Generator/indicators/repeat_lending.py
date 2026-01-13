from collections import Counter

def evaluate_repeat_lending(accounts):
    lenders = [a["lender"] for a in accounts]
    counts = Counter(lenders)
    return any(v >= 2 for v in counts.values())
