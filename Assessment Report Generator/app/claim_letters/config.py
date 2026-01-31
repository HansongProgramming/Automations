# Configuration for Letter of Claim Generator
# Update these values with your firm's actual details
import os
from pathlib import Path

BANK_DETAILS = {
    'bank_name': 'YOUR BANK NAME',
    'account_name': 'Ryans Solicitors Client Account',
    'account_number': '12345678',
    'sort_code': '12-34-56'
}

# Path to template (using absolute path based on this file's location)
# This gets the directory where config.py is located, goes up one level to 'app',
# then into 'templates' folder
BASE_DIR = Path(__file__).resolve().parent.parent  # This gets us to the 'app' directory
TEMPLATE_PATH = BASE_DIR / 'templates' / 'Affordability_Letter_of_Claim_.docx'

# Convert to string for compatibility
TEMPLATE_PATH = str(TEMPLATE_PATH)

# Default output directory
DEFAULT_OUTPUT_DIR = 'claim_letters'

# Defendant addresses (if you have a database of known lenders)
# This is optional - you can populate this with known addresses
DEFENDANT_ADDRESSES = {
    'INDIGO MICHAEL LTD': 'Address line 1\nAddress line 2\nPostcode',
    'CAPITAL ONE (EUROPE) PLC': 'Trent House, Station Street\nNottingham\nNG2 3HX',
    'VANQUIS BANK': 'No. 1 Godwin Street\nBradford\nBD1 2SU',
    'JAJA FINANCE LIMITED': 'Address TBC',
    'ZABLE': 'Address TBC',
    # Add more as needed
}

# Agreement details mapping (if you want to map account types to agreement templates)
AGREEMENT_TYPES = {
    'Credit Card': 'Credit Card Agreement',
    'Hire Purchase': 'Hire Purchase Agreement',
    'Unsecured Loan': 'Unsecured Loan Agreement',
    'Mail Order Account': 'Mail Order Agreement',
    'Budget Account': 'Budget Account Agreement',
    'Home Lending Agreement': 'Home Lending Agreement',
}