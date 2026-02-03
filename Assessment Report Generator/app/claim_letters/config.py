# Configuration for Letter of Claim Generator
# This file contains only structural settings - no client data
# All client-specific data comes from the JSON input

import os
from pathlib import Path

# Path to template (adjust based on your app structure)
# Option 1: Relative to this config file
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE_DIR / 'templates' / 'Affordability_Letter_of_Claim_.docx'

# Option 2: Absolute path (uncomment and modify if needed)
# TEMPLATE_PATH = '/path/to/your/templates/Affordability_Letter_of_Claim_.docx'

# Convert to string for compatibility
TEMPLATE_PATH = str(TEMPLATE_PATH)

# Default output directory for generated letters
DEFAULT_OUTPUT_DIR = 'claim_letters'

# Known defendant/lender addresses
# Add more as you discover them, or they can be provided in the JSON
# If not found here or in JSON, will use "Address TBC"
DEFENDANT_ADDRESSES = {
    'INDIGO MICHAEL LTD': 'Indigo Michael Ltd\nPO Box 4849\nWorthing\nBN11 9NX',
    'CAPITAL ONE (EUROPE) PLC': 'Capital One (Europe) plc\nTrent House, Station Street\nNottingham\nNG2 3HX',
    'VANQUIS BANK': 'Vanquis Bank\nNo. 1 Godwin Street\nBradford\nBD1 2SU',
    'JAJA FINANCE LIMITED': 'Jaja Finance Limited\n2 Lochside Avenue\nEdinburgh Park\nEdinburgh\nEH12 9DJ',
    'ZABLE': 'Zable Limited\n6th Floor\n1 London Wall Place\nLondon\nEC2Y 5AU',
    'SKY UK LTD': 'Sky UK Limited\nGrant Way\nIsleworth\nMiddlesex\nTW7 5QD',
    'FIRST RESPONSE FINANCE LTD': 'First Response Finance Ltd\n504 Pavilion Drive\nNorthampton Business Park\nNorthampton\nNN4 7ZE',
    'MONEYBARN NO': 'Moneybarn No. 1 Limited\nMoneybarn House\nChineham Business Park\nCrockford Lane\nBasingstoke\nRG24 8AL',
    'ADVANTAGE FINANCE LTD': 'Advantage Finance Ltd\n504 Pavilion Drive\nNorthampton Business Park\nNorthampton\nNN4 7ZE',
    'EE FLEX PAY': 'EE Limited\nTrident Place\nMosquito Way\nHatfield\nHertfordshire\nAL10 9BW',
    'NEXT DIRECTORY': 'Next Retail Ltd\nDesford Road\nEnderly\nLeicester\nLE19 4AT',
    'ZILCH': 'Zilch Technology Limited\n109-111 Farringdon Road\nLondon\nEC1R 3BW',
    'MORSES CLUB LTD': 'Morses Club PLC\nCarlton Park\nSaxon Way East\nCorby\nNorthamptonshire\nNN18 9EW',
}

# Agreement type mapping (reference only - not currently used in letter generation)
AGREEMENT_TYPES = {
    'Credit Card': 'Credit Card Agreement',
    'Hire Purchase': 'Hire Purchase Agreement',
    'Unsecured Loan': 'Unsecured Loan Agreement',
    'Mail Order Account': 'Mail Order Agreement',
    'Budget Account': 'Budget Account Agreement',
    'Home Lending Agreement': 'Home Lending Agreement',
    'Fixed Term Agreement': 'Fixed Term Agreement',
}