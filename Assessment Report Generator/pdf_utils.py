import fitz  # PyMuPDF

def pdf_to_pngs(
    pdf_path,
    start_keyword,
    stop_keyword
):
    doc = fitz.open(pdf_path)
    start_page = None
    stop_page = None

    for i, page in enumerate(doc):
        text = page.get_text()
        if start_keyword in text and start_page is None:
            start_page = i
        if stop_keyword in text:
            stop_page = i
            break

    if start_page is None:
        raise RuntimeError("Start keyword not found")

    if stop_page is None:
        stop_page = len(doc)

    images = []
    for i in range(start_page, stop_page):
        pix = doc[i].get_pixmap(dpi=300)
        images.append(pix.tobytes("png"))

    return images
