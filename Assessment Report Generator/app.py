import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from typing import Dict, List, Any

class CreditReportAnalyzer:
    """
    Analyzes credit report HTML to extract key risk indicators and generate a credit score.
    """
    
    def __init__(self, html_content: str, verbose: bool = True):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.current_date = datetime.now()
        self.verbose = verbose
        
        # Payment code definitions
        self.negative_codes = ['1', '2', '3', '4', '5', '6', 'A', 'B', 'D', 'R', 'W', 'V']
        self.arrears_codes = ['1', '2', '3', '4', '5', '6', 'A', 'B']
        self.severe_codes = ['D', 'R', 'W', 'V']
        
    def log(self, message: str):
        """Print message if verbose mode is enabled"""
        if self.verbose:
            print(f"[ANALYZER] {message}")
        
    def fetch_from_url(url: str) -> str:
        """Fetch HTML content from URL"""
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    
    def parse_ccj_data(self) -> List[Dict[str, Any]]:
        """Extract County Court Judgement (CCJ) data"""
        self.log("\n" + "="*60)
        self.log("PARSING CCJ DATA")
        self.log("="*60)
        
        ccjs = []
        
        # Find all CCJ sections
        content = self.soup.get_text()
        ccj_pattern = r'County Court Judgement \(CCJ\)\s*([0-9\-]+)?\s*Court Name\s+([A-Z\s]+)\s*Case Number\s+([A-Z0-9]+)\s*Case Type\s+([A-Z]+)\s*Amount\s+(\d+)\s+GBP'
        
        matches = re.finditer(ccj_pattern, content)
        for idx, match in enumerate(matches, 1):
            date_str = match.group(1)
            ccj = {
                'court_name': match.group(2).strip(),
                'case_number': match.group(3).strip(),
                'case_type': match.group(4).strip(),
                'amount': int(match.group(5)),
                'date': date_str if date_str else None
            }
            ccjs.append(ccj)
            self.log(f"CCJ #{idx}: Court={ccj['court_name']}, Case={ccj['case_number']}, Amount=£{ccj['amount']:,}, Date={ccj['date']}")
        
        self.log(f"Total CCJs found: {len(ccjs)}")
        return ccjs
    
    def parse_credit_accounts(self) -> List[Dict[str, Any]]:
        """Extract all credit account information"""
        self.log("\n" + "="*60)
        self.log("PARSING CREDIT ACCOUNTS")
        self.log("="*60)
        
        accounts = []
        
        # Find all account tables
        tables = self.soup.find_all('table')
        self.log(f"Found {len(tables)} tables to process")
        
        for table_idx, table in enumerate(tables):
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            account_data = {}
            payment_history = []
            
            # Parse account details
            for row in rows:
                cells = row.find_all('td')
                if len(cells) == 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    account_data[key] = value
            
            # Parse payment history
            payment_headers = []
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if len(cells) > 12:  # Payment history row
                    year_cell = cells[0].get_text(strip=True)
                    if year_cell.isdigit():
                        year = int(year_cell)
                        for i, cell in enumerate(cells[1:13]):
                            code = cell.get_text(strip=True)
                            if code:
                                payment_history.append({
                                    'year': year,
                                    'month': i + 1,
                                    'code': code
                                })
            
            if account_data:
                account_data['payment_history'] = payment_history
                accounts.append(account_data)
                
                # Log account summary
                account_num = account_data.get('Account Number', 'Unknown')
                loan_value = account_data.get('Loan Value', '£0')
                credit_limit = account_data.get('Credit Limit', 'N/A')
                default_date = account_data.get('Default Date', 'N/A')
                
                self.log(f"\nAccount: {account_num}")
                self.log(f"  Loan Value: {loan_value}, Credit Limit: {credit_limit}")
                self.log(f"  Default Date: {default_date}")
                self.log(f"  Payment History Entries: {len(payment_history)}")
        
        self.log(f"\nTotal accounts parsed: {len(accounts)}")
        return accounts
    
    def check_active_ccj(self, ccjs: List[Dict]) -> bool:
        """Check if there are active CCJs (within 6 years)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Active CCJ")
        self.log("-"*60)
        
        six_years_ago = self.current_date - timedelta(days=6*365)
        self.log(f"Current Date: {self.current_date.strftime('%Y-%m-%d')}")
        self.log(f"6 Years Ago: {six_years_ago.strftime('%Y-%m-%d')}")
        
        active_ccjs = []
        
        for ccj in ccjs:
            if ccj.get('date'):
                try:
                    ccj_date = datetime.strptime(ccj['date'], '%Y-%m-%d')
                    is_active = ccj_date >= six_years_ago
                    self.log(f"CCJ {ccj['case_number']}: Date={ccj['date']}, Active={is_active}")
                    if is_active:
                        active_ccjs.append(ccj)
                except:
                    self.log(f"CCJ {ccj['case_number']}: Date parsing failed, assuming active")
                    active_ccjs.append(ccj)
            else:
                self.log(f"CCJ {ccj['case_number']}: No date, assuming active")
                active_ccjs.append(ccj)
        
        result = len(active_ccjs) > 0 or len(ccjs) > 0
        self.log(f"RESULT: {'✓ FLAGGED' if result else '✗ PASS'} - Active CCJs: {len(active_ccjs)}/{len(ccjs)}")
        return result
    
    def check_multiple_ccjs(self, ccjs: List[Dict]) -> bool:
        """Check if there are multiple CCJs"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Multiple CCJs")
        self.log("-"*60)
        self.log(f"Total CCJs: {len(ccjs)}")
        self.log(f"Threshold: >= 2")
        result = len(ccjs) >= 2
        self.log(f"RESULT: {'✓ FLAGGED' if result else '✗ PASS'}")
        return result
    
    def check_active_default(self, accounts: List[Dict]) -> bool:
        """Check for active defaults (D code in payment history)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Active Default")
        self.log("-"*60)
        
        defaults_found = []
        
        for account in accounts:
            account_num = account.get('Account Number', 'Unknown')
            default_date = account.get('Default Date', 'N/A')
            
            if default_date != 'N/A':
                self.log(f"Account {account_num}: Default Date = {default_date}")
                defaults_found.append(account_num)
            
            # Also check payment history for 'D' code
            for payment in account.get('payment_history', []):
                if payment['code'] == 'D':
                    self.log(f"Account {account_num}: 'D' code found in {payment['year']}-{payment['month']:02d}")
                    if account_num not in defaults_found:
                        defaults_found.append(account_num)
        
        result = len(defaults_found) > 0
        self.log(f"RESULT: {'✓ FLAGGED' if result else '✗ PASS'} - Accounts with defaults: {len(defaults_found)}")
        return result
    
    def check_debt_collection(self, accounts: List[Dict]) -> bool:
        """
        Check if accounts are with debt collection agencies.
        Criteria: Account has been passed to debt collection agency (Lowell, Cabot, PRA).
        Indicates serious payment failure and debt enforcement action.
        
        Detection methods:
        1. Transfer marker ('X' code in payment history)
        2. Explicit debt collection keywords in lender name
        3. Default with non-originator lender (likely sold to debt collector)
        """
        self.log("\n" + "-"*60)
        self.log("CHECKING: Debt Collection")
        self.log("-"*60)
        self.log("Criteria: Serious payment failure and debt enforcement action")
        
        # Keywords that indicate debt collection agencies
        DEBT_KEYWORDS = [
            "PORTFOLIO",
            "RECOVER",
            "RECOVERY",
            "COLLECTION",
            "CREDIT MANAGEMENT",
            "DEBT",
            "HOLDINGS",
            "LOWELL",
            "CABOT",
            "PRA",
            "LANTERN",
            "PERCH",
            "WESCOT",
            "INTRUM",
            "RESOLVE",
            "FAIRFAX",
        ]
        
        # Known original lenders (not debt collectors)
        KNOWN_ORIGINATORS = [
            "BARCLAY",
            "CAPITAL ONE",
            "VANQUIS",
            "NEWDAY",
            "AQUA",
            "JAJA",
            "ZABLE",
            "HSBC",
            "LLOYDS",
            "NATWEST",
            "MONZO",
            "SANTANDER",
            "TSB",
            "FIRST DIRECT",
            "NATIONWIDE",
            "HALIFAX",
            "TESCO",
            "SAINSBURY",
            "AMEX",
            "MBNA",
        ]
        
        collection_accounts = []
        
        for account in accounts:
            account_num = account.get('Account Number', 'Unknown')
            account_str = str(account).upper()
            default_date = account.get('Default Date', 'N/A')
            
            # Extract lender name
            lender = "Unknown"
            lender_match = re.search(r'from ([A-Z\s&\(\)\.]+?)(?:\(I\)|$)', account_str)
            if lender_match:
                lender = lender_match.group(1).strip()
            
            # Method 1: Check for Transfer marker ('X' code)
            payment_history = account.get('payment_history', [])
            has_transfer = False
            for payment in payment_history:
                if payment['code'] == 'X':
                    has_transfer = True
                    self.log(f"Account {account_num}: Transfer marker 'X' found in {payment['year']}-{payment['month']:02d}")
                    break
            
            if has_transfer:
                collection_accounts.append({
                    'account': account_num,
                    'reason': 'Transfer marker (X)',
                    'lender': lender
                })
                continue
            
            # Method 2: Check for explicit debt collection keywords
            matched_keyword = None
            for keyword in DEBT_KEYWORDS:
                if keyword in lender:
                    matched_keyword = keyword
                    break
            
            if matched_keyword:
                self.log(f"Account {account_num}: Lender '{lender}' matches keyword '{matched_keyword}'")
                collection_accounts.append({
                    'account': account_num,
                    'reason': f"Debt collection keyword: {matched_keyword}",
                    'lender': lender
                })
                continue
            
            # Method 3: Default + Non-originator lender
            if default_date and default_date != 'N/A':
                is_originator = any(orig in lender for orig in KNOWN_ORIGINATORS)
                if not is_originator:
                    self.log(f"Account {account_num}: Default with non-originator lender '{lender}'")
                    collection_accounts.append({
                        'account': account_num,
                        'reason': 'Default with non-originator (likely sold to debt collector)',
                        'lender': lender
                    })
        
        result = len(collection_accounts) > 0
        self.log(f"RESULT: {'✓ FLAGGED' if result else '✗ PASS'} - Debt collection accounts: {len(collection_accounts)}")
        
        if result:
            for item in collection_accounts:
                self.log(f"  → {item['account']}: {item['reason']}")
        
        return result
    
    def check_ap_marker(self, accounts: List[Dict]) -> bool:
        """Check for arrangement to pay markers (I code)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Arrangement to Pay (AP) Marker")
        self.log("-"*60)
        
        ap_accounts = []
        
        for account in accounts:
            account_num = account.get('Account Number', 'Unknown')
            for payment in account.get('payment_history', []):
                if payment['code'] == 'I':
                    self.log(f"Account {account_num}: 'I' code found in {payment['year']}-{payment['month']:02d}")
                    if account_num not in ap_accounts:
                        ap_accounts.append(account_num)
        
        result = len(ap_accounts) > 0
        self.log(f"RESULT: {'✓ FLAGGED' if result else '✗ PASS'} - Accounts with AP marker: {len(ap_accounts)}")
        return result
    
    def check_arrears(self, accounts: List[Dict]) -> bool:
        """Check for recent arrears (1-6, A, B codes in last 12 months)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Arrears (Last 12 Months)")
        self.log("-"*60)
        
        one_year_ago = self.current_date - timedelta(days=365)
        self.log(f"Current Date: {self.current_date.strftime('%Y-%m-%d')}")
        self.log(f"12 Months Ago: {one_year_ago.strftime('%Y-%m-%d')}")
        self.log(f"Arrears Codes: {', '.join(self.arrears_codes)}")
        
        arrears_found = []
        
        for account in accounts:
            account_num = account.get('Account Number', 'Unknown')
            for payment in account.get('payment_history', []):
                payment_date = datetime(payment['year'], payment['month'], 1)
                if payment_date >= one_year_ago:
                    if payment['code'] in self.arrears_codes:
                        self.log(f"Account {account_num}: Code '{payment['code']}' found in {payment['year']}-{payment['month']:02d}")
                        arrears_found.append({
                            'account': account_num,
                            'date': payment_date.strftime('%Y-%m'),
                            'code': payment['code']
                        })
        
        result = len(arrears_found) > 0
        self.log(f"RESULT: {'✓ FLAGGED' if result else '✗ PASS'} - Arrears entries: {len(arrears_found)}")
        return result
    
    def check_utilisation(self, accounts: List[Dict]) -> bool:
        """
        Check for high credit utilization (>80%).
        Indicates over-reliance on credit and limited financial buffer.
        
        Calculates overall utilization across all accounts with credit limits.
        """
        self.log("\n" + "-"*60)
        self.log("CHECKING: Credit Utilization (>80%)")
        self.log("-"*60)
        self.log("Threshold: 80% (indicates over-reliance on credit)")
        
        total_used = 0
        total_limit = 0
        individual_high_util = False
        high_util_accounts = []
        
        for account in accounts:
            try:
                loan_value_str = account.get('Loan Value', '£0')
                credit_limit_str = account.get('Credit Limit', '£N/A')
                account_num = account.get('Account Number', 'Unknown')
                
                if credit_limit_str != '£N/A':
                    loan_value = int(re.sub(r'[^\d]', '', loan_value_str))
                    credit_limit = int(re.sub(r'[^\d]', '', credit_limit_str))
                    
                    if credit_limit > 0:
                        # Track totals for overall utilization
                        total_used += loan_value
                        total_limit += credit_limit
                        
                        # Check individual account utilization
                        individual_utilization = loan_value / credit_limit
                        utilization_pct = individual_utilization * 100
                        
                        self.log(f"Account {account_num}: £{loan_value:,} / £{credit_limit:,} = {utilization_pct:.1f}%")
                        
                        if individual_utilization > 0.80:
                            individual_high_util = True
                            high_util_accounts.append(account_num)
            except Exception as e:
                self.log(f"Error processing account: {e}")
                continue
        
        # Check overall utilization across all accounts
        overall_high_util = False
        if total_limit > 0:
            overall_utilization = total_used / total_limit
            overall_pct = overall_utilization * 100
            self.log(f"\nOVERALL: £{total_used:,} / £{total_limit:,} = {overall_pct:.1f}%")
            if overall_utilization > 0.80:
                overall_high_util = True
        
        # Flag as true if either individual account or overall utilization exceeds 80%
        result = individual_high_util or overall_high_util
        self.log(f"RESULT: {'✓ FLAGGED' if result else '✗ PASS'}")
        if individual_high_util:
            self.log(f"  - Individual accounts >80%: {len(high_util_accounts)}")
        if overall_high_util:
            self.log(f"  - Overall utilization >80%")
        
        return result
    
    def check_rapid_borrowing(self, accounts: List[Dict]) -> bool:
        """Check for rapid borrowing (multiple accounts opened in last 6 months)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Rapid Borrowing")
        self.log("-"*60)
        
        six_months_ago = self.current_date - timedelta(days=180)
        self.log(f"Current Date: {self.current_date.strftime('%Y-%m-%d')}")
        self.log(f"6 Months Ago: {six_months_ago.strftime('%Y-%m-%d')}")
        self.log(f"Threshold: >= 3 new accounts")
        
        recent_accounts = []
        
        for account in accounts:
            start_date_str = account.get('Agreement Start Date', '')
            account_num = account.get('Account Number', 'Unknown')
            
            if start_date_str:
                try:
                    # Parse date in format DD/MM/YYYY
                    start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
                    if start_date >= six_months_ago:
                        self.log(f"Account {account_num}: Opened on {start_date.strftime('%Y-%m-%d')}")
                        recent_accounts.append(account_num)
                except Exception as e:
                    self.log(f"Account {account_num}: Date parsing error - {e}")
                    continue
        
        result = len(recent_accounts) >= 3
        self.log(f"RESULT: {'✓ FLAGGED' if result else '✗ PASS'} - New accounts in last 6 months: {len(recent_accounts)}")
        return result
    
    def check_repeat_lending(self, accounts: List[Dict]) -> bool:
        """Check for repeat lending with same providers"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Repeat Lending")
        self.log("-"*60)
        self.log("Looking for multiple accounts with same provider...")
        
        providers = {}
        
        for account in accounts:
            account_info = str(account)
            account_num = account.get('Account Number', 'Unknown')
            
            # Extract provider name from account info
            match = re.search(r'from ([A-Z\s&\(\)]+)', account_info)
            if match:
                provider = match.group(1).strip()
                if provider not in providers:
                    providers[provider] = []
                providers[provider].append(account_num)
        
        repeat_providers = []
        for provider, account_list in providers.items():
            count = len(account_list)
            self.log(f"Provider '{provider}': {count} account(s)")
            if count >= 2:
                repeat_providers.append(provider)
        
        result = len(repeat_providers) > 0
        self.log(f"RESULT: {'✓ FLAGGED' if result else '✗ PASS'} - Providers with multiple accounts: {len(repeat_providers)}")
        return result
    
    def calculate_score(self, flags: Dict[str, bool]) -> int:
        """
        Calculate credit score based on flags.
        Score range: 0-300 (lower is worse)
        """
        self.log("\n" + "="*60)
        self.log("CALCULATING CREDIT SCORE")
        self.log("="*60)
        
        base_score = 300
        self.log(f"Base Score: {base_score}")
        
        penalties = {
            'active_ccj': -30,
            'multiple_ccjs': -40,
            'active_default': -50,
            'debt_collection': -25,
            'ap_marker': -15,
            'arrears': -30,
            'utilisation': -20,
            'rapid_borrowing': -25,
            'repeat_lending': -10
        }
        
        total_penalty = 0
        for flag, active in flags.items():
            if active:
                penalty = penalties.get(flag, 0)
                total_penalty += penalty
                self.log(f"  - {flag}: {penalty} points")
        
        final_score = max(0, min(300, base_score + total_penalty))
        self.log(f"\nTotal Penalty: {total_penalty}")
        self.log(f"Final Score: {final_score}/300")
        
        return final_score
    
    def determine_traffic_light(self, score: int) -> str:
        """
        Determine traffic light status based on score.
        GREEN: 250-300
        AMBER: 150-249
        RED: 0-149
        """
        self.log("\n" + "="*60)
        self.log("DETERMINING TRAFFIC LIGHT STATUS")
        self.log("="*60)
        self.log(f"Score: {score}")
        self.log("Thresholds: GREEN (250-300) | AMBER (150-249) | RED (0-149)")
        
        if score >= 70:
            result = 'GREEN'
        elif score >= 40 and score < 70:
            result = 'AMBER'
        else:
            result = 'RED'
        
        self.log(f"Traffic Light: {result}")
        return result
    
    def extract_report_data(self) -> Dict[str, Any]:
        """
        Extract comprehensive report data including personal info, financial metrics, and risk indicators.
        Returns a dictionary with all required fields.
        """
        self.log("\n" + "="*60)
        self.log("EXTRACTING REPORT DATA")
        self.log("="*60)
        
        content = self.soup.get_text()
        
        # Initialize data dictionary
        data = {
            'Date': None,
            'Defendant Name': None,
            'Defendant Address': None,
            'Client First Name': None,
            'Client Surname': None,
            'Address Line 1': None,
            'Address Line 2': None,
            'Address Line 3': None,
            'Postcode': None,
            'Agreement Number': None,
            'Agreement Start Date': None,
            'Report Received Date': None,
            'Report Outcome': None,
            'averageConsistentIncome': 0.0,
            'averageCommittedExpenditure': 0.0,
            'averageLivingExpenditure': 0.0,
            'totalAverageExpenditure': 0.0,
            'disposableincome': 0.0,
            'totalContribution': 0.0,
            'averageTotalContribution': 0.0,
            'totalPeerToPeer': 0,
            'totalDefaults12Months': 0,
            'totalArrears12Months': 0,
            'numberofTotalTransactions': 0,
            'averageTotalGambling': 0.0,
            'averageOverdraftUsageInDays': 0.0
        }
        
        # Extract date from header (e.g., "Date issued: May 14, 2025")
        date_match = re.search(r'Date issued:\s+([A-Za-z]+\s+\d+,\s+\d{4})', content)
        if date_match:
            data['Date'] = date_match.group(1)
            self.log(f"Date: {data['Date']}")
        
        # Extract client name from header (first line is usually the name)
        name_match = re.search(r'^([A-Z\s]+)\s+Credit File', content, re.MULTILINE)
        if name_match:
            full_name = name_match.group(1).strip()
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                data['Client First Name'] = name_parts[0]
                data['Client Surname'] = ' '.join(name_parts[1:])
                data['Defendant Name'] = full_name
                self.log(f"Client Name: {data['Client First Name']} {data['Client Surname']}")
        
        # Extract supplied address (first supplied address)
        supplied_addr_pattern = r'Supplied Address 1\s+(\d+)\s+([A-Z\s]+)\s+([A-Z0-9\s]+)\s+([A-Z\s]+)'
        supplied_match = re.search(supplied_addr_pattern, content)
        if supplied_match:
            data['Address Line 1'] = supplied_match.group(1)  # House number
            data['Address Line 2'] = supplied_match.group(2).strip()  # Street name
            data['Postcode'] = supplied_match.group(3).strip()  # Postcode
            data['Address Line 3'] = supplied_match.group(4).strip()  # City
            data['Defendant Address'] = f"{data['Address Line 1']} {data['Address Line 2']}, {data['Address Line 3']}, {data['Postcode']}"
            self.log(f"Address: {data['Defendant Address']}")
        
        # Parse accounts for financial data
        accounts = self.parse_credit_accounts()
        
        # Get the most recent/primary account for agreement details
        if accounts:
            primary_account = accounts[0]
            data['Agreement Number'] = primary_account.get('Account Number', None)
            data['Agreement Start Date'] = primary_account.get('Agreement Start Date', None)
            self.log(f"Agreement Number: {data['Agreement Number']}")
            self.log(f"Agreement Start Date: {data['Agreement Start Date']}")
        
        # Report received date (use current date or extraction date)
        data['Report Received Date'] = self.current_date.strftime('%Y-%m-%d')
        
        # Calculate financial metrics
        data = self._calculate_financial_metrics(data, accounts)
        
        # Calculate risk metrics
        data = self._calculate_risk_metrics(data, accounts)
        
        # Determine report outcome based on flags
        flags = {
            'active_ccj': self.check_active_ccj(self.parse_ccj_data()),
            'multiple_ccjs': self.check_multiple_ccjs(self.parse_ccj_data()),
            'active_default': self.check_active_default(accounts),
            'debt_collection': self.check_debt_collection(accounts),
        }
        
        # Determine outcome
        if flags['active_default'] or flags['debt_collection']:
            data['Report Outcome'] = 'DECLINED'
        elif flags['active_ccj'] or flags['multiple_ccjs']:
            data['Report Outcome'] = 'REVIEW'
        else:
            data['Report Outcome'] = 'APPROVED'
        
        self.log(f"Report Outcome: {data['Report Outcome']}")
        
        return data
    
    def _calculate_financial_metrics(self, data: Dict, accounts: List[Dict]) -> Dict:
        """Calculate financial metrics from account data"""
        self.log("\nCalculating financial metrics...")
        
        total_loan_values = 0
        total_credit_limits = 0
        monthly_payments = []
        
        for account in accounts:
            # Sum up loan values
            loan_value_str = account.get('Loan Value', '£0')
            try:
                loan_value = int(re.sub(r'[^\d]', '', loan_value_str))
                total_loan_values += loan_value
            except:
                pass
            
            # Sum up credit limits
            credit_limit_str = account.get('Credit Limit', '£N/A')
            if credit_limit_str != '£N/A':
                try:
                    credit_limit = int(re.sub(r'[^\d]', '', credit_limit_str))
                    total_credit_limits += credit_limit
                except:
                    pass
            
            # Estimate monthly payment (loan value / forecasted months)
            try:
                start_date_str = account.get('Agreement Start Date', '')
                end_date_str = account.get('Forecasted End Date', '')
                if start_date_str and end_date_str:
                    start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
                    end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
                    months = max(1, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month))
                    if loan_value > 0:
                        monthly_payment = loan_value / months
                        monthly_payments.append(monthly_payment)
            except:
                pass
        
        # Estimate income (assume 3x debt burden as conservative estimate)
        estimated_monthly_payment = sum(monthly_payments) if monthly_payments else 0
        data['averageConsistentIncome'] = round(estimated_monthly_payment * 3, 2) if estimated_monthly_payment > 0 else 0
        
        # Committed expenditure (monthly debt payments)
        data['averageCommittedExpenditure'] = round(estimated_monthly_payment, 2)
        
        # Living expenditure (estimated at 60% of income)
        data['averageLivingExpenditure'] = round(data['averageConsistentIncome'] * 0.6, 2)
        
        # Total expenditure
        data['totalAverageExpenditure'] = round(
            data['averageCommittedExpenditure'] + data['averageLivingExpenditure'], 2
        )
        
        # Disposable income
        data['disposableincome'] = round(
            data['averageConsistentIncome'] - data['totalAverageExpenditure'], 2
        )
        
        # Total and average contribution
        data['totalContribution'] = data['disposableincome']
        data['averageTotalContribution'] = data['disposableincome']
        
        self.log(f"Average Income: £{data['averageConsistentIncome']:,.2f}")
        self.log(f"Committed Expenditure: £{data['averageCommittedExpenditure']:,.2f}")
        self.log(f"Disposable Income: £{data['disposableincome']:,.2f}")
        
        return data
    
    def _calculate_risk_metrics(self, data: Dict, accounts: List[Dict]) -> Dict:
        """Calculate risk metrics from account data"""
        self.log("\nCalculating risk metrics...")
        
        defaults_12m = 0
        arrears_12m = 0
        total_transactions = 0
        peer_to_peer_count = 0
        gambling_accounts = 0
        overdraft_days = []
        
        one_year_ago = self.current_date - timedelta(days=365)
        
        # Peer-to-peer lenders
        P2P_LENDERS = [
            'ZOPA', 'FUNDING CIRCLE', 'RATESETTER', 'LENDING WORKS',
            'ASSETZ', 'FOLK2FOLK', 'REBUILDINGSOCIETY'
        ]
        
        for account in accounts:
            account_str = str(account).upper()
            
            # Check for P2P lending
            for p2p in P2P_LENDERS:
                if p2p in account_str:
                    peer_to_peer_count += 1
                    break
            
            # Check for gambling-related accounts
            if any(word in account_str for word in ['BET', 'CASINO', 'GAMBLING', 'POKER', 'SLOTS']):
                gambling_accounts += 1
            
            # Count payment history transactions
            payment_history = account.get('payment_history', [])
            total_transactions += len(payment_history)
            
            # Check defaults and arrears in last 12 months
            for payment in payment_history:
                payment_date = datetime(payment['year'], payment['month'], 1)
                if payment_date >= one_year_ago:
                    if payment['code'] == 'D':
                        defaults_12m += 1
                    if payment['code'] in self.arrears_codes:
                        arrears_12m += 1
            
            # Estimate overdraft usage for current accounts
            if 'CURRENT ACCOUNT' in account_str:
                # Count months with negative balance indicators
                overdraft_months = sum(1 for p in payment_history if p['code'] in ['1', '2', '3', '4', '5', '6'])
                if overdraft_months > 0:
                    overdraft_days.append(overdraft_months * 30)  # Rough estimate
        
        data['totalPeerToPeer'] = peer_to_peer_count
        data['totalDefaults12Months'] = defaults_12m
        data['totalArrears12Months'] = arrears_12m
        data['numberofTotalTransactions'] = total_transactions
        data['averageTotalGambling'] = round(gambling_accounts * 100.0, 2)  # Estimated spending
        data['averageOverdraftUsageInDays'] = round(
            sum(overdraft_days) / len(overdraft_days) if overdraft_days else 0, 2
        )
        
        self.log(f"Defaults (12m): {defaults_12m}")
        self.log(f"Arrears (12m): {arrears_12m}")
        self.log(f"Total Transactions: {total_transactions}")
        self.log(f"P2P Accounts: {peer_to_peer_count}")
        self.log(f"Gambling Activity: £{data['averageTotalGambling']:.2f}")
        self.log(f"Avg Overdraft Days: {data['averageOverdraftUsageInDays']:.1f}")
        
        return data
    
    def analyze(self, include_data_extraction: bool = True) -> Dict[str, Any]:
        """
        Main analysis method that returns the complete analysis
        
        Args:
            include_data_extraction: If True, includes comprehensive data extraction (default: True)
        
        Returns:
            Dictionary with summary (extracted data), flags, score, and traffic_light
        """
        self.log("\n" + "🔍 STARTING CREDIT REPORT ANALYSIS " + "🔍")
        self.log("="*60)
        
        # Parse data
        ccjs = self.parse_ccj_data()
        accounts = self.parse_credit_accounts()
        
        self.log("\n" + "="*60)
        self.log("RUNNING RISK FLAG CHECKS")
        self.log("="*60)
        
        # Check all flags
        flags = {
            'active_ccj': self.check_active_ccj(ccjs),
            'multiple_ccjs': self.check_multiple_ccjs(ccjs),
            'active_default': self.check_active_default(accounts),
            'debt_collection': self.check_debt_collection(accounts),
            'ap_marker': self.check_ap_marker(accounts),
            'arrears': self.check_arrears(accounts),
            'utilisation': self.check_utilisation(accounts),
            'rapid_borrowing': self.check_rapid_borrowing(accounts),
            'repeat_lending': self.check_repeat_lending(accounts)
        }
        
        # Calculate score and traffic light
        score = self.calculate_score(flags)
        traffic_light = self.determine_traffic_light(score)
        
        # Extract comprehensive data for summary
        summary = {}
        if include_data_extraction:
            summary = self.extract_report_data()
        
        self.log("\n" + "="*60)
        self.log("✅ ANALYSIS COMPLETE")
        self.log("="*60)
        
        return {
            "summary": summary,
            "flags": flags,
            "score": score,
            "traffic_light": traffic_light
        }

# Usage example
def analyze_credit_report(url_or_html: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Analyze a credit report from URL or HTML string.
    
    Args:
        url_or_html: Either a URL starting with 'http' or raw HTML string
        verbose: Enable/disable detailed logging (default: True)
        
    Returns:
        Dictionary with flags, score, and traffic_light
    """
    if url_or_html.startswith('http'):
        html_content = requests.get(url_or_html).text
    else:
        html_content = url_or_html
    
    analyzer = CreditReportAnalyzer(html_content, verbose=verbose)
    return analyzer.analyze()


