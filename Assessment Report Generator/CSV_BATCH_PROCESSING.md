# CSV Batch Processing Feature

## Overview

The CSV Batch Processing feature allows you to upload a CSV file containing multiple credit report links, automatically analyze them, generate PDF reports, upload them to Google Drive, and track everything in Google Sheets.

## Features

- 📊 **CSV Upload**: Upload a CSV file with credit report links
- ⚡ **Batch Processing**: Analyze multiple reports simultaneously  
- 📄 **PDF Generation**: Automatically generate affordability assessment PDFs
- ☁️ **Google Drive Upload**: Upload all PDFs to Google Drive with shareable links
- 📈 **Google Sheets Tracking**: Track all reports in a Google Sheet with download links
- 🔄 **Real-time Progress**: See processing status in real-time

## Setup Instructions

### 1. Google Cloud Setup

#### Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing one)
3. Note your Project ID

#### Enable Required APIs

Enable these APIs in your project:
- Google Drive API
- Google Sheets API

To enable:
1. Go to "APIs & Services" > "Library"
2. Search for "Google Drive API" and click "Enable"
3. Search for "Google Sheets API" and click "Enable"

#### Create Service Account

1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Name it (e.g., "affordability-reports-service")
4. Click "Create and Continue"
5. Grant role: "Editor" (or more restrictive if preferred)
6. Click "Done"

#### Generate Credentials

1. Click on your newly created service account
2. Go to "Keys" tab
3. Click "Add Key" > "Create New Key"
4. Choose "JSON" format
5. Download the JSON file
6. Save it as `credentials/google-service-account.json` in your project

### 2. Google Drive Setup

#### Create Upload Folder (Optional)

1. Go to [Google Drive](https://drive.google.com/)
2. Create a new folder (e.g., "Affordability Reports")
3. Copy the folder ID from the URL:
   ```
   https://drive.google.com/drive/folders/FOLDER_ID_HERE
   ```
4. Right-click the folder > Share
5. Add your service account email (found in the JSON file: `client_email`)
6. Give it "Editor" permissions

### 3. Google Sheets Setup

#### Create Tracking Sheet

1. Go to [Google Sheets](https://sheets.google.com/)
2. Create a new spreadsheet (e.g., "Affordability Reports Tracker")
3. Copy the spreadsheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit
   ```
4. Share the spreadsheet with your service account email
5. Give it "Editor" permissions

The sheet will be automatically initialized with headers on first use.

### 4. Environment Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your values:
   ```env
   GOOGLE_CREDENTIALS_PATH=credentials/google-service-account.json
   GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
   GOOGLE_SHEETS_ID=your_spreadsheet_id_here
   ```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

Install Playwright browsers (required for PDF generation):
```bash
playwright install chromium
```

### 6. Run the Application

```bash
python -m app.run
```

Or with uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at:
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Usage

### CSV File Format

Your CSV file must contain a column named **"Credit File Link"** with URLs to credit reports.

Example CSV:
```csv
Client Name,Credit File Link,Case Number
John Doe,https://example.com/report1.html,CASE001
Jane Smith,https://example.com/report2.html,CASE002
```

### Using the Web Interface

1. Open http://localhost:8000 in your browser
2. Click the upload area or drag and drop your CSV file
3. (Optional) Change the Google Sheets tab name
4. Click "Process CSV File"
5. Wait for processing to complete
6. View results and check your Google Drive/Sheets

### Using the API

You can also use the API directly:

```bash
curl -X POST "http://localhost:8000/batch-process-csv?sheet_name=Tracker" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_file.csv"
```

## Google Sheets Output

The tracker sheet will contain these columns:

| Column | Description |
|--------|-------------|
| Timestamp | When the report was processed |
| Client Name | Name from the credit report |
| Credit Report URL | Original URL |
| Analysis Status | Success or Failed |
| Total Score | Affordability score |
| Risk Level | Risk assessment level |
| Flagged Indicators | Number of flagged indicators |
| PDF Report Link | Clickable link to download PDF |
| File ID | Google Drive file ID |
| Error Message | Error details (if any) |

## Troubleshooting

### "Google credentials not found" Error

Make sure:
1. The credentials file exists at the path specified in `.env`
2. The path is correct (relative to project root)
3. The JSON file is valid

### "GOOGLE_SHEETS_ID environment variable not set" Error

Make sure:
1. You created a `.env` file (not just `.env.example`)
2. The `GOOGLE_SHEETS_ID` variable is set
3. You restarted the application after adding the variable

### Permission Errors

Make sure:
1. The Google Drive folder is shared with your service account email
2. The Google Sheets spreadsheet is shared with your service account email
3. The service account has "Editor" permissions

### Upload Fails

Check:
1. Google Drive API is enabled in your project
2. Service account has proper permissions
3. Folder ID is correct (if specified)

### Sheet Update Fails

Check:
1. Google Sheets API is enabled in your project
2. Spreadsheet ID is correct
3. Service account has edit access to the spreadsheet

## API Endpoints

### POST /batch-process-csv

Process a CSV file with credit report links.

**Parameters:**
- `file`: CSV file (multipart/form-data)
- `sheet_name`: (optional) Name of the Google Sheets tab (default: "Tracker")

**Response:**
```json
{
  "total_processed": 10,
  "successful": 9,
  "failed": 1,
  "drive_uploads": 9,
  "sheet_updates": 10,
  "errors": [
    {
      "url": "https://example.com/bad-report.html",
      "client_name": "Unknown",
      "error": "Failed to fetch HTML"
    }
  ],
  "message": "Successfully processed 9/10 reports..."
}
```

## Architecture

```
CSV Upload
    ↓
Parse CSV & Extract URLs
    ↓
Fetch HTML Content (parallel)
    ↓
Analyze Reports (parallel)
    ↓
Generate PDFs (parallel)
    ↓
Upload to Google Drive (sequential)
    ↓
Update Google Sheets (sequential)
    ↓
Return Results
```

## Security Notes

- Never commit your `credentials/google-service-account.json` file
- Never commit your `.env` file
- Add both to `.gitignore`
- Consider using more restrictive Google Cloud IAM roles for production
- Implement authentication for the web interface in production

## Support

For issues or questions:
- Email: info@systemizesolutions.co.uk
- Phone: +44 7597 195 645
