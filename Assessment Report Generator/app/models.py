from pydantic import BaseModel, HttpUrl, validator
from typing import List, Dict, Any, Optional

class AnalyzeRequest(BaseModel):
    """Request model for credit report analysis"""
    urls: List[str]
    
    @validator('urls')
    def validate_urls(cls, v):
        if not v:
            raise ValueError('At least one URL is required')
        if len(v) > 20:
            raise ValueError('Maximum 20 URLs allowed per request')
        return v


class IndicatorResult(BaseModel):
    """Individual indicator result"""
    flagged: bool
    points: int


class ClientInfo(BaseModel):
    """Client information from credit report"""
    name: Optional[str]
    address: Optional[str]


class AccountSummary(BaseModel):
    """Summary of a credit account"""
    name: str
    type: str
    title: str
    body: str


class CreditTimeline(BaseModel):
    """Timeline of credit events"""
    ccjs: List[Dict[str, Any]]
    defaults: List[Dict[str, Any]]
    arrears_pattern: List[Dict[str, Any]]


class ClaimsAnalysis(BaseModel):
    """Claims analysis results"""
    in_scope: List[AccountSummary]
    out_of_scope: List[AccountSummary]
    credit_timeline: CreditTimeline


class AnalysisResult(BaseModel):
    """Complete analysis result for a single credit report"""
    client_info: ClientInfo
    indicators: Dict[str, IndicatorResult]
    total_points: int
    traffic_light: str


class SingleReportResult(BaseModel):
    """Result for a single URL - matches original output format"""
    credit_analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    url: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Response model - returns array of credit analysis results"""
    
    class Config:
        # Allow this to be a plain list
        schema_extra = {
            "example": [
                {
                    "credit_analysis": {
                        "client_info": {},
                        "indicators": {},
                        "total_points": 95,
                        "traffic_light": "GREEN",
                        "claims_analysis": {}
                    }
                }
            ]
        }


class ClientDriveLinks(BaseModel):
    """Per-client Drive folder and file links returned to the UI."""
    client_name:         str
    client_folder_link:  str = ''   # top-level client folder
    pdf_link:            str = ''   # direct link to PDF file
    html_link:           str = ''   # direct link to HTML file
    loc_link:            str = ''   # link to LOC subfolder
    error:               Optional[str] = None


# ── UPDATE CSVBatchProcessResult — add client_drive_links ───
class CSVBatchProcessResult(BaseModel):
    total_processed: int
    successful:      int
    failed:          int
    drive_uploads:   int
    sheet_updates:   int
    errors:          List[Dict[str, Any]] = []
    message:         str
    sheets_url:      Optional[str] = None
    client_drive_links: List[ClientDriveLinks] = []   # ← NEW FIELD