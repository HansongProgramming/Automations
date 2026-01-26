from weasyprint import HTML, CSS
from pathlib import Path
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Converts HTML content to PDF using WeasyPrint (VPS-friendly)"""
    
    def __init__(self):
        # Optional: Add custom CSS for better PDF rendering
        self.base_css = CSS(string='''
            @page {
                size: A4;
                margin: 0;
            }
            body {
                margin: 0;
                padding: 0;
            }
        ''')
    
    async def html_string_to_pdf(
        self, 
        html_content: str, 
        client_name: str = "report"
    ) -> bytes:
        """
        Convert HTML string directly to PDF bytes.
        
        Args:
            html_content: The HTML string to convert
            client_name: Name for logging purposes
            
        Returns:
            PDF file as bytes
        """
        try:
            # WeasyPrint can work directly with HTML strings
            html = HTML(string=html_content)
            
            # Generate PDF to bytes
            pdf_bytes = html.write_pdf(stylesheets=[self.base_css])
            
            logger.info(f"Generated PDF for {client_name}: {len(pdf_bytes):,} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error generating PDF for {client_name}: {e}", exc_info=True)
            raise
    
    def html_string_to_pdf_sync(
        self, 
        html_content: str, 
        client_name: str = "report"
    ) -> bytes:
        """
        Synchronous version - WeasyPrint doesn't need async.
        Use this if you want to avoid the async wrapper.
        
        Args:
            html_content: The HTML string to convert
            client_name: Name for logging purposes
            
        Returns:
            PDF file as bytes
        """
        try:
            html = HTML(string=html_content)
            pdf_bytes = html.write_pdf(stylesheets=[self.base_css])
            
            logger.info(f"Generated PDF for {client_name}: {len(pdf_bytes):,} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error generating PDF for {client_name}: {e}", exc_info=True)
            raise


# Global instance
pdf_generator = PDFGenerator()