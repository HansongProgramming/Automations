from datetime import datetime

def evaluate_rapid_borrowing(accounts):
    dates = []

    for a in accounts:
        try:
            dates.append(datetime.strptime(a["start_date"], "%d/%m/%Y"))
        except:
            pass

    dates.sort()
    for i in range(len(dates) - 1):
        if (dates[i+1] - dates[i]).days < 60:
            return True

    return False
