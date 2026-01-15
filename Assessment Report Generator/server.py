from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

# Import your existing modules
from app import analyze_credit_report
from chatbot import analyse_credit_report

app = FastAPI(
    title="Credit Report Analyzer API",
    description="Analyzes credit reports and returns risk indicators with AI analysis",
    version="1.0.0"
)

# Add CORS middleware for n8n compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreditReportRequest(BaseModel):
    """Request model for credit report analysis"""
    url: Optional[str] = None
    html: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://api.boshhhfintech.com/File/CreditReport/95d1ce7e-2c3c-49d5-a303-6a4727f91005?Auth=..."
            }
        }


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Credit Report Analyzer API",
        "version": "1.0.0"
    }


@app.post("/analyze")
async def analyze_endpoint(request: CreditReportRequest):
    """
    Analyze a credit report and generate AI analysis.
    Returns complete analysis in a single JSON response.
    
    - **url**: URL to fetch the credit report HTML from
    - **html**: Raw HTML string of the credit report
    
    Note: Provide either url OR html, not both.
    """
    try:
        # Validate that either url or html is provided
        if not request.url and not request.html:
            raise HTTPException(
                status_code=400,
                detail="Either 'url' or 'html' must be provided"
            )
        
        if request.url and request.html:
            raise HTTPException(
                status_code=400,
                detail="Provide either 'url' or 'html', not both"
            )
        
        # Step 1: Analyze credit report
        url_or_html = request.url if request.url else request.html
        credit_analysis = analyze_credit_report(url_or_html)
        
        # Step 2: Send to chatbot for AI analysis
        ai_analysis = analyse_credit_report(credit_analysis)
        
        # Return combined in single JSON
        return {
            "credit_analysis": credit_analysis,
            "ai_analysis": ai_analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy"}


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )