from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
from typing import List
import logging

from .models import AnalyzeRequest, AnalyzeResponse, SingleReportResult
from .utils.html_fetcher import fetch_multiple_html
from .analyzer.credit_analyzer import CreditReportAnalyzer

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


async def analyze_single_report(url: str, html_content: str) -> SingleReportResult:
    """
    Analyze a single credit report.
    
    Args:
        url: The source URL
        html_content: The HTML content to analyze
        
    Returns:
        SingleReportResult with analysis data or error
    """
    try:
        analyzer = CreditReportAnalyzer(html_content)
        result = analyzer.analyze()
        
        return SingleReportResult(
            url=url,
            status="success",
            data=result
        )
    except Exception as e:
        logger.error(f"Error analyzing {url}: {str(e)}", exc_info=True)
        return SingleReportResult(
            url=url,
            status="error",
            error=f"Analysis failed: {str(e)}"
        )


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


@app.post("/analyze", response_model=AnalyzeResponse)
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
    
    Returns analysis results for each URL with success/error status.
    """
    urls = request.urls
    logger.info(f"Received analysis request for {len(urls)} URL(s)")
    
    try:
        # Step 1: Fetch all HTML content concurrently
        logger.info("Fetching HTML content...")
        fetch_results = await fetch_multiple_html(urls)
        
        # Step 2: Process successful fetches
        analysis_tasks = []
        failed_fetches = []
        
        for fetch_result in fetch_results:
            if fetch_result['status'] == 'success':
                task = analyze_single_report(
                    fetch_result['url'],
                    fetch_result['html_content']
                )
                analysis_tasks.append(task)
            else:
                # Record failed fetch
                failed_fetches.append(SingleReportResult(
                    url=fetch_result['url'],
                    status='error',
                    error=fetch_result.get('error', 'Unknown fetch error')
                ))
        
        # Step 3: Analyze all successfully fetched reports concurrently
        logger.info(f"Analyzing {len(analysis_tasks)} report(s)...")
        analysis_results = []
        
        if analysis_tasks:
            analysis_results = await asyncio.gather(*analysis_tasks)
        
        # Step 4: Combine all results
        all_results = failed_fetches + list(analysis_results)
        
        # Step 5: Generate summary
        successful = sum(1 for r in all_results if r.status == 'success')
        failed = len(all_results) - successful
        
        logger.info(f"Analysis complete: {successful} successful, {failed} failed")
        
        return AnalyzeResponse(
            results=all_results,
            summary={
                'total': len(all_results),
                'successful': successful,
                'failed': failed
            }
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_reports: {str(e)}", exc_info=True)
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