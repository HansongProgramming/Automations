from playwright.sync_api import sync_playwright
from pathlib import Path

def html_to_pdf(
    html_path: str,
    output_pdf: str,
    page_width: str = "8.27in",   # A4 width
    page_height: str = "11.69in", # A4 height
    scale: float = 1.0
):
    html_path = Path(html_path).resolve()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Load local HTML file
        page.goto(f"file://{html_path}")

        # Wait for fonts, images, JS, etc.
        page.wait_for_load_state("networkidle")

        page.pdf(
            path=output_pdf,
            print_background=True,  # VERY important for exact look
            width=page_width,
            height=page_height,
            scale=scale,
            margin={
                "top": "0in",
                "right": "0in",
                "bottom": "0in",
                "left": "0in",
            },
        )

        browser.close()

if __name__ == "__main__":
    html_to_pdf(
        html_path="input.html",
        output_pdf="output.pdf"
    )
