from playwright.sync_api import sync_playwright
from PIL import Image
from pathlib import Path
import math

# A4 @ 150 DPI
A4_WIDTH_PX = 1240
A4_HEIGHT_PX = 1754

def html_to_pdf_a4_sliced(html_path, output_pdf):
    html_path = Path(html_path).resolve()

    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    screenshot_path = "full_page.png"

    # --- Render HTML and take full screenshot ---
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": A4_WIDTH_PX, "height": A4_HEIGHT_PX}
        )

        page.goto(html_path.as_uri())
        page.wait_for_load_state("networkidle")

        page.screenshot(path=screenshot_path, full_page=True)
        browser.close()

    # --- Slice screenshot into A4 pages ---
    img = Image.open(screenshot_path)
    width, height = img.size

    pages = []
    total_pages = math.ceil(height / A4_HEIGHT_PX)

    for i in range(total_pages):
        top = i * A4_HEIGHT_PX
        bottom = min((i + 1) * A4_HEIGHT_PX, height)

        page_img = img.crop((0, top, width, bottom))
        pages.append(page_img)

    # --- Save as multi-page PDF ---
    pages[0].save(
        output_pdf,
        "PDF",
        resolution=150,
        save_all=True,
        append_images=pages[1:]
    )

    print(f"✔ PDF created: {output_pdf} ({total_pages} pages)")

if __name__ == "__main__":
    html_to_pdf_a4_sliced("input.html", "output.pdf")
