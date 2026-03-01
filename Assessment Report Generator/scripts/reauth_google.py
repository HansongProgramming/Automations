"""
Run this script on your LOCAL machine (Windows/Mac) to generate a fresh OAuth token.

Usage:
    python scripts/reauth_google.py

It will open a browser for you to log in with Google, then save
credentials/oauth-token.pkl. Upload that file to the VPS:

    scp credentials/oauth-token.pkl root@<your-vps-ip>:/var/www/credit-report-analyzer/Automations/Assessment\ Report\ Generator/credentials/oauth-token.pkl

Then restart the container:
    docker restart credit-report-analyzer
"""

import os
import pickle
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]

CREDENTIALS_DIR = Path(__file__).parent.parent / 'credentials'
CLIENT_SECRETS   = CREDENTIALS_DIR / 'oauth-client.json'
TOKEN_PATH       = CREDENTIALS_DIR / 'oauth-token.pkl'


def main():
    if not CLIENT_SECRETS.exists():
        print(f"ERROR: oauth-client.json not found at {CLIENT_SECRETS}")
        print("Download it from Google Cloud Console → APIs & Services → Credentials.")
        return

    print("Opening browser for Google authentication...")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, 'wb') as f:
        pickle.dump(creds, f)

    print(f"\nToken saved to: {TOKEN_PATH}")
    print("\nNow upload it to the VPS with:")
    print(f"  scp {TOKEN_PATH} root@<vps-ip>:/var/www/credit-report-analyzer/Automations/Assessment\\ Report\\ Generator/credentials/oauth-token.pkl")
    print("\nThen restart the container:")
    print("  docker restart credit-report-analyzer")


if __name__ == '__main__':
    main()
