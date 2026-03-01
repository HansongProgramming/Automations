from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
from typing import List, Dict, Any
import logging
import sys
import zipfile
from io import BytesIO
import base64
import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix for Windows asyncio + Playwright subprocess support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from .models import AnalyzeRequest, AnalyzeResponse, SingleReportResult, CSVBatchProcessResult
from .utils.html_fetcher import fetch_multiple_html
from .analyzer.credit_analyzer import CreditReportAnalyzer
from .utils.template_renderer import HTMLTemplateRenderer
from .utils.pdf_generator import pdf_generator
from .claim_letters.generator import ClaimLetterGenerator
from .claim_letters.config import TEMPLATE_PATH  # REMOVED BANK_DETAILS - now dynamic
from .utils.google_drive_uploader import GoogleDriveUploader
from .utils.google_sheets_tracker import GoogleSheetsTracker
from .utils.error_logger import log_failure
from .utils.company_store import get_company, save_company, LOGO_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Credit Report Analyzer API",
    description="Analyze credit reports for irresponsible lending indicators",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Force Windows ProactorEventLoop on startup"""
    if sys.platform == 'win32':
        loop = asyncio.get_event_loop()
        logger.info(f"Event loop type: {type(loop).__name__}")
        if not isinstance(loop, asyncio.ProactorEventLoop):
            logger.warning("Event loop is not ProactorEventLoop, attempting to set policy...")
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize HTML template renderer
html_renderer = HTMLTemplateRenderer()

# Initialize claim letter generator (NO BANK_DETAILS - now dynamic from JSON)
claim_letter_generator = ClaimLetterGenerator(TEMPLATE_PATH)

# Google API Configuration (set via environment variables)
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/google-service-account.json")
GOOGLE_OAUTH_CLIENT_PATH = os.getenv("GOOGLE_OAUTH_CLIENT_PATH", "credentials/oauth-client.json")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", None)
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", None)
GOOGLE_OAUTH_TOKEN_PATH = os.getenv("GOOGLE_OAUTH_TOKEN_PATH", "credentials/oauth-token.pkl")

# Initialize Google services (lazy initialization)
drive_uploader = None
sheets_tracker = None

def get_drive_uploader():
    """Get or initialize Google Drive uploader"""
    global drive_uploader
    if drive_uploader is None:
        if not os.path.exists(GOOGLE_OAUTH_CLIENT_PATH):
            raise HTTPException(
                status_code=500,
                detail=f"Google OAuth client file not found at {GOOGLE_OAUTH_CLIENT_PATH}"
            )
        drive_uploader = GoogleDriveUploader(
            credentials_path=GOOGLE_OAUTH_CLIENT_PATH,
            folder_id=GOOGLE_DRIVE_FOLDER_ID,
            token_path=GOOGLE_OAUTH_TOKEN_PATH
        )
    return drive_uploader

def get_sheets_tracker():
    """Get or initialize Google Sheets tracker"""
    global sheets_tracker
    if sheets_tracker is None:
        if not os.path.exists(GOOGLE_OAUTH_CLIENT_PATH):
            raise HTTPException(
                status_code=500,
                detail=f"Google OAuth client file not found at {GOOGLE_OAUTH_CLIENT_PATH}"
            )
        if not GOOGLE_SHEETS_ID:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_SHEETS_ID environment variable not set"
            )
        sheets_tracker = GoogleSheetsTracker(
            credentials_path=GOOGLE_OAUTH_CLIENT_PATH,
            spreadsheet_id=GOOGLE_SHEETS_ID,
            token_path=GOOGLE_OAUTH_TOKEN_PATH
        )
    return sheets_tracker

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Ensure logo upload directory exists on startup
os.makedirs(LOGO_DIR, exist_ok=True)


async def analyze_single_report(url: str, html_content: str) -> Dict[str, Any]:
    """
    Analyze a single credit report.
    
    Args:
        url: The source URL
        html_content: The HTML content to analyze
        
    Returns:
        Dict with credit_analysis or error
    """
    try:
        analyzer = CreditReportAnalyzer(html_content)
        result = analyzer.analyze()
        
        return {
            "url": url,
            "credit_analysis": result
        }
    except Exception as e:
        logger.error(f"Error analyzing {url}: {str(e)}", exc_info=True)
        return {
            "error": f"Analysis failed: {str(e)}",
            "url": url
        }


@app.get("/")
async def root():
    """Serve the main batch processing webpage"""
    index_file = Path(__file__).parent / "static" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return {
            "status": "ok",
            "message": "Credit Report Analyzer API is running",
            "version": "1.0.0"
        }


@app.get("/api/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "credit-report-analyzer"
    }


@app.post("/analyze")
async def analyze_reports(request: AnalyzeRequest):
    """
    Analyze one or more credit reports from URLs.
    
    Processes URLs in batches of 10 to ensure all URLs are handled.
    Can process any number of URLs (e.g., 30+) by queuing them in batches.
    Each batch is processed sequentially, but URLs within a batch are fetched concurrently.
    
    Example request:
    ```json
    {
        "urls": [
            "https://example.com/report1.html",
            "https://example.com/report2.html"
        ]
    }
    ```
    
    Returns array of credit analysis results matching original format.
    """
    urls = request.urls
    logger.info(f"Received analysis request for {len(urls)} URL(s)")
    logger.info("=" * 60)
    
    try:
        # Step 1: Fetch all HTML content concurrently
        logger.info("Fetching HTML content...")
        fetch_results = await fetch_multiple_html(urls)
        
        # Step 2: Process successful fetches
        analysis_tasks = []
        results = []
        
        for fetch_result in fetch_results:
            if fetch_result['status'] == 'success':
                task = analyze_single_report(
                    fetch_result['url'],
                    fetch_result['html_content']
                )
                analysis_tasks.append(task)
            else:
                # Record failed fetch
                results.append({
                    "error": fetch_result.get('error', 'Unknown fetch error'),
                    "url": fetch_result['url']
                })
        
        # Step 3: Analyze all successfully fetched reports concurrently
        if analysis_tasks:
            logger.info(f"Analyzing {len(analysis_tasks)} successfully fetched report(s)...")
            analysis_results = await asyncio.gather(*analysis_tasks)
            results.extend(analysis_results)
        
        successful_analyses = sum(1 for r in results if 'credit_analysis' in r)
        failed_analyses = sum(1 for r in results if 'error' in r)
        
        logger.info("=" * 60)
        logger.info(f"Analysis complete:")
        logger.info(f"  ✓ {successful_analyses} successful")
        logger.info(f"  ✗ {failed_analyses} failed")
        logger.info(f"  Total: {len(results)} results")
        logger.info("=" * 60)
        
        # Return as plain array matching original format
        return results
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_reports: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/analyze-pdf")
async def analyze_reports_pdf(request: AnalyzeRequest):
    """
    Analyze credit reports and return PDF files.
    
    This endpoint performs credit analysis and returns PDF reports.
    Each PDF is base64 encoded for easy transmission.
    
    Processes URLs in batches of 10 to ensure all URLs are handled.
    Can process any number of URLs (e.g., 30+) by queuing them in batches.
    
    Example request:
    ```json
    {
        "urls": [
            "https://example.com/report1.html",
            "https://example.com/report2.html"
        ]
    }
    ```
    
    Returns array of objects with:
    - url: The source URL
    - pdf_base64: Base64-encoded PDF file (or null if error)
    - client_name: Name of the client (for reference)
    - filename: Suggested filename for the PDF
    - error: Error message (if applicable)
    
    Example response:
    ```json
    [
        {
            "url": "https://example.com/report1.html",
            "pdf_base64": "JVBERi0xLjQKJeLjz9...",
            "client_name": "JOHN DOE",
            "filename": "JOHN_DOE_AffordabilityReport.pdf"
        }
    ]
    ```
    """
    urls = request.urls
    logger.info(f"Received PDF analysis request for {len(urls)} URL(s)")
    
    try:
        # Step 1: Get JSON analysis results
        fetch_results = await fetch_multiple_html(urls)
        
        analysis_tasks = []
        results = []
        
        for fetch_result in fetch_results:
            if fetch_result['status'] == 'success':
                task = analyze_single_report(
                    fetch_result['url'],
                    fetch_result['html_content']
                )
                analysis_tasks.append(task)
            else:
                results.append({
                    "error": fetch_result.get('error', 'Unknown fetch error'),
                    "url": fetch_result['url']
                })
        
        if analysis_tasks:
            analysis_results = await asyncio.gather(*analysis_tasks)
            results.extend(analysis_results)
        
        # Step 2: Render HTML for each successful analysis
        logger.info(f"Rendering {len(results)} HTML report(s)...")
        html_results = html_renderer.render_multiple(results)
        
        # Step 3: Convert each HTML to PDF
        logger.info(f"Converting {len(html_results)} report(s) to PDF...")
        pdf_results = []
        
        for html_result in html_results:
            if 'error' in html_result:
                # Pass through errors
                pdf_results.append(html_result)
            elif 'html' in html_result:
                try:
                    client_name = html_result.get('client_name', 'Unknown')
                    
                    # Generate PDF - AWAIT ADDED HERE
                    pdf_bytes = await pdf_generator.html_string_to_pdf(
                        html_result['html'],
                        client_name
                    )
                    
                    # Encode to base64 for JSON transmission
                    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    
                    # Clean filename
                    safe_name = client_name.replace(' ', '_').replace('/', '_')
                    filename = f"{safe_name}_AffordabilityReport.pdf"
                    
                    pdf_results.append({
                        'url': html_result.get('url', 'unknown'),
                        'pdf_base64': pdf_base64,
                        'client_name': client_name,
                        'filename': filename,
                        'size_bytes': len(pdf_bytes)
                    })
                    
                    logger.info(f"Generated PDF for {client_name}: {len(pdf_bytes):,} bytes")
                    
                except Exception as e:
                    error_msg = f"{type(e).__name__}: {str(e)}" if str(e) else type(e).__name__
                    logger.error(f"PDF generation failed for {client_name}: {error_msg}", exc_info=True)
                    pdf_results.append({
                        'url': html_result.get('url', 'unknown'),
                        'error': f'PDF generation failed: {error_msg}',
                        'client_name': html_result.get('client_name', 'Unknown')
                    })
            else:
                pdf_results.append({
                    'url': html_result.get('url', 'unknown'),
                    'error': 'Unexpected result format'
                })
        
        logger.info(f"PDF generation complete: {len(pdf_results)} results")
        return pdf_results
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_reports_pdf: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/analyze-html")
async def analyze_reports_html(request: AnalyzeRequest):
    """
    Analyze credit reports and return rendered HTML for each.
    
    This endpoint performs the same analysis as /analyze but returns
    rendered HTML reports instead of JSON.
    
    Example request:
    ```json
    {
        "urls": [
            "https://example.com/report1.html",
            "https://example.com/report2.html"
        ]
    }
    ```
    
    Returns array of objects with:
    - url: The source URL
    - html: Rendered HTML report (or null if error)
    - client_name: Name of the client (for reference)
    - error: Error message (if applicable)
    
    Example response:
    ```json
    [
        {
            "url": "https://example.com/report1.html",
            "html": "<!DOCTYPE html>...",
            "client_name": "JOHN DOE"
        },
        {
            "url": "https://example.com/report2.html",
            "error": "Analysis failed: Invalid HTML"
        }
    ]
    ```
    """
    urls = request.urls
    logger.info(f"Received HTML analysis request for {len(urls)} URL(s)")
    
    try:
        # Step 1: Get JSON analysis results
        # We'll reuse the existing analyze logic
        fetch_results = await fetch_multiple_html(urls)
        
        analysis_tasks = []
        results = []
        
        for fetch_result in fetch_results:
            if fetch_result['status'] == 'success':
                task = analyze_single_report(
                    fetch_result['url'],
                    fetch_result['html_content']
                )
                analysis_tasks.append(task)
            else:
                results.append({
                    "error": fetch_result.get('error', 'Unknown fetch error'),
                    "url": fetch_result['url']
                })
        
        if analysis_tasks:
            analysis_results = await asyncio.gather(*analysis_tasks)
            results.extend(analysis_results)
        
        # Step 2: Render HTML for each successful analysis
        logger.info(f"Rendering {len(results)} HTML report(s)...")
        html_results = html_renderer.render_multiple(results)
        
        logger.info(f"HTML rendering complete: {len(html_results)} reports")
        
        return html_results
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_reports_html: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/generate-claim-letters")
async def generate_claim_letters(analysis_results: List[Dict[str, Any]]):
    """
    Generate Letters of Claim from credit analysis JSON.
    
    This endpoint accepts the JSON output from /analyze and generates
    individual Word documents for each in-scope lender.
    
    IMPORTANT: Bank details are now extracted DYNAMICALLY from the JSON:
    - Bank: Uses defendant/lender name
    - Account Name: Uses client name from JSON
    - Account Number: From client_info.bank_details.account_number (or "TBC")
    - Sort Code: From client_info.bank_details.sort_code (or "TBC")
    
    Example request (JSON from /analyze endpoint):
    ```json
    [
        {
            "url": "...",
            "credit_analysis": {
                "client_info": {
                    "name": "JOHN DOE",
                    "address": "123 Main St\nLondon\nSW1A 1AA",
                    "bank_details": {  // OPTIONAL
                        "account_number": "12345678",
                        "sort_code": "12-34-56"
                    }
                },
                "claims_analysis": {
                    "in_scope": [
                        {
                            "name": "VANQUIS BANK",
                            "type": "Credit Card",
                            ...
                        }
                    ]
                }
            }
        }
    ]
    ```
    
    Returns a ZIP file containing all generated letters.
    """
    logger.info(f"Received claim letter generation request for {len(analysis_results)} report(s)")
    
    try:
        # Create in-memory ZIP file
        memory_file = BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            letter_count = 0
            
            # Process each credit report
            for report_data in analysis_results:
                # Skip if there's an error in the report
                if 'error' in report_data:
                    logger.warning(f"Skipping report with error: {report_data.get('url', 'unknown')}")
                    continue
                
                credit_analysis = report_data.get('credit_analysis', {})
                client_info = credit_analysis.get('client_info', {})
                client_name = client_info.get('name', 'Unknown_Client')
                
                # Clean client name for filename
                safe_client_name = ''.join(c if c.isalnum() or c in [' ', '_'] else '_' for c in client_name)
                safe_client_name = safe_client_name.replace(' ', '_')
                
                claims_analysis = credit_analysis.get('claims_analysis', {})
                in_scope_lenders = claims_analysis.get('in_scope', [])
                
                if not in_scope_lenders:
                    logger.info(f"No in-scope lenders for {client_name}")
                    continue
                
                logger.info(f"Processing {client_name}: {len(in_scope_lenders)} in-scope lender(s)")
                
                # Generate a letter for each in-scope lender
                for lender in in_scope_lenders:
                    lender_name = lender.get('name', 'Unknown_Lender')
                    safe_lender_name = ''.join(c if c.isalnum() or c in [' ', '_'] else '_' for c in lender_name)
                    safe_lender_name = safe_lender_name.replace(' ', '_')
                    
                    # Generate filename
                    filename = f"{safe_client_name}_{safe_lender_name}_LOC.docx"
                    
                    try:
                        from docx import Document
                        from datetime import datetime
                        import tempfile
                        import os
                        
                        # Use the enhanced generate_letter method that includes:
                        # - Metric extraction from credit data
                        # - Conditional section removal
                        # - Placeholder replacement with calculated values
                        
                        # Create a temporary file for the letter
                        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.docx') as tmp_file:
                            tmp_path = tmp_file.name
                        
                        try:
                            # Generate letter using the enhanced method
                            success = claim_letter_generator.generate_letter(
                                tmp_path,
                                report_data,
                                lender,
                                debug=False
                            )
                            
                            if success:
                                # Read the generated file and add to ZIP
                                with open(tmp_path, 'rb') as f:
                                    zf.writestr(filename, f.read())
                                
                                letter_count += 1
                                logger.info(f"  ✓ {lender_name}")
                            else:
                                logger.error(f"  ✗ {lender_name} - Generation returned False")
                        
                        finally:
                            # Clean up temp file
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                        
                    except Exception as e:
                        logger.error(f"  ✗ {lender_name} - Failed: {str(e)}")
                        continue
            
            if letter_count == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No letters generated - no in-scope lenders found"
                )
        
        memory_file.seek(0)
        
        logger.info(f"Successfully generated {letter_count} letter(s)")
        
        # Return ZIP file
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return StreamingResponse(
            memory_file,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=claim_letters_{timestamp}.zip"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_claim_letters: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/analyze-pdf-and-letters")
async def analyze_pdf_and_letters(request: AnalyzeRequest):
    """
    COMBINED ENDPOINT: Analyze credit reports and generate both PDFs, HTML, and Claim Letters.
    
    This endpoint does everything in one call:
    1. Analyzes credit reports from URLs (processed in batches of 10)
    2. Generates HTML reports
    3. Generates PDF reports
    4. Generates Letters of Claim for all in-scope lenders (with DYNAMIC bank details)
    
    Processes URLs in batches to ensure all URLs are handled.
    Can process any number of URLs (e.g., 30+) by queuing them in batches.
    
    Bank details in letters are extracted from JSON:
    - Bank: Defendant/lender name
    - Account Name: Client name
    - Account Number/Sort Code: From bank_details in JSON (or "TBC")
    
    Returns JSON array of files with base64-encoded content, organized by client.
    Each file includes metadata for organizing into folders in n8n:
    
    Example request:
    ```json
    {
        "urls": [
            "https://example.com/report1.html",
            "https://example.com/report2.html"
        ]
    }
    ```
    
    Returns: JSON array of files:
    ```json
    [
        {
            "client_name": "JOHN_DOE",
            "file_type": "PDF",
            "filename": "JOHN_DOE_AffordabilityReport.pdf",
            "file_content_base64": "JVBERi0x...",
            "suggested_path": "JOHN_DOE/PDF/",
            "size_bytes": 12345
        },
        {
            "client_name": "JOHN_DOE",
            "file_type": "HTML",
            "filename": "JOHN_DOE_AffordabilityReport.html",
            "file_content_base64": "PCFET0NUW...",
            "suggested_path": "JOHN_DOE/HTML/",
            "size_bytes": 98765
        },
        {
            "client_name": "JOHN_DOE",
            "file_type": "DOCX",
            "filename": "JOHN_DOE_VANQUIS_BANK_LOC.docx",
            "file_content_base64": "UEsDBBQA...",
            "suggested_path": "JOHN_DOE/LOCS/",
            "size_bytes": 45678
        }
    ]
    ```
    """
    urls = request.urls
    logger.info("=" * 60)
    logger.info(f"COMBINED ENDPOINT: Received request for {len(urls)} URL(s)")
    logger.info("=" * 60)
    
    try:
        # ==========================================
        # STEP 1: ANALYZE CREDIT REPORTS
        # ==========================================
        logger.info("Step 1: Fetching and analyzing credit reports...")
        fetch_results = await fetch_multiple_html(urls)
        
        analysis_tasks = []
        analysis_results = []
        
        for fetch_result in fetch_results:
            if fetch_result['status'] == 'success':
                task = analyze_single_report(
                    fetch_result['url'],
                    fetch_result['html_content']
                )
                analysis_tasks.append(task)
            else:
                analysis_results.append({
                    "error": fetch_result.get('error', 'Unknown fetch error'),
                    "url": fetch_result['url']
                })
        
        if analysis_tasks:
            results = await asyncio.gather(*analysis_tasks)
            analysis_results.extend(results)
        
        successful_analyses = sum(1 for r in analysis_results if 'credit_analysis' in r)
        failed_analyses = sum(1 for r in analysis_results if 'error' in r)
        
        logger.info(f"Analysis phase complete: {successful_analyses} successful, {failed_analyses} failed")
        
        # ==========================================
        # STEP 2: GENERATE HTML & PDFs
        # ==========================================
        logger.info("Step 2: Generating HTML and PDF reports...")
        html_results = html_renderer.render_multiple(analysis_results)
        
        # Array to store all files for JSON response
        all_files = []
        
        for html_result in html_results:
            if 'error' not in html_result and 'html' in html_result:
                try:
                    client_name = html_result.get('client_name', 'Unknown')
                    safe_name = client_name.replace(' ', '_').replace('/', '_')
                    
                    # ==========================================
                    # ADD HTML FILE
                    # ==========================================
                    html_filename = f"{safe_name}_AffordabilityReport.html"
                    html_bytes = html_result['html'].encode('utf-8')
                    html_base64 = base64.b64encode(html_bytes).decode('utf-8')
                    
                    all_files.append({
                        "client_name": safe_name,
                        "file_type": "HTML",
                        "filename": html_filename,
                        "file_content_base64": html_base64,
                        "suggested_path": f"{safe_name}/HTML/",
                        "size_bytes": len(html_bytes)
                    })
                    logger.info(f"  ✓ HTML: {html_filename} ({len(html_bytes):,} bytes)")
                    
                    # ==========================================
                    # GENERATE AND ADD PDF FILE
                    # ==========================================
                    pdf_bytes = await pdf_generator.html_string_to_pdf(
                        html_result['html'],
                        client_name
                    )
                    
                    pdf_filename = f"{safe_name}_AffordabilityReport.pdf"
                    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    
                    all_files.append({
                        "client_name": safe_name,
                        "file_type": "PDF",
                        "filename": pdf_filename,
                        "file_content_base64": pdf_base64,
                        "suggested_path": f"{safe_name}/PDF/",
                        "size_bytes": len(pdf_bytes)
                    })
                    logger.info(f"  ✓ PDF: {pdf_filename} ({len(pdf_bytes):,} bytes)")
                    
                except Exception as e:
                    logger.error(f"  ✗ HTML/PDF failed for {client_name}: {e}")
        
        # ==========================================
        # STEP 3: GENERATE CLAIM LETTERS
        # ==========================================
        logger.info("Step 3: Generating Letters of Claim...")
        
        for report_data in analysis_results:
            if 'error' in report_data:
                continue
            
            credit_analysis = report_data.get('credit_analysis', {})
            client_info = credit_analysis.get('client_info', {})
            client_name = client_info.get('name', 'Unknown_Client')
            
            safe_client_name = ''.join(c if c.isalnum() or c in [' ', '_'] else '_' for c in client_name)
            safe_client_name = safe_client_name.replace(' ', '_')
            
            claims_analysis = credit_analysis.get('claims_analysis', {})
            in_scope_lenders = claims_analysis.get('in_scope', [])
            
            if not in_scope_lenders:
                continue
            
            logger.info(f"Processing {client_name}: {len(in_scope_lenders)} in-scope lender(s)")
            
            for lender in in_scope_lenders:
                lender_name = lender.get('name', 'Unknown_Lender')
                safe_lender_name = ''.join(c if c.isalnum() or c in [' ', '_'] else '_' for c in lender_name)
                safe_lender_name = safe_lender_name.replace(' ', '_')
                
                filename = f"{safe_client_name}_{safe_lender_name}_LOC.docx"
                
                try:
                    from datetime import datetime
                    import tempfile
                    import os
                    
                    # Create a temporary file for the letter
                    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.docx') as tmp_file:
                        tmp_path = tmp_file.name
                    
                    try:
                        # Generate letter using the enhanced method
                        success = claim_letter_generator.generate_letter(
                            tmp_path,
                            report_data,
                            lender,
                            debug=False
                        )
                        
                        if success:
                            # Read the generated file and encode to base64
                            with open(tmp_path, 'rb') as f:
                                docx_bytes = f.read()
                            
                            docx_base64 = base64.b64encode(docx_bytes).decode('utf-8')
                            
                            all_files.append({
                                "client_name": safe_client_name,
                                "file_type": "DOCX",
                                "filename": filename,
                                "file_content_base64": docx_base64,
                                "suggested_path": f"{safe_client_name}/LOCS/",
                                "size_bytes": len(docx_bytes)
                            })
                            
                            logger.info(f"  ✓ Letter: {filename}")
                        else:
                            logger.error(f"  ✗ Letter failed: {filename} - Generation returned False")
                    
                    finally:
                        # Clean up temp file
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                    
                except Exception as e:
                    logger.error(f"  ✗ Letter failed: {filename} - {str(e)}")
        
        # ==========================================
        # SUMMARY
        # ==========================================
        html_count = sum(1 for f in all_files if f['file_type'] == 'HTML')
        pdf_count = sum(1 for f in all_files if f['file_type'] == 'PDF')
        docx_count = sum(1 for f in all_files if f['file_type'] == 'DOCX')
        unique_clients = len(set(f['client_name'] for f in all_files))
        
        logger.info("=" * 60)
        logger.info(f"✓ GENERATION COMPLETE - {len(urls)} URLs processed")
        logger.info(f"  - {unique_clients} unique client(s)")
        logger.info(f"  - {html_count} HTML report(s)")
        logger.info(f"  - {pdf_count} PDF report(s)")
        logger.info(f"  - {docx_count} claim letter(s)")
        logger.info(f"  - Total: {len(all_files)} files generated")
        logger.info("=" * 60)
        
        # Return JSON array of all files
        return all_files
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_pdf_and_letters: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ── Company branding endpoints ─────────────────────────────────────────────

@app.get("/company/{company_name}")
async def lookup_company(company_name: str):
    """Return stored branding config for a company, or 404 if unknown."""
    config = get_company(company_name)
    if not config:
        raise HTTPException(status_code=404, detail="Company not found")
    # Expose logo as a web-accessible URL instead of an absolute path
    if config.get('logo_path') and os.path.exists(config['logo_path']):
        rel = os.path.relpath(config['logo_path'], str(Path(__file__).parent / 'static'))
        config = {**config, 'logo_url': '/static/' + rel.replace(os.sep, '/')}
    return config


@app.post("/company/config")
async def upsert_company(
    company_name:    str           = Form(...),
    footer_message:  str           = Form(''),
    logo:            UploadFile    = File(None),
):
    """Save or update company branding. Uploaded logo is stored locally."""
    logo_path = ''
    if logo and logo.filename:
        os.makedirs(LOGO_DIR, exist_ok=True)
        ext       = os.path.splitext(logo.filename)[1].lower() or '.png'
        slug      = ''.join(c if c.isalnum() else '_' for c in company_name.lower())
        logo_path = os.path.join(LOGO_DIR, f"{slug}{ext}")
        with open(logo_path, 'wb') as fh:
            fh.write(await logo.read())
        logger.info(f"Saved logo for '{company_name}' → {logo_path}")

    config = save_company(company_name, footer_message=footer_message, logo_path=logo_path)
    logger.info(f"Upserted company config: {company_name}")
    return config


@app.post("/batch-process-csv", response_model=CSVBatchProcessResult)
async def batch_process_csv(
    file:         UploadFile = File(...),
    company_name: str        = "Tracker",
):
    """
    Process a CSV file containing credit report links.

    Steps:
    1. Parse CSV, extract 'Credit File Link' column
    2. Analyse each credit report
    3. Generate PDF, HTML, and claim letter (DOCX) for each
    4. Upload all files to Google Drive under:
           <root>/<Client Name>/PDF/
           <root>/<Client Name>/HTML/
           <root>/<Client Name>/LOC/
    5. Write per-client rows to Google Sheets with clickable Drive links
    6. Return summary + per-client Drive links for display in the UI

    Also fully usable via curl:

        curl -X POST http://localhost:8000/batch-process-csv \\
             -F "file=@input.csv" \\
             -F "sheet_name=Tracker"

    Response JSON:
    {
        "total_processed": 3,
        "successful": 3,
        "failed": 0,
        "drive_uploads": 9,
        "sheet_updates": 3,
        "errors": [],
        "message": "...",
        "sheets_url": "https://docs.google.com/...",
        "client_drive_links": [
            {
                "client_name": "JOHN DOE",
                "client_folder_link": "https://drive.google.com/...",
                "pdf_link":  "https://drive.google.com/...",
                "html_link": "https://drive.google.com/...",
                "loc_link":  "https://drive.google.com/...",
                "error": null
            }
        ]
    }
    """
    sheet_name = company_name
    branding   = get_company(company_name)  # None when company not found / no branding

    logger.info("=" * 60)
    logger.info(f"CSV batch processing started: {file.filename} | company: {company_name}")
    logger.info("=" * 60)

    try:
        # ── Step 1: Parse CSV ──────────────────────────────────────
        contents = await file.read()
        try:
            df = pd.read_csv(BytesIO(contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

        if "Credit File Link" not in df.columns:
            raise HTTPException(
                status_code=400,
                detail=f"CSV must contain 'Credit File Link' column. Found: {', '.join(df.columns)}"
            )

        urls = [u.strip() for u in df["Credit File Link"].dropna().astype(str).tolist() if u.strip()]
        if not urls:
            raise HTTPException(status_code=400, detail="No valid URLs found in 'Credit File Link' column")

        logger.info(f"Found {len(urls)} URL(s) to process")

        # ── Build URL → CSV row data mapping ───────────────────────
        def safe_str(val):
            """Convert value to string, return empty string if NaN/None."""
            if pd.isna(val):
                return ''
            return str(val).strip()

        csv_row_by_url: dict[str, dict] = {}
        for _, row in df.iterrows():
            url = safe_str(row.get('Credit File Link', ''))
            if url:
                csv_row_by_url[url] = {
                    'title': safe_str(row.get('Client 1 Title', '')),
                    'first_name': safe_str(row.get('Client 1 First Name', '')),
                    'surname': safe_str(row.get('Client 1 Surname', '')),
                    'date_of_birth': safe_str(row.get('Client 1 DOB', '')),
                    'email': (
                        safe_str(row.get('Client 1 E-mail Address')) or
                        safe_str(row.get('Client 1 Email')) or
                        safe_str(row.get('Email')) or
                        safe_str(row.get('E-mail')) or
                        ''
                    ),
                    'phone': safe_str(row.get('Client 1 Phone Number', '')),
                    'residence_1': safe_str(row.get('Client 1 Residential Address Line 1', '')),
                    'residence_2': safe_str(row.get('Client 1 Residential Address Line 2', '')),
                    'residence_3': safe_str(row.get('Client 1 Residential Address Line 3', '')),
                    'postal_code': safe_str(row.get('Client 1 Residential Postcode', '')),
                    'defendant': safe_str(row.get('Defendant', '')),
                }

        # ── Step 2: Fetch & analyse ────────────────────────────────
        fetch_results = await fetch_multiple_html(urls)
        analysis_tasks, analysis_results = [], []

        for fr in fetch_results:
            if fr['status'] == 'success':
                analysis_tasks.append(analyze_single_report(fr['url'], fr['html_content']))
            else:
                analysis_results.append({'error': fr.get('error', 'Fetch failed'), 'url': fr['url']})

        if analysis_tasks:
            analysis_results.extend(await asyncio.gather(*analysis_tasks))

        successful_analyses = sum(1 for r in analysis_results if 'credit_analysis' in r)
        logger.info(f"Analysed {successful_analyses}/{len(analysis_results)} reports")

        # ── Step 3: Generate HTML, PDF, and DOCX ──────────────────
        html_results = html_renderer.render_multiple(analysis_results)

        # Build a lookup: client_name -> analysis_result (for DOCX step)
        analysis_by_url = {r.get('url', ''): r for r in analysis_results}

        # ── Step 4: Upload to Drive (per-client folder structure) ──
        uploader = get_drive_uploader()
        tracker  = get_sheets_tracker()
        await tracker.initialize_sheet(sheet_name=sheet_name)

        # We accumulate per-client link info for the UI and Sheets
        # client_summary: client_name -> { client_folder_link, pdf_link, html_link, loc_link, error }
        client_summary: dict[str, dict] = {}

        upload_count = 0
        tracking_records = []
        errors = []

        for html_result in html_results:
            if 'error' in html_result:
                client_name = html_result.get('client_name', 'Unknown')
                url_fail    = html_result.get('url', '')
                error_msg   = html_result['error']
                errors.append({'client_name': client_name, 'error': error_msg, 'url': url_fail, 'csv_data': csv_row_by_url.get(url_fail, {})})
                log_failure(client_name, error_msg, url=url_fail)
                tracking_records.append({
                    'client_name':     client_name,
                    'credit_url':      url_fail,
                    'analysis_result': {'error': error_msg},
                    'drive_result':    {'success': False, 'error': error_msg},
                    'csv_row_data':    csv_row_by_url.get(url_fail, {}),
                })
                continue

            client_name = html_result.get('client_name', 'Unknown')
            url         = html_result.get('url', '')

            try:
                # ── 3a: Generate PDF ───────────────────────────────
                pdf_bytes = await pdf_generator.html_string_to_pdf(html_result['html'], client_name)
                safe_name = client_name.replace(' ', '_').replace('/', '_')
                pdf_filename  = f"{safe_name}_AffordabilityReport.pdf"
                html_filename = f"{safe_name}_AffordabilityReport.html"

                # ── 3b: Ensure client folder structure exists ──────
                folders = uploader.get_client_subfolders(client_name)

                # Keep folder links (Drive folder URLs use the same URL structure)
                def folder_url(fid): return f"https://drive.google.com/drive/folders/{fid}"
                client_folder_link = folder_url(folders['client'])
                pdf_folder_link    = folder_url(folders['PDF'])
                html_folder_link   = folder_url(folders['HTML'])
                loc_folder_link    = folder_url(folders['LOC'])

                # ── 3c: Upload PDF ─────────────────────────────────
                pdf_result = await uploader.upload_file_to_client_folder(
                    file_bytes=pdf_bytes,
                    filename=pdf_filename,
                    client_name=client_name,
                    file_type='PDF',
                    mime_type='application/pdf'
                )
                pdf_view_link = pdf_result.get('web_view_link', pdf_folder_link)
                pdf_download_link = pdf_result.get('web_content_link', '')
                upload_count += 1

                # ── 3d: Upload HTML ────────────────────────────────
                html_bytes = html_result['html'].encode('utf-8')
                html_up = await uploader.upload_file_to_client_folder(
                    file_bytes=html_bytes,
                    filename=html_filename,
                    client_name=client_name,
                    file_type='HTML',
                    mime_type='text/html'
                )
                html_view_link = html_up.get('web_view_link', html_folder_link)
                html_download_link = html_up.get('web_content_link', '')
                upload_count += 1

                # ── 3e: Upload DOCX claim letters ──────────────────
                loc_link = loc_folder_link  # default to folder if no letters
                analysis_result = analysis_by_url.get(url, {})
                
                # Collect LOC uploads for per-defendant tracking
                loc_uploads: list[dict] = []

                if 'credit_analysis' in analysis_result:
                    credit_analysis = analysis_result['credit_analysis']
                    in_scope = credit_analysis.get('claims_analysis', {}).get('in_scope', [])

                    for lender in in_scope:
                        lender_name     = lender.get('name', 'Unknown_Lender')
                        safe_lender     = ''.join(c if c.isalnum() or c in [' ', '_'] else '_' for c in lender_name).replace(' ', '_')
                        docx_filename   = f"{safe_name}_{safe_lender}_LOC.docx"

                        import tempfile, os as _os
                        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.docx') as tmp:
                            tmp_path = tmp.name
                        try:
                            success = claim_letter_generator.generate_letter(
                                tmp_path, analysis_result, lender, debug=False,
                                branding=branding,
                            )
                            if success:
                                with open(tmp_path, 'rb') as f:
                                    docx_bytes = f.read()

                                loc_up = await uploader.upload_file_to_client_folder(
                                    file_bytes=docx_bytes,
                                    filename=docx_filename,
                                    client_name=client_name,
                                    file_type='LOC',
                                    mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                                )
                                # Store each LOC upload with defendant info
                                loc_uploads.append({
                                    'defendant': lender_name,
                                    'loc_view_link': loc_up.get('web_view_link', loc_folder_link),
                                    'loc_download_link': loc_up.get('web_content_link', ''),
                                    'filename': docx_filename,
                                })
                                upload_count += 1
                        finally:
                            if _os.path.exists(tmp_path):
                                _os.unlink(tmp_path)

                # ── 3f: Store per-client summary ───────────────────
                client_summary[client_name] = {
                    'client_name':         client_name,
                    'client_folder_link':  client_folder_link,
                    'pdf_link':            pdf_view_link,
                    'html_link':           html_view_link,
                    'loc_link':            loc_folder_link,   # always the LOC subfolder
                    'error':               None,
                }

                # ── 3g: Tracking records for Sheets (one per LOC document) ─
                csv_data = csv_row_by_url.get(url, {})
                
                if loc_uploads:
                    # Create one row per LOC document
                    for loc_info in loc_uploads:
                        # Override defendant with the lender name for this LOC
                        row_csv_data = csv_data.copy()
                        row_csv_data['defendant'] = loc_info['defendant']
                        
                        tracking_records.append({
                            'client_name':    client_name,
                            'credit_url':     url,
                            'analysis_result': analysis_result,
                            'drive_result': {
                                'success':             True,
                                'client_folder_link':  client_folder_link,
                                'pdf_view_link':       pdf_view_link,
                                'pdf_download_link':   pdf_download_link,
                                'html_view_link':      html_view_link,
                                'html_download_link':  html_download_link,
                                'loc_view_link':       loc_info['loc_view_link'],
                                'loc_download_link':   loc_info['loc_download_link'],
                            },
                            'csv_row_data': row_csv_data,
                        })
                else:
                    # No LOC documents, create single row with folder link
                    tracking_records.append({
                        'client_name':    client_name,
                        'credit_url':     url,
                        'analysis_result': analysis_result,
                        'drive_result': {
                            'success':             True,
                            'client_folder_link':  client_folder_link,
                            'pdf_view_link':       pdf_view_link,
                            'pdf_download_link':   pdf_download_link,
                            'html_view_link':      html_view_link,
                            'html_download_link':  html_download_link,
                            'loc_view_link':       loc_folder_link,
                            'loc_download_link':   '',  # No download for folder
                        },
                        'csv_row_data': csv_data,
                    })

            except Exception as e:
                logger.error(f"Processing failed for {client_name}: {e}", exc_info=True)
                error_str = str(e)
                errors.append({'client_name': client_name, 'error': error_str, 'url': url, 'csv_data': csv_row_by_url.get(url, {})})
                log_failure(client_name, error_str, url=url)
                client_summary[client_name] = {
                    'client_name':        client_name,
                    'client_folder_link': '',
                    'pdf_link':           '',
                    'html_link':          '',
                    'loc_link':           '',
                    'error':              error_str,
                }
                tracking_records.append({
                    'client_name':     client_name,
                    'credit_url':      url,
                    'analysis_result': {'error': error_str},
                    'drive_result':    {'success': False, 'error': error_str},
                    'csv_row_data':    csv_row_by_url.get(url, {}),
                })

        # ── Step 5: Write to Google Sheets ─────────────────────────
        if tracking_records:
            await tracker.append_multiple_records(tracking_records, sheet_name=sheet_name)
        logger.info(f"Wrote {len(tracking_records)} rows to Sheets")

        # ── Step 6: Build response ─────────────────────────────────
        total      = len(analysis_results)
        successful = sum(1 for v in client_summary.values() if v['error'] is None)
        failed     = len(errors)

        sheets_url = None
        if GOOGLE_SHEETS_ID:
            sheets_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit"

        logger.info("=" * 60)
        logger.info(f"BATCH COMPLETE — {successful}/{total} succeeded, {upload_count} files uploaded")
        logger.info("=" * 60)

        return CSVBatchProcessResult(
            total_processed=total,
            successful=successful,
            failed=failed,
            drive_uploads=upload_count,
            sheet_updates=len(tracking_records),
            errors=errors,
            message=(
                f"Processed {successful}/{total} reports. "
                f"{upload_count} files uploaded to Google Drive. "
                f"{len(tracking_records)} records added to Google Sheets."
            ),
            sheets_url=sheets_url,
            client_drive_links=list(client_summary.values())
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "error": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )