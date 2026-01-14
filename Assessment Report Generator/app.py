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
            # Safe print that handles encoding issues
            try:
                print(f"[ANALYZER] {message}")
            except UnicodeEncodeError:
                print(f"[ANALYZER] {message.encode('ascii', 'ignore').decode('ascii')}")
        
    def parse_ccj_data(self) -> List[Dict[str, Any]]:
        """Extract County Court Judgement (CCJ) data"""
        self.log("\n" + "="*60)
        self.log("PARSING CCJ DATA")
        self.log("="*60)
        
        ccjs = []
        
        # Find all CCJ sections in tables
        tables = self.soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            ccj_data = {}
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) == 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    
                    if 'Court Name' in key:
                        ccj_data['court_name'] = value
                    elif 'Case Number' in key and 'Old' not in key:
                        ccj_data['case_number'] = value
                    elif 'Case Type' in key:
                        ccj_data['case_type'] = value
                    elif 'Amount' in key and 'GBP' in value:
                        try:
                            ccj_data['amount'] = int(re.sub(r'[^\d]', '', value))
                        except:
                            ccj_data['amount'] = 0
            
            # Check if this table had CCJ data
            if ccj_data.get('case_number'):
                # Try to find date in the row before the table
                date_match = None
                prev = table.find_previous(['p', 'td'])
                if prev:
                    date_text = prev.get_text(strip=True)
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_text)
                
                ccj_data['date'] = date_match.group(1) if date_match else None
                ccjs.append(ccj_data)
                
                self.log(f"CCJ: Court={ccj_data.get('court_name', 'N/A')}, " +
                        f"Case={ccj_data['case_number']}, " +
                        f"Amount=£{ccj_data.get('amount', 0):,}, " +
                        f"Date={ccj_data['date']}")
        
        self.log(f"Total CCJs found: {len(ccjs)}")
        return ccjs
    
    def parse_credit_accounts(self) -> List[Dict[str, Any]]:
        """Extract all credit account information"""
        self.log("\n" + "="*60)
        self.log("PARSING CREDIT ACCOUNTS")
        self.log("="*60)
        
        accounts = []
        content = self.soup.get_text()
        
        # Split by account type headers
        account_sections = re.split(r'(Comms Supply Account|Credit Card|Current Account|Fixed Term Agreement|Hire Purchase|Unsecured Loan|Mail Order Account|Budget Account|Home Lending Agreement)', content)
        
        for i in range(1, len(account_sections), 2):
            if i+1 < len(account_sections):
                account_type = account_sections[i]
                account_text = account_sections[i+1]
                
                # Extract account details
                account_data = {'Account Type': account_type}
                
                # Account number
                acc_match = re.search(r'Account Number\s*(\S+)', account_text)
                if acc_match:
                    account_data['Account Number'] = acc_match.group(1)
                
                # Loan value
                loan_match = re.search(r'Loan Value\s*£(\d+)', account_text)
                if loan_match:
                    account_data['Loan Value'] = f"£{loan_match.group(1)}"
                
                # Credit limit
                limit_match = re.search(r'Credit Limit\s*£(\S+)', account_text)
                if limit_match:
                    account_data['Credit Limit'] = f"£{limit_match.group(1)}"
                
                # Dates
                start_match = re.search(r'Agreement Start Date\s*(\d{2}/\d{2}/\d{4})', account_text)
                if start_match:
                    account_data['Agreement Start Date'] = start_match.group(1)
                
                default_match = re.search(r'Default Date\s*(\d{2}/\d{2}/\d{4})', account_text)
                if default_match:
                    account_data['Default Date'] = default_match.group(1)
                elif 'Default Date' in account_text and 'N/A' in account_text:
                    account_data['Default Date'] = 'N/A'
                
                # Lender name (from the line after account type)
                lender_match = re.search(r'from ([A-Z\s&\(\)\.]+?)(?:\(I\)|\d)', account_text)
                if lender_match:
                    account_data['Lender'] = lender_match.group(1).strip()
                
                # Payment history - look for year rows followed by month codes
                payment_history = []
                payment_section = re.search(r'Payment History.*?(?=\n\n|\Z)', account_text, re.DOTALL)
                if payment_section:
                    lines = payment_section.group(0).split('\n')
                    current_year = None
                    
                    for line in lines:
                        # Check if line starts with a year
                        year_match = re.match(r'^(20\d{2})\s+(.+)$', line.strip())
                        if year_match:
                            current_year = int(year_match.group(1))
                            codes = year_match.group(2).split()
                            
                            for month_idx, code in enumerate(codes, 1):
                                if code and code not in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']:
                                    payment_history.append({
                                        'year': current_year,
                                        'month': month_idx,
                                        'code': code
                                    })
                
                account_data['payment_history'] = payment_history
                
                if account_data.get('Account Number'):
                    accounts.append(account_data)
                    
                    self.log(f"\nAccount: {account_data.get('Account Number')}")
                    self.log(f"  Type: {account_type}")
                    self.log(f"  Lender: {account_data.get('Lender', 'Unknown')}")
                    self.log(f"  Loan Value: {account_data.get('Loan Value', '£0')}")
                    self.log(f"  Credit Limit: {account_data.get('Credit Limit', 'N/A')}")
                    self.log(f"  Default Date: {account_data.get('Default Date', 'N/A')}")
                    self.log(f"  Payment History Entries: {len(payment_history)}")
        
        self.log(f"\nTotal accounts parsed: {len(accounts)}")
        return accounts
    
    def check_active_ccj(self, ccjs: List[Dict]) -> tuple[bool, int]:
        """Check if there are active CCJs (within 6 years). Returns (flagged, points)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Active CCJ")
        self.log("-"*60)
        
        six_years_ago = self.current_date - timedelta(days=6*365)
        active_ccjs = []
        
        for ccj in ccjs:
            if ccj.get('date'):
                try:
                    ccj_date = datetime.strptime(ccj['date'], '%Y-%m-%d')
                    is_active = ccj_date >= six_years_ago
                    if is_active:
                        active_ccjs.append(ccj)
                except:
                    # If can't parse date, assume active
                    active_ccjs.append(ccj)
            else:
                # No date means assume active
                active_ccjs.append(ccj)
        
        result = len(active_ccjs) > 0
        points = 40 if result else 0
        self.log(f"Active CCJs: {len(active_ccjs)}/{len(ccjs)}")
        self.log(f"RESULT: {'+' + str(points) if points > 0 else 'PASS'}")
        return result, points
    
    def check_multiple_ccjs(self, ccjs: List[Dict]) -> tuple[bool, int]:
        """Check if there are multiple CCJs (2+). Returns (flagged, points)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Multiple CCJs")
        self.log("-"*60)
        
        result = len(ccjs) >= 2
        points = 50 if result else 0
        self.log(f"Total CCJs: {len(ccjs)} (threshold: >= 2)")
        self.log(f"RESULT: {'+' + str(points) if points > 0 else 'PASS'}")
        return result, points
    
    def check_active_default(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check for active defaults. Returns (flagged, points)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Active Default")
        self.log("-"*60)
        
        defaults_found = []
        
        for account in accounts:
            account_num = account.get('Account Number', 'Unknown')
            default_date = account.get('Default Date', 'N/A')
            
            if default_date and default_date != 'N/A':
                self.log(f"Account {account_num}: Default Date = {default_date}")
                defaults_found.append(account_num)
            
            # Also check payment history for 'D' code
            for payment in account.get('payment_history', []):
                if payment['code'] == 'D':
                    self.log(f"Account {account_num}: 'D' code in {payment['year']}-{payment['month']:02d}")
                    if account_num not in defaults_found:
                        defaults_found.append(account_num)
        
        result = len(defaults_found) > 0
        points = 30 if result else 0
        self.log(f"Accounts with defaults: {len(defaults_found)}")
        self.log(f"RESULT: {'+' + str(points) if points > 0 else 'PASS'}")
        return result, points
    
    def check_debt_collection(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check if accounts are with debt collection agencies. Returns (flagged, points)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Debt Collection")
        self.log("-"*60)
        
        DEBT_KEYWORDS = [
            "LOWELL", "CABOT", "PRA", "LANTERN", "PERCH", "WESCOT",
            "INTRUM", "RESOLVE", "FAIRFAX", "PORTFOLIO", "RECOVER",
            "RECOVERY", "COLLECTION", "DEBT", "HOLDINGS"
        ]
        
        collection_accounts = []
        
        for account in accounts:
            account_num = account.get('Account Number', 'Unknown')
            lender = account.get('Lender', '').upper()
            
            # Check for debt collection keywords
            for keyword in DEBT_KEYWORDS:
                if keyword in lender:
                    self.log(f"Account {account_num}: Debt collector '{lender}'")
                    collection_accounts.append(account_num)
                    break
            
            # Check for Transfer marker ('X' code)
            for payment in account.get('payment_history', []):
                if payment['code'] == 'X':
                    self.log(f"Account {account_num}: Transfer marker 'X'")
                    if account_num not in collection_accounts:
                        collection_accounts.append(account_num)
                    break
        
        result = len(collection_accounts) > 0
        points = 25 if result else 0
        self.log(f"Debt collection accounts: {len(collection_accounts)}")
        self.log(f"RESULT: {'+' + str(points) if points > 0 else 'PASS'}")
        return result, points
    
    def check_ap_marker(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check for arrangement to pay markers. Returns (flagged, points)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Arrangement to Pay (AP) Marker")
        self.log("-"*60)
        
        ap_accounts = []
        
        for account in accounts:
            account_num = account.get('Account Number', 'Unknown')
            for payment in account.get('payment_history', []):
                if payment['code'] == 'I':
                    self.log(f"Account {account_num}: 'I' code in {payment['year']}-{payment['month']:02d}")
                    if account_num not in ap_accounts:
                        ap_accounts.append(account_num)
        
        result = len(ap_accounts) > 0
        points = 20 if result else 0
        self.log(f"Accounts with AP marker: {len(ap_accounts)}")
        self.log(f"RESULT: {'+' + str(points) if points > 0 else 'PASS'}")
        return result, points
    
    def check_arrears(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check for arrears in last 6 months. Returns (flagged, points)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Arrears (Last 6 Months)")
        self.log("-"*60)
        
        six_months_ago = self.current_date - timedelta(days=180)
        arrears_found = []
        
        for account in accounts:
            account_num = account.get('Account Number', 'Unknown')
            for payment in account.get('payment_history', []):
                payment_date = datetime(payment['year'], payment['month'], 1)
                if payment_date >= six_months_ago:
                    if payment['code'] in self.arrears_codes:
                        self.log(f"Account {account_num}: Code '{payment['code']}' in {payment['year']}-{payment['month']:02d}")
                        arrears_found.append({'account': account_num, 'code': payment['code']})
        
        result = len(arrears_found) > 0
        points = 20 if result else 0
        self.log(f"Arrears entries: {len(arrears_found)}")
        self.log(f"RESULT: {'+' + str(points) if points > 0 else 'PASS'}")
        return result, points
    
    def check_utilisation(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check for high credit utilization (>80%). Returns (flagged, points)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Credit Utilization (>80%)")
        self.log("-"*60)
        
        total_used = 0
        total_limit = 0
        high_util_accounts = []
        
        for account in accounts:
            try:
                loan_value_str = account.get('Loan Value', '£0')
                credit_limit_str = account.get('Credit Limit', '£N/A')
                account_num = account.get('Account Number', 'Unknown')
                
                if credit_limit_str and credit_limit_str != '£N/A':
                    loan_value = int(re.sub(r'[^\d]', '', loan_value_str))
                    credit_limit = int(re.sub(r'[^\d]', '', credit_limit_str))
                    
                    if credit_limit > 0:
                        total_used += loan_value
                        total_limit += credit_limit
                        
                        utilization = loan_value / credit_limit
                        self.log(f"Account {account_num}: £{loan_value:,} / £{credit_limit:,} = {utilization*100:.1f}%")
                        
                        if utilization > 0.80:
                            high_util_accounts.append(account_num)
            except:
                continue
        
        # Check overall utilization
        overall_high = False
        if total_limit > 0:
            overall_util = total_used / total_limit
            self.log(f"OVERALL: £{total_used:,} / £{total_limit:,} = {overall_util*100:.1f}%")
            overall_high = overall_util > 0.80
        
        result = len(high_util_accounts) > 0 or overall_high
        points = 15 if result else 0
        self.log(f"RESULT: {'+' + str(points) if points > 0 else 'PASS'}")
        return result, points
    
    def check_rapid_borrowing(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check for rapid borrowing (3+ accounts in 6 months). Returns (flagged, points)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Rapid Borrowing Acceleration")
        self.log("-"*60)
        
        six_months_ago = self.current_date - timedelta(days=180)
        recent_accounts = []
        
        for account in accounts:
            start_date_str = account.get('Agreement Start Date', '')
            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
                    if start_date >= six_months_ago:
                        self.log(f"Account {account.get('Account Number')}: Opened {start_date.strftime('%Y-%m-%d')}")
                        recent_accounts.append(account.get('Account Number'))
                except:
                    continue
        
        result = len(recent_accounts) >= 3
        points = 15 if result else 0
        self.log(f"New accounts in 6 months: {len(recent_accounts)} (threshold: >= 3)")
        self.log(f"RESULT: {'+' + str(points) if points > 0 else 'PASS'}")
        return result, points
    
    def check_repeat_lending(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check for repeat lending with same providers. Returns (flagged, points)"""
        self.log("\n" + "-"*60)
        self.log("CHECKING: Repeat Lending")
        self.log("-"*60)
        
        providers = {}
        
        for account in accounts:
            lender = account.get('Lender', 'Unknown')
            account_num = account.get('Account Number', 'Unknown')
            
            if lender not in providers:
                providers[lender] = []
            providers[lender].append(account_num)
        
        repeat_providers = []
        for provider, account_list in providers.items():
            if len(account_list) >= 2:
                self.log(f"Provider '{provider}': {len(account_list)} accounts")
                repeat_providers.append(provider)
        
        result = len(repeat_providers) > 0
        points = 25 if result else 0
        self.log(f"Providers with multiple accounts: {len(repeat_providers)}")
        self.log(f"RESULT: {'+' + str(points) if points > 0 else 'PASS'}")
        return result, points
    
    def calculate_score_and_traffic_light(self, total_points: int) -> tuple[int, str]:
        """
        Calculate traffic light based on total penalty points.
        70+ = GREEN
        40-69 = AMBER
        <40 = RED
        """
        self.log("\n" + "="*60)
        self.log("DETERMINING TRAFFIC LIGHT STATUS")
        self.log("="*60)
        self.log(f"Total Penalty Points: {total_points}")
        self.log("Thresholds: RED (<40) | AMBER (40-69) | GREEN (70+)")
        
        if total_points >= 70:
            traffic_light = 'GREEN'
        elif total_points >= 40:
            traffic_light = 'AMBER'
        else:
            traffic_light = 'RED'
        
        self.log(f"Traffic Light: {traffic_light}")
        return total_points, traffic_light
    
    def analyze(self) -> Dict[str, Any]:
        """Main analysis method"""
        self.log("\n" + "STARTING CREDIT REPORT ANALYSIS")
        self.log("="*60)
        
        # Parse data
        ccjs = self.parse_ccj_data()
        accounts = self.parse_credit_accounts()
        
        self.log("\n" + "="*60)
        self.log("RUNNING RISK FLAG CHECKS")
        self.log("="*60)
        
        # Check all flags and accumulate points
        total_points = 0
        flags = {}
        
        flag, pts = self.check_active_ccj(ccjs)
        flags['active_ccj'] = flag
        total_points += pts
        
        flag, pts = self.check_multiple_ccjs(ccjs)
        flags['multiple_ccjs'] = flag
        total_points += pts
        
        flag, pts = self.check_active_default(accounts)
        flags['active_default'] = flag
        total_points += pts
        
        flag, pts = self.check_debt_collection(accounts)
        flags['debt_collection'] = flag
        total_points += pts
        
        flag, pts = self.check_ap_marker(accounts)
        flags['ap_marker'] = flag
        total_points += pts
        
        flag, pts = self.check_arrears(accounts)
        flags['arrears'] = flag
        total_points += pts
        
        flag, pts = self.check_utilisation(accounts)
        flags['utilisation'] = flag
        total_points += pts
        
        flag, pts = self.check_rapid_borrowing(accounts)
        flags['rapid_borrowing'] = flag
        total_points += pts
        
        flag, pts = self.check_repeat_lending(accounts)
        flags['repeat_lending'] = flag
        total_points += pts
        
        # Calculate traffic light
        score, traffic_light = self.calculate_score_and_traffic_light(total_points)
        
        self.log("\n" + "="*60)
        self.log("ANALYSIS COMPLETE")
        self.log("="*60)
        
        return {
            "flags": flags,
            "score": score,
            "traffic_light": traffic_light
        }

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
    
    print("\nFLAGS:")
    print("-"*60)
    for flag, status in result['flags'].items():
        status_icon = "[X]" if status else "[ ]"
        print(f"  {status_icon} {flag}: {status}")
    
    print("\nRISK ASSESSMENT:")
    print("-"*60)
    print(f"  Total Penalty Points: {result['score']}")
    print(f"  Traffic Light: {result['traffic_light']}")
    print("="*60)