# Example usage:
if __name__ == "__main__":
    url = "https://api.boshhhfintech.com/File/CreditReport/95d1ce7e-2c3c-49d5-a303-6a4727f91005?Auth=af26383640b084af4d2895307480ed795c334405b786d7419d78be541fcc0656"
    result = analyze_credit_report(url, verbose=True)
    
    print("\n" + "="*60)
    print("FINAL RESULT:")
    print("="*60)
    
    print("\n📋 SUMMARY (Extracted Data):")
    print("-"*60)
    if result.get('summary'):
        for key, value in result['summary'].items():
            print(f"  {key}: {value}")
    else:
        print("  No summary data extracted")
    
    print("\n🚩 FLAGS:")
    print("-"*60)
    for flag, status in result['flags'].items():
        status_icon = "✓" if status else "✗"
        print(f"  {status_icon} {flag}: {status}")
    
    print("\n📊 RISK ASSESSMENT:")
    print("-"*60)
    print(f"  Score: {result['score']}/300")
    
    traffic_light = result['traffic_light']
    if traffic_light == 'GREEN':
        light_emoji = "🟢"
    elif traffic_light == 'AMBER':
        light_emoji = "🟡"
    else:
        light_emoji = "🔴"
    
    print(f"  Traffic Light: {light_emoji} {traffic_light}")
    print("="*60)