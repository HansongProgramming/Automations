import asyncio
import os
import shutil
import sys
from playwright.async_api import async_playwright
from pathlib import Path
import tempfile
import logging
from concurrent.futures import ThreadPoolExecutor
import functools

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Converts HTML to pixel-perfect PDF using Playwright"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1)
    
    async def _generate_pdf_in_new_loop(self, html_content: str, client_name: str) -> bytes:
        """Run PDF generation in a new event loop with proper Windows support"""
        def run_in_new_loop():
            # Create new event loop with Windows ProactorEventLoop
            if sys.platform == 'win32':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # Ensure it's ProactorEventLoop
                if not isinstance(loop, asyncio.ProactorEventLoop):
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            else:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            try:
                return loop.run_until_complete(self._do_generate_pdf(html_content, client_name))
            finally:
                loop.close()
        
        # Run in thread pool to avoid event loop conflicts
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, run_in_new_loop)
    
    async def _do_generate_pdf(self, html_content: str, client_name: str) -> bytes:
        """
        Actual PDF generation logic - Convert HTML string to PDF with pixel-perfect rendering.
        
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
                    # Discover Chromium: env var → system packages → Playwright's bundled browser
                    executable_path = (
                        os.getenv('CHROMIUM_EXECUTABLE_PATH') or
                        shutil.which('chromium-browser') or
                        shutil.which('chromium') or
                        shutil.which('google-chrome') or
                        None
                    )
                    if executable_path:
                        logger.info(f"Using Chromium at: {executable_path}")
                    browser = await p.chromium.launch(
                        headless=True,
                        executable_path=executable_path,
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
    
    async def html_string_to_pdf(self, html_content: str, client_name: str = "report") -> bytes:
        """Public API: Generate PDF from HTML string"""
        return await self._generate_pdf_in_new_loop(html_content, client_name)


# Global instance
pdf_generator = PDFGenerator()