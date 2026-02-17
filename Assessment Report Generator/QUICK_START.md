# Quick Start Guide - CSV Batch Processing

## What Was Added

A complete CSV batch processing system that:
- ✅ Accepts CSV file uploads via a modern web interface
- ✅ Extracts credit report URLs from "Credit File Link" column
- ✅ Analyzes all reports in parallel
- ✅ Generates PDF affordability reports
- ✅ Uploads PDFs to Google Drive automatically
- ✅ Tracks everything in Google Sheets with download links

## New Files Created

### Backend
- `app/utils/google_drive_uploader.py` - Google Drive upload functionality
- `app/utils/google_sheets_tracker.py` - Google Sheets tracking functionality
- `app/models.py` - Added `CSVBatchProcessResult` model
- `app/main.py` - Added `/batch-process-csv` endpoint

### Frontend
- `app/static/index.html` - Beautiful web interface for CSV upload

### Configuration
- `.env.example` - Environment variable template
- `credentials/README.md` - Instructions for credentials setup
- `sample_input.csv` - Example CSV format

### Documentation
- `CSV_BATCH_PROCESSING.md` - Complete setup and usage guide

### Dependencies Added
- `google-auth==2.25.2`
- `google-auth-oauthlib==1.2.0`
- `google-auth-httplib2==0.2.0`
- `google-api-python-client==2.111.0`
- `pandas==2.1.4`

## Quick Setup (5 Steps)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Google Cloud Setup
- Create a Google Cloud project
- Enable Google Drive API and Google Sheets API
- Create a Service Account
- Download JSON credentials to `credentials/google-service-account.json`

### 3. Google Drive & Sheets Setup
- Create a folder in Google Drive (optional)
- Create a spreadsheet in Google Sheets
- Share both with your service account email (found in credentials JSON)
- Copy the folder ID and spreadsheet ID

### 4. Configure Environment
```bash
cp .env.example .env
```

Edit `.env`:
```env
GOOGLE_CREDENTIALS_PATH=credentials/google-service-account.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
GOOGLE_SHEETS_ID=your_spreadsheet_id
```

### 5. Run the Application
```bash
python -m app.run
```

Visit: http://localhost:8000

## Using the System

1. **Open the Web Interface**: Navigate to http://localhost:8000
2. **Prepare Your CSV**: Must have a "Credit File Link" column with report URLs
3. **Upload**: Drag and drop or click to upload your CSV
4. **Process**: Click "Process CSV File" and wait
5. **Review**: Check results on screen
6. **Access Reports**: Open your Google Sheet to see all reports with download links

## CSV Format

Your CSV must contain a column named **"Credit File Link"**:

```csv
Client Name,Credit File Link,Case Number
John Doe,https://example.com/report1.html,CASE001
Jane Smith,https://example.com/report2.html,CASE002
```

See `sample_input.csv` for a complete example.

## Google Sheets Output

The tracker will automatically create a sheet with:
- Timestamp
- Client Name
- Credit Report URL
- Analysis Status
- Total Score
- Risk Level
- Flagged Indicators
- **PDF Report Link** (clickable download link)
- File ID
- Error Message (if any)

## Architecture Flow

```
Web Interface (index.html)
        ↓
    Upload CSV
        ↓
API Endpoint (/batch-process-csv)
        ↓
1. Parse CSV → Extract URLs
2. Fetch HTML (parallel)
3. Analyze Reports (parallel)
4. Generate PDFs (parallel)
5. Upload to Google Drive
6. Update Google Sheets
        ↓
Return Results to User
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/batch-process-csv` | POST | Process CSV file |
| `/api/health` | GET | Health check |
| `/analyze` | POST | Original analyze endpoint (still works) |
| `/analyze-pdf` | POST | Original PDF endpoint (still works) |

## What Happens During Processing

1. **CSV Upload**: File is uploaded and validated
2. **URL Extraction**: System finds "Credit File Link" column and extracts URLs
3. **HTML Fetching**: All reports fetched concurrently (fast!)
4. **Analysis**: Credit analysis runs on each report
5. **PDF Generation**: Affordability reports generated as PDFs
6. **Google Drive Upload**: Each PDF uploaded and made shareable
7. **Sheet Update**: Tracker updated with report data and download links
8. **Results Display**: Summary shown on screen

## Troubleshooting

### Can't Find Credentials
- Make sure `credentials/google-service-account.json` exists
- Check the path in your `.env` file
- Restart the application after adding credentials

### Permission Errors
- Share Google Drive folder with service account email
- Share Google Sheets with service account email
- Give "Editor" permissions

### CSV Errors
- Make sure column is named exactly "Credit File Link" (case-sensitive)
- Ensure URLs are valid and accessible
- Try with `sample_input.csv` first

## Security Notes

⚠️ **Never commit**:
- `.env` file
- `credentials/` directory
- Any JSON credential files

These are already in `.gitignore`.

## Support

For detailed setup instructions, see `CSV_BATCH_PROCESSING.md`

For issues:
- Email: info@systemizesolutions.co.uk
- Phone: +44 7597 195 645

## Next Steps

1. Follow the 5-step setup above
2. Test with `sample_input.csv`
3. Create your own CSV with real credit report links
4. Process and review results in Google Sheets
5. Download PDFs directly from the sheet links

Enjoy your automated affordability report generation! 🚀
