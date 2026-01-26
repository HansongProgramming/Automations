import asyncio
import sys
from playwright.async_api import async_playwright
from pathlib import Path
import tempfile
import logging

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Converts HTML to pixel-perfect PDF using Playwright"""
    
    async def html_string_to_pdf(
        self, 
        html_content: str, 
        client_name: str = "report"
    ) -> bytes:
        """
        Convert HTML string to PDF with pixel-perfect rendering.
        
        Args:
            html_content: The HTML string to convert
            client_name: Name for logging purposes
            
        Returns:
            PDF file as bytes
        """
        try:
            # Create temp HTML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                html_path = f.name
            
            try:
                # Generate PDF using Playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-setuid-sandbox']
                    )
                    
                    page = await browser.new_page()
                    
                    # Load HTML
                    file_url = Path(html_path).as_uri()
                    await page.goto(file_url)
                    await page.wait_for_load_state('networkidle')
                    
                    # Generate PDF with print settings
                    pdf_bytes = await page.pdf(
                        format='A4',
                        print_background=True,
                        margin={
                            'top': '0',
                            'right': '0',
                            'bottom': '0',
                            'left': '0'
                        },
                        prefer_css_page_size=False
                    )
                    
                    await browser.close()
                
                logger.info(f"Generated PDF for {client_name}: {len(pdf_bytes):,} bytes")
                return pdf_bytes
                
            finally:
                # Clean up temp file
                Path(html_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Error generating PDF for {client_name}:", exc_info=True)
            raise


# Global instance
pdf_generator = PDFGenerator()