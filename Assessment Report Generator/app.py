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
        
        if score >= 250:
            result = 'GREEN'
        elif score >= 150:
            result = 'AMBER'
        else:
            result = 'RED'
        
        self.log(f"Traffic Light: {result}")
        return result
    
    def analyze(self) -> Dict[str, Any]:
        """Main analysis method that returns the complete analysis"""
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
        
        self.log("\n" + "="*60)
        self.log("✅ ANALYSIS COMPLETE")
        self.log("="*60)
        
        return {
            'flags': flags,
            'score': score,
            'traffic_light': traffic_light
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
    # From URL (with verbose logging)
    url = "https://api.boshhhfintech.com/File/CreditReport/95d1ce7e-2c3c-49d5-a303-6a4727f91005?Auth=af26383640b084af4d2895307480ed795c334405b786d7419d78be541fcc0656"
    result = analyze_credit_report(url, verbose=True)
    
    print("\n" + "="*60)
    print("FINAL RESULT:")
    print("="*60)
    print(f"Flags: {result['flags']}")
    print(f"Score: {result['score']}")
    print(f"Traffic Light: {result['traffic_light']}")
    
    # Or from HTML file (with verbose off for clean output)
    # with open('credit_report.html', 'r') as f:
    #     html_content = f.read()
    #     result = analyze_credit_report(html_content, verbose=False)