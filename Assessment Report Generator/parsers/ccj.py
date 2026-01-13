from bs4 import BeautifulSoup
from datetime import datetime

def extract_ccjs(soup):
    ccjs = []

    for record in soup.find_all(string=lambda x: "County Court Judgement" in x):
        block = record.find_parent("table")
        if not block:
            continue

        text = block.get_text(" ", strip=True)

        date = None
        for token in text.split():
            try:
                date = datetime.strptime(token, "%Y-%m-%d")
                break
            except:
                pass

        ccjs.append({
            "raw": text,
            "date": date
        })

    return ccjs
