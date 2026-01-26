from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import asyncio
from typing import List, Dict, Any
import logging

from .models import AnalyzeRequest, AnalyzeResponse, SingleReportResult
from .utils.html_fetcher import fetch_multiple_html
from .analyzer.credit_analyzer import CreditReportAnalyzer
from .utils.template_renderer import HTMLTemplateRenderer
from .utils.pdf_generator import pdf_generator

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
                    
                    # Generate PDF
                    pdf_bytes = await pdf_generator.html_string_to_pdf(
                        html_result['html'],
                        client_name
                    )
                    
                    # Encode to base64 for JSON transmission
                    import base64
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