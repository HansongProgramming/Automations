from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
import asyncio
from typing import List, Dict, Any
import logging
import sys
import zipfile
from io import BytesIO
import base64

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from .models import AnalyzeRequest, AnalyzeResponse, SingleReportResult
from .utils.html_fetcher import fetch_multiple_html
from .analyzer.credit_analyzer import CreditReportAnalyzer
from .utils.template_renderer import HTMLTemplateRenderer
from .utils.pdf_generator import pdf_generator
from .claim_letters.generator import ClaimLetterGenerator
from .claim_letters.config import TEMPLATE_PATH  # REMOVED BANK_DETAILS - now dynamic

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
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Credit Report Analyzer API is running",
        "version": "1.0.0"
    }


@app.get("/health")
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
    
    Processes up to 10 URLs concurrently. Works with single or multiple URLs.
    
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
        logger.info(f"Analyzing {len(analysis_tasks)} report(s)...")
        
        if analysis_tasks:
            analysis_results = await asyncio.gather(*analysis_tasks)
            results.extend(analysis_results)
        
        logger.info(f"Analysis complete: {len(results)} total results")
        
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
            "filename": "JOHN_DOE_credit_report.pdf"
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
                    filename = f"{safe_name}_credit_report.pdf"
                    
                    pdf_results.append({
                        'url': html_result.get('url', 'unknown'),
                        'pdf_base64': pdf_base64,
                        'client_name': client_name,
                        'filename': filename,
                        'size_bytes': len(pdf_bytes)
                    })
                    
                    logger.info(f"Generated PDF for {client_name}: {len(pdf_bytes):,} bytes")
                    
                except Exception as e:
                    logger.error(f"PDF generation failed for {client_name}: {e}")
                    pdf_results.append({
                        'url': html_result.get('url', 'unknown'),
                        'error': f'PDF generation failed: {str(e)}',
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
                        
                        # Load template
                        doc = Document(TEMPLATE_PATH)
                        
                        # Parse client information
                        client_name_parts = claim_letter_generator.parse_client_name(client_info['name'])
                        client_address = claim_letter_generator.parse_address(client_info['address'])
                        
                        # DYNAMIC: Extract bank details from JSON
                        bank_details = claim_letter_generator.extract_bank_details_from_json(report_data)
                        
                        # DYNAMIC: Get defendant address (checks config then JSON)
                        defendant_address = claim_letter_generator.get_defendant_address(lender_name, lender)
                        
                        # Get current date
                        current_date = datetime.now().strftime('%d/%m/%Y')
                        account_details = claim_letter_generator.extract_account_details_from_lender(lender)

                        # Prepare replacements with DYNAMIC data
                        replacements = {
                            '{Date}': current_date,
                            '{Defendant Name}': lender_name,
                            '{Defendant Address}': defendant_address,
                            '{Client First Name}': client_name_parts['first_name'],
                            '{Client Surname}': client_name_parts['surname'],
                            '{Address Line 1}': client_address['line1'],
                            '{Address Line 2}': client_address['line2'],
                            '{Address Line 3}': client_address['line3'],
                            '{Postcode}': client_address['postcode'],
                            '{Bank}': lender_name,  # DEFENDANT NAME as bank
                            '{Account Name}': client_info['name'],  # CLIENT NAME as account name
                            '{Account Number}': account_details['account_number'],
                            '{Sort Code}': bank_details.get('sort_code', 'TBC'),
                            '{Agreement Number}': 'TBC',
                            '{Agreement Start Date}': account_details['start_date'],
                            '{Report Received Date}': current_date,
                            '{Report Outcome}': 'unaffordable',
                        }
                        
                        # Replace all placeholders
                        claim_letter_generator.replace_placeholders(doc, replacements)
                        
                        # Save to BytesIO
                        doc_bytes = BytesIO()
                        doc.save(doc_bytes)
                        doc_bytes.seek(0)
                        
                        # Add to ZIP
                        zf.writestr(filename, doc_bytes.getvalue())
                        letter_count += 1
                        
                        logger.info(f"  ✓ {lender_name}")
                        
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
    COMBINED ENDPOINT: Analyze credit reports and generate both PDFs and Claim Letters.
    
    This endpoint does everything in one call:
    1. Analyzes credit reports from URLs
    2. Generates PDF reports
    3. Generates Letters of Claim for all in-scope lenders (with DYNAMIC bank details)
    
    Bank details in letters are extracted from JSON:
    - Bank: Defendant/lender name
    - Account Name: Client name
    - Account Number/Sort Code: From bank_details in JSON (or "TBC")
    
    Returns a ZIP file containing:
    - PDF reports (one per client)
    - Claim letters (one per in-scope lender per client)
    
    Example request:
    ```json
    {
        "urls": [
            "https://example.com/report1.html",
            "https://example.com/report2.html"
        ]
    }
    ```
    
    Returns: ZIP file with structure:
    ```
    analysis_20260131_143022.zip
    ├── pdfs/
    │   ├── JOHN_DOE_credit_report.pdf
    │   └── JANE_SMITH_credit_report.pdf
    └── claim_letters/
        ├── JOHN_DOE_VANQUIS_BANK_LOC.docx
        ├── JOHN_DOE_CAPITAL_ONE_LOC.docx
        └── JANE_SMITH_INDIGO_LOC.docx
    ```
    """
    urls = request.urls
    logger.info(f"Received combined analysis request for {len(urls)} URL(s)")
    
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
        
        logger.info(f"Analysis complete: {len(analysis_results)} results")
        
        # ==========================================
        # STEP 2: GENERATE PDFs
        # ==========================================
        logger.info("Step 2: Generating PDF reports...")
        html_results = html_renderer.render_multiple(analysis_results)
        
        pdf_files = {}  # {filename: pdf_bytes}
        
        for html_result in html_results:
            if 'error' not in html_result and 'html' in html_result:
                try:
                    client_name = html_result.get('client_name', 'Unknown')
                    
                    # Generate PDF
                    pdf_bytes = await pdf_generator.html_string_to_pdf(
                        html_result['html'],
                        client_name
                    )
                    
                    # Clean filename
                    safe_name = client_name.replace(' ', '_').replace('/', '_')
                    filename = f"{safe_name}_credit_report.pdf"
                    
                    pdf_files[filename] = pdf_bytes
                    logger.info(f"  ✓ PDF: {filename} ({len(pdf_bytes):,} bytes)")
                    
                except Exception as e:
                    logger.error(f"  ✗ PDF failed for {client_name}: {e}")
        
        # ==========================================
        # STEP 3: GENERATE CLAIM LETTERS
        # ==========================================
        logger.info("Step 3: Generating Letters of Claim...")
        letter_files = {}  # {filename: docx_bytes}
        
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
                    from docx import Document
                    from datetime import datetime
                    
                    # Load template
                    doc = Document(TEMPLATE_PATH)
                    
                    # Parse client information
                    client_name_parts = claim_letter_generator.parse_client_name(client_info['name'])
                    client_address = claim_letter_generator.parse_address(client_info['address'])
                    
                    # DYNAMIC: Extract bank details from JSON
                    bank_details = claim_letter_generator.extract_bank_details_from_json(report_data)
                    
                    # ✅ ADD THIS: Extract account details from lender
                    account_details = claim_letter_generator.extract_account_details_from_lender(lender)
                    
                    # DYNAMIC: Get defendant address
                    defendant_address = claim_letter_generator.get_defendant_address(lender_name, lender)
                    
                    current_date = datetime.now().strftime('%d/%m/%Y')
                    
                    # Prepare replacements with DYNAMIC data
                    replacements = {
                        '{Date}': current_date,
                        '{Defendant Name}': lender_name,
                        '{Defendant Address}': defendant_address,
                        '{Client First Name}': client_name_parts['first_name'],
                        '{Client Surname}': client_name_parts['surname'],
                        '{Address Line 1}': client_address['line1'],
                        '{Address Line 2}': client_address['line2'],
                        '{Address Line 3}': client_address['line3'],
                        '{Postcode}': client_address['postcode'],
                        '{Bank}': lender_name,  # DEFENDANT NAME as bank
                        '{Account Name}': client_info['name'],  # CLIENT NAME as account name
                        '{Account Number}': account_details['account_number'],
                        '{Sort Code}': bank_details.get('sort_code', 'TBC'),
                        '{Agreement Number}': 'TBC',  
                        '{Agreement Start Date}': account_details['start_date'],  
                        '{Report Received Date}': current_date,
                        '{Report Outcome}': 'unaffordable',
                    }
                    
                    # Replace placeholders
                    claim_letter_generator.replace_placeholders(doc, replacements)
                    
                    # Save to BytesIO
                    doc_bytes = BytesIO()
                    doc.save(doc_bytes)
                    doc_bytes.seek(0)
                    
                    letter_files[filename] = doc_bytes.getvalue()
                    logger.info(f"  ✓ Letter: {filename}")
                    
                except Exception as e:
                    logger.error(f"  ✗ Letter failed: {filename} - {str(e)}")
        
        # ==========================================
        # STEP 4: CREATE COMBINED ZIP FILE
        # ==========================================
        logger.info("Step 4: Creating combined ZIP file...")
        memory_file = BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add PDFs to pdfs/ folder
            for filename, pdf_bytes in pdf_files.items():
                zf.writestr(f"pdfs/{filename}", pdf_bytes)
            
            # Add claim letters to claim_letters/ folder
            for filename, docx_bytes in letter_files.items():
                zf.writestr(f"claim_letters/{filename}", docx_bytes)
        
        memory_file.seek(0)
        
        # ==========================================
        # SUMMARY
        # ==========================================
        logger.info("="*60)
        logger.info(f"✓ Successfully generated:")
        logger.info(f"  - {len(pdf_files)} PDF report(s)")
        logger.info(f"  - {len(letter_files)} claim letter(s)")
        logger.info(f"  - Total: {len(pdf_files) + len(letter_files)} files")
        logger.info("="*60)
        
        # Return combined ZIP
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return StreamingResponse(
            memory_file,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=analysis_complete_{timestamp}.zip"
            }
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_pdf_and_letters: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


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