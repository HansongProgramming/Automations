from datetime import datetime, timedelta

def evaluate_ccjs(ccjs):
    active = False
    multiple = len(ccjs) >= 2

    for ccj in ccjs:
        if ccj["date"] and ccj["date"] > datetime.now() - timedelta(days=6*365):
            active = True

    return {
        "active_ccj": active,
        "multiple_ccjs": multiple
    }
