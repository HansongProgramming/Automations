from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
from .account_summarizer import AccountSummarizer


class CreditReportAnalyzer:
    """
    Analyzes credit report HTML to extract key risk indicators and generate a credit score.
    """
    
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.current_date = datetime.now()
        self.summarizer = AccountSummarizer()
        
        # Payment code definitions
        self.negative_codes = ['1', '2', '3', '4', '5', '6', 'A', 'B', 'D', 'R', 'W', 'V']
        self.arrears_codes = ['1', '2', '3', '4', '5', '6', 'A', 'B']
        self.severe_codes = ['D', 'R', 'W', 'V']
        
        # Load business rules from configuration file
        self._load_config()
    
    def _load_config(self):
        """Load business rules from JSON configuration file."""
        config_path = Path(__file__).parent / 'lending_rules_config.json'
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Load all rule categories from config
            self.DEBT_COLLECTORS = config.get('debt_collectors', [])
            self.SUBPRIME_LENDERS = config.get('subprime_lenders', [])
            self.TELECOM_COMPANIES = config.get('telecom_companies', [])
            self.INSOLVENT_COMPANIES = config.get('insolvent_companies', [])
            self.NON_CREDIT_TYPES = config.get('non_credit_account_types', [])
            self.REPAIR_LENDING_PATTERNS = config.get('repair_lending_patterns', [])
            
        except FileNotFoundError:
            # Fallback to defaults if config file not found
            print(f"Warning: Config file not found at {config_path}. Using default rules.")
            self._load_default_rules()
        except json.JSONDecodeError as e:
            print(f"Warning: Error parsing config file: {e}. Using default rules.")
            self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default rules if config file is not available."""
        self.DEBT_COLLECTORS = ["LOWELL", "CABOT", "PRA", "LANTERN", "PERCH", "WESCOT",
                                "INTRUM", "RESOLVE", "FAIRFAX", "PORTFOLIO", "RECOVER",
                                "RECOVERY", "COLLECTION", "DEBT", "HOLDINGS"]
        self.SUBPRIME_LENDERS = ["VANQUIS", "AQUA", "NEWDAY", "CAPITAL ONE", "JAJA",
                                 "ZABLE", "INDIGO", "OCEAN", "PROVIDENT", "MORSES"]
        self.TELECOM_COMPANIES = ["EE", "O2", "VODAPHONE", "VODAFONE", "SKY", "PHONE", "MOBILE"]
        self.INSOLVENT_COMPANIES = ["MORSES CLUB", "AMIGO LOANS", "INDIGO MICHAEL",
                                    "AVELO", "LENDING WORKS", "RATESETTER"]
        self.NON_CREDIT_TYPES = ["Current Account", "Comms Supply Account"]
        self.REPAIR_LENDING_PATTERNS = ["REPAIR LEND", "REPAIR LOAN"]
        
    def parse_ccj_data(self) -> List[Dict[str, Any]]:
        """Extract County Court Judgement (CCJ) data with deduplication"""
        ccjs = []
        seen_cases = set()
        content = self.soup.get_text()
        
        ccj_section_match = re.search(r'Public Records at Supplied Address 1(.*?)(?:Public Records at Linked Address|---)', content, re.DOTALL)
        
        if not ccj_section_match:
            return ccjs
        
        ccj_section = ccj_section_match.group(1)
        ccj_blocks = re.split(r'County Court Judgement \(CCJ\)', ccj_section)
        
        for block in ccj_blocks[1:]:
            ccj_data = {}
            
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', block[:50])
            if date_match:
                ccj_data['date'] = date_match.group(1)
            
            court_match = re.search(r'Court Name\s*([A-Z\s]+?)(?:Case Number|$)', block)
            if court_match:
                ccj_data['court_name'] = court_match.group(1).strip()
            
            case_match = re.search(r'Case Number\s*([A-Z0-9]+)', block)
            if case_match:
                ccj_data['case_number'] = case_match.group(1).strip()
            
            type_match = re.search(r'Case Type\s*([A-Z]+)', block)
            if type_match:
                ccj_data['case_type'] = type_match.group(1).strip()
            
            amount_match = re.search(r'Amount\s*(\d+)\s*GBP', block)
            if amount_match:
                try:
                    ccj_data['amount'] = int(amount_match.group(1))
                except:
                    ccj_data['amount'] = 0
            
            case_num = ccj_data.get('case_number')
            if case_num and case_num not in seen_cases:
                ccjs.append(ccj_data)
                seen_cases.add(case_num)
        
        return ccjs
    
    def parse_credit_accounts(self) -> List[Dict[str, Any]]:
        """Extract all credit account information with deduplication"""
        seen_accounts = {}
        content = self.soup.get_text()
        
        account_sections = re.split(r'(Comms Supply Account|Credit Card|Current Account|Fixed Term Agreement|Hire Purchase|Unsecured Loan|Mail Order Account|Budget Account|Home Lending Agreement)', content)
        
        for i in range(1, len(account_sections), 2):
            if i+1 < len(account_sections):
                account_type = account_sections[i]
                account_text = account_sections[i+1]
                
                account_data = {'Account Type': account_type}
                
                acc_match = re.search(r'Account Number\s*(\S+)', account_text)
                if acc_match:
                    account_data['Account Number'] = acc_match.group(1)
                
                loan_match = re.search(r'Loan Value\s*£(\d+)', account_text)
                if loan_match:
                    account_data['Loan Value'] = f"£{loan_match.group(1)}"
                
                limit_match = re.search(r'Credit Limit\s*£(\S+)', account_text)
                if limit_match:
                    account_data['Credit Limit'] = f"£{limit_match.group(1)}"
                
                start_match = re.search(r'Agreement Start Date\s*(\d{2}/\d{2}/\d{4})', account_text)
                if start_match:
                    account_data['Agreement Start Date'] = start_match.group(1)
                
                default_match = re.search(r'Default Date\s*(\d{2}/\d{2}/\d{4})', account_text)
                if default_match:
                    account_data['Default Date'] = default_match.group(1)
                elif 'Default Date' in account_text and 'N/A' in account_text:
                    account_data['Default Date'] = 'N/A'
                
                # Fixed regex to properly capture company names with numbers (O2, Loans 2 Go, etc.)
                lender_match = re.search(r'from ([A-Z0-9\s&\(\)\.]+?)(?:\s+\(I\)|\s+Account Number|\n)', account_text)
                if lender_match:
                    account_data['Lender'] = lender_match.group(1).strip()
                
                payment_history = []
                payment_section = re.search(r'Payment History.*?(?=\n\n|\Z)', account_text, re.DOTALL)
                if payment_section:
                    lines = payment_section.group(0).split('\n')
                    current_year = None
                    
                    for line in lines:
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
                
                account_num = account_data.get('Account Number')
                if account_num:
                    if account_num in seen_accounts:
                        existing = seen_accounts[account_num]
                        
                        existing_payments = {(p['year'], p['month']): p for p in existing.get('payment_history', [])}
                        new_payments = {(p['year'], p['month']): p for p in payment_history}
                        
                        combined_payments = {**existing_payments, **new_payments}
                        existing['payment_history'] = sorted(
                            combined_payments.values(), 
                            key=lambda x: (x['year'], x['month'])
                        )
                        
                        for key, value in account_data.items():
                            if key == 'payment_history':
                                continue
                            
                            existing_value = existing.get(key)
                            
                            if not existing_value or existing_value in ['N/A', '£0', '£N/A']:
                                if value and value not in ['N/A', '£0', '£N/A']:
                                    existing[key] = value
                            elif key == 'Default Date' and existing_value == 'N/A' and value != 'N/A':
                                existing[key] = value
                    else:
                        seen_accounts[account_num] = account_data
        
        accounts = list(seen_accounts.values())
        return accounts
    
    def check_active_ccj(self, ccjs: List[Dict]) -> tuple[bool, int]:
        """Check if there are active CCJs (within 6 years). Returns (flagged, points)"""
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
                    active_ccjs.append(ccj)
            else:
                active_ccjs.append(ccj)
        
        result = len(active_ccjs) > 0
        points = 40 if result else 0
        return result, points
    
    def check_multiple_ccjs(self, ccjs: List[Dict]) -> tuple[bool, int]:
        """Check if there are multiple CCJs (2+). Returns (flagged, points)"""
        result = len(ccjs) >= 2
        points = 50 if result else 0
        return result, points
    
    def check_active_default(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check for active defaults. Returns (flagged, points)"""
        defaults_found = []
        
        for account in accounts:
            account_num = account.get('Account Number', 'Unknown')
            default_date = account.get('Default Date', 'N/A')
            
            if default_date and default_date != 'N/A':
                defaults_found.append(account_num)
            
            for payment in account.get('payment_history', []):
                if payment['code'] == 'D':
                    if account_num not in defaults_found:
                        defaults_found.append(account_num)
        
        result = len(defaults_found) > 0
        points = 30 if result else 0
        return result, points
    
    def check_debt_collection(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check if accounts are with debt collection agencies. Returns (flagged, points)"""
        collection_accounts = []
        
        for account in accounts:
            account_num = account.get('Account Number', 'Unknown')
            lender = account.get('Lender', '').upper()
            
            for keyword in self.DEBT_COLLECTORS:
                if keyword in lender:
                    collection_accounts.append(account_num)
                    break
            
            for payment in account.get('payment_history', []):
                if payment['code'] == 'X':
                    if account_num not in collection_accounts:
                        collection_accounts.append(account_num)
                    break
        
        result = len(collection_accounts) > 0
        points = 25 if result else 0
        return result, points
    
    def check_ap_marker(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check for arrangement to pay markers. Returns (flagged, points)"""
        ap_accounts = []
        
        for account in accounts:
            account_num = account.get('Account Number', 'Unknown')
            for payment in account.get('payment_history', []):
                if payment['code'] == 'I':
                    if account_num not in ap_accounts:
                        ap_accounts.append(account_num)
        
        result = len(ap_accounts) > 0
        points = 20 if result else 0
        return result, points
    
    def check_arrears(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check for arrears in last 6 months. Returns (flagged, points)"""
        six_months_ago = self.current_date - timedelta(days=180)
        arrears_found = []
        
        for account in accounts:
            account_num = account.get('Account Number', 'Unknown')
            for payment in account.get('payment_history', []):
                payment_date = datetime(payment['year'], payment['month'], 1)
                if payment_date >= six_months_ago:
                    if payment['code'] in self.arrears_codes:
                        arrears_found.append({'account': account_num, 'code': payment['code']})
        
        result = len(arrears_found) > 0
        points = 20 if result else 0
        return result, points
    
    def check_utilisation(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check for high credit utilization (>80%). Returns (flagged, points)"""
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
                        if utilization > 0.80:
                            high_util_accounts.append(account_num)
            except:
                continue
        
        overall_high = False
        if total_limit > 0:
            overall_util = total_used / total_limit
            overall_high = overall_util > 0.80
        
        result = len(high_util_accounts) > 0 or overall_high
        points = 15 if result else 0
        return result, points
    
    def check_rapid_borrowing(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check for rapid borrowing (3+ accounts in 6 months). Returns (flagged, points)"""
        six_months_ago = self.current_date - timedelta(days=180)
        recent_accounts = []
        
        for account in accounts:
            start_date_str = account.get('Agreement Start Date', '')
            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
                    if start_date >= six_months_ago:
                        recent_accounts.append(account.get('Account Number'))
                except:
                    continue
        
        result = len(recent_accounts) >= 3
        points = 15 if result else 0
        return result, points
    
    def check_repeat_lending(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check for repeat lending with same providers. Returns (flagged, points)"""
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
                repeat_providers.append(provider)
        
        result = len(repeat_providers) > 0
        points = 25 if result else 0
        return result, points
    
    def calculate_traffic_light(self, total_points: int) -> str:
        """Calculate traffic light based on total penalty points."""
        if total_points >= 70:
            return 'GREEN'
        elif total_points >= 40:
            return 'AMBER'
        else:
            return 'RED'
    
    def extract_client_info(self) -> Dict[str, Any]:
        """Extract client name and address information"""
        content = self.soup.get_text()
        
        client_info = {
            'name': None,
            'address': None
        }
        
        # Updated regex to include hyphens, apostrophes, and other common name characters
        name_match = re.search(r'^([A-Z\s\-\'\.\/]+?)\s+Credit File', content, re.MULTILINE)
        if name_match:
            client_info['name'] = name_match.group(1).strip()
        
        supplied_addr_pattern = r'Supplied Address 1\s+(\d+)\s+([A-Z\s]+)\s+([A-Z0-9\s]+)\s+([A-Z\s]+)'
        supplied_match = re.search(supplied_addr_pattern, content)
        if supplied_match:
            client_info['address'] = f"{supplied_match.group(1)} {supplied_match.group(2).strip()}, {supplied_match.group(4).strip()}, {supplied_match.group(3).strip()}"
        
        return client_info
    
    def _group_accounts_by_lender(self, accounts: List[Dict]) -> Dict[str, List[Dict]]:
        """Group accounts by lender, filtering out 'Unknown' lenders"""
        grouped = defaultdict(list)
        
        for account in accounts:
            lender = account.get('lender', 'Unknown').strip()
            # Skip accounts with unknown lenders
            if lender.upper() == 'UNKNOWN' or not lender:
                continue
            grouped[lender].append(account)
        
        return dict(grouped)
    
    def categorize_accounts_for_claims(self, accounts: List[Dict], ccjs: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize accounts into potential in-scope and out-of-scope claims."""
        # Separate accounts into in-scope and out-of-scope first
        in_scope_raw = []
        out_of_scope_raw = []
        
        credit_timeline = {
            'ccjs': [],
            'defaults': [],
            'arrears_pattern': []
        }
        
        for ccj in ccjs:
            credit_timeline['ccjs'].append({
                'date': ccj.get('date', 'Unknown'),
                'amount': ccj.get('amount', 0),
                'court': ccj.get('court_name', 'Unknown')
            })
        
        for account in accounts:
            lender = account.get('Lender', 'Unknown').strip()
            
            # Skip accounts with unknown lenders entirely
            if lender.upper() == 'UNKNOWN' or not lender:
                continue
            
            lender_upper = lender.upper()
            account_type = account.get('Account Type', 'Unknown')
            account_num = account.get('Account Number', 'Unknown')
            start_date = account.get('Agreement Start Date', 'Unknown')
            default_date = account.get('Default Date', 'N/A')
            loan_value = account.get('Loan Value', '£0')
            credit_limit = account.get('Credit Limit', 'N/A')
            
            if default_date and default_date != 'N/A':
                credit_timeline['defaults'].append({
                    'lender': lender_upper,
                    'date': default_date,
                    'amount': loan_value
                })
            
            payment_history = account.get('payment_history', [])
            arrears_count = sum(1 for p in payment_history if p['code'] in ['1', '2', '3', '4', '5', '6', 'A', 'B'])
            if arrears_count > 0:
                credit_timeline['arrears_pattern'].append({
                    'lender': lender_upper,
                    'account': account_num,
                    'arrears_months': arrears_count
                })
            
            account_summary = {
                'lender': lender,
                'account_type': account_type,
                'account_number': account_num,
                'start_date': start_date,
                'loan_value': loan_value,
                'credit_limit': credit_limit,
                'default_date': default_date,
                'payment_history_summary': {
                    'total_entries': len(payment_history),
                    'defaults': sum(1 for p in payment_history if p['code'] == 'D'),
                    'arrears': arrears_count,
                    'arrangement_to_pay': sum(1 for p in payment_history if p['code'] == 'I')
                }
            }
            
            is_debt_collector = any(keyword in lender_upper for keyword in self.DEBT_COLLECTORS)
            is_non_credit = account_type in self.NON_CREDIT_TYPES
            is_telecom = any(keyword in lender_upper for keyword in self.TELECOM_COMPANIES)
            is_insolvent = any(keyword in lender_upper for keyword in self.INSOLVENT_COMPANIES)
            is_repair_lending = any(pattern in lender_upper for pattern in self.REPAIR_LENDING_PATTERNS)
            
            if is_debt_collector:
                out_of_scope_raw.append({
                    **account_summary,
                    'exclusion_reason': 'debt_collector',
                    'notes': 'Not original lender - debt purchaser/collection agency'
                })
            
            elif is_non_credit:
                out_of_scope_raw.append({
                    **account_summary,
                    'exclusion_reason': 'no_lending_decision',
                    'notes': f'{account_type} is not a credit agreement - FCA irresponsible lending rules do not apply'
                })
            
            elif is_telecom:
                out_of_scope_raw.append({
                    **account_summary,
                    'exclusion_reason': 'telecoms_provider',
                    'notes': 'Telecommunications service provider - not subject to irresponsible lending claims'
                })
            
            elif is_insolvent:
                out_of_scope_raw.append({
                    **account_summary,
                    'exclusion_reason': 'company_insolvent',
                    'notes': 'Company is insolvent and no longer in business - cannot pursue claim'
                })
            
            elif is_repair_lending:
                out_of_scope_raw.append({
                    **account_summary,
                    'exclusion_reason': 'repair_lending',
                    'notes': 'Repair lending agreement - secured against property, not considered irresponsible lending risk'
                })
            
            else:
                risk_indicators = self._calculate_risk_at_lending_date(
                    start_date, ccjs, accounts, account
                )
                
                is_subprime = any(sp in lender_upper for sp in self.SUBPRIME_LENDERS)
                
                # Check if this is a "clean profile" case with insufficient evidence
                risk_level = self._assess_risk_level(risk_indicators)
                has_default = default_date and default_date != 'N/A'
                payment_history = account.get('payment_history', [])
                arrears_count = sum(1 for p in payment_history if p['code'] in ['1', '2', '3', '4', '5', '6', 'A', 'B'])
                
                # If clean profile (low risk) with no default and minimal arrears, classify as out-of-scope
                if risk_level == 'low' and not has_default and arrears_count <= 2:
                    out_of_scope_raw.append({
                        'lender': lender,
                        'account_type': account_type,
                        'account_number': account_num,
                        'start_date': start_date,
                        'loan_value': loan_value,
                        'credit_limit': credit_limit,
                        'default_date': default_date,
                        'payment_history_summary': {
                            'total_entries': len(payment_history),
                            'defaults': sum(1 for p in payment_history if p['code'] == 'D'),
                            'arrears': arrears_count,
                            'arrangement_to_pay': sum(1 for p in payment_history if p['code'] == 'I')
                        },
                        'exclusion_reason': 'insufficient_credit_evidence',
                        'notes': 'Clean credit profile at lending - insufficient evidence in credit file to support claim'
                    })
                else:
                    in_scope_raw.append({
                        'lender': lender,
                        'account_type': account_type,
                        'account_number': account_num,
                        'start_date': start_date,
                        'loan_value': loan_value,
                        'credit_limit': credit_limit,
                        'default_date': default_date,
                        'payment_history_summary': {
                            'total_entries': len(payment_history),
                            'defaults': sum(1 for p in payment_history if p['code'] == 'D'),
                            'arrears': arrears_count,
                            'arrangement_to_pay': sum(1 for p in payment_history if p['code'] == 'I')
                        },
                        'is_subprime_lender': is_subprime,
                        'risk_indicators_at_lending': risk_indicators
                    })
        
        # Group by lender
        in_scope_grouped = self._group_accounts_by_lender(in_scope_raw)
        out_of_scope_grouped = self._group_accounts_by_lender(out_of_scope_raw)
        
        # Generate summaries - one per account but grouped display
        in_scope_summaries = []
        for lender, lender_accounts in in_scope_grouped.items():
            if len(lender_accounts) == 1:
                # Single account - process normally
                summary = self.summarizer.summarize_in_scope(lender_accounts[0])
                in_scope_summaries.append(summary)
            else:
                # Multiple accounts - create one grouped summary
                dates = sorted([acc['start_date'] for acc in lender_accounts if acc['start_date'] != 'Unknown'])
                grouped_summary = self.summarizer.summarize_in_scope_grouped(lender, lender_accounts, dates)
                in_scope_summaries.append(grouped_summary)
        
        out_of_scope_summaries = []
        for lender, lender_accounts in out_of_scope_grouped.items():
            if len(lender_accounts) == 1:
                # Single account - process normally
                summary = self.summarizer.summarize_out_of_scope(lender_accounts[0])
                out_of_scope_summaries.append(summary)
            else:
                # Multiple accounts - create one grouped summary
                dates = sorted([acc['start_date'] for acc in lender_accounts if acc['start_date'] != 'Unknown'])
                grouped_summary = self.summarizer.summarize_out_of_scope_grouped(lender, lender_accounts, dates)
                out_of_scope_summaries.append(grouped_summary)
        
        return {
            'in_scope': in_scope_summaries,
            'out_of_scope': out_of_scope_summaries,
            'credit_timeline': credit_timeline
        }
    
    def _calculate_risk_at_lending_date(self, lending_date_str: str, ccjs: List[Dict], 
                                       all_accounts: List[Dict], current_account: Dict) -> Dict[str, Any]:
        """Calculate what risk indicators were present at the time of lending decision."""
        if not lending_date_str or lending_date_str == 'Unknown':
            return {'unable_to_determine': True}
        
        try:
            lending_date = datetime.strptime(lending_date_str, '%d/%m/%Y')
        except:
            return {'unable_to_determine': True}
        
        risk_flags = {
            'active_ccjs_at_lending': 0,
            'active_defaults_at_lending': 0,
            'accounts_in_arrears_at_lending': 0,
            'recent_payment_issues': False,
            'debt_collection_accounts_active': 0
        }
        
        for ccj in ccjs:
            if ccj.get('date'):
                try:
                    ccj_date = datetime.strptime(ccj['date'], '%Y-%m-%d')
                    if ccj_date <= lending_date and (lending_date - ccj_date).days <= 6*365:
                        risk_flags['active_ccjs_at_lending'] += 1
                except:
                    pass
        
        for account in all_accounts:
            if account.get('Account Number') == current_account.get('Account Number'):
                continue
            
            default_date_str = account.get('Default Date', 'N/A')
            if default_date_str and default_date_str != 'N/A':
                try:
                    default_date = datetime.strptime(default_date_str, '%d/%m/%Y')
                    if default_date <= lending_date:
                        risk_flags['active_defaults_at_lending'] += 1
                except:
                    pass
            
            for payment in account.get('payment_history', []):
                try:
                    payment_date = datetime(payment['year'], payment['month'], 1)
                    if payment_date <= lending_date:
                        if payment['code'] in ['1', '2', '3', '4', '5', '6', 'A', 'B']:
                            risk_flags['accounts_in_arrears_at_lending'] += 1
                            if (lending_date - payment_date).days <= 365:
                                risk_flags['recent_payment_issues'] = True
                except:
                    pass
        
        return risk_flags
    
    def _assess_risk_level(self, risk_indicators: Dict[str, Any]) -> str:
        """Assess overall risk level from risk indicators. Returns 'low', 'moderate', or 'high'."""
        if risk_indicators.get('unable_to_determine'):
            return 'unknown'
        
        risk_score = 0
        risk_score += risk_indicators.get('active_ccjs_at_lending', 0) * 3
        risk_score += risk_indicators.get('active_defaults_at_lending', 0) * 3
        risk_score += risk_indicators.get('accounts_in_arrears_at_lending', 0)
        if risk_indicators.get('recent_payment_issues'):
            risk_score += 2
        
        if risk_score >= 6:
            return 'high'
        elif risk_score >= 3:
            return 'moderate'
        else:
            return 'low'
    
    def analyze(self) -> Dict[str, Any]:
        """Main analysis method that returns JSON-ready results"""
        ccjs = self.parse_ccj_data()
        accounts = self.parse_credit_accounts()
        client_info = self.extract_client_info()
        
        total_points = 0
        indicators = {}
        
        flag, pts = self.check_active_ccj(ccjs)
        indicators['active_ccj'] = {'flagged': flag, 'points': pts}
        total_points += pts
        
        flag, pts = self.check_multiple_ccjs(ccjs)
        indicators['multiple_ccjs'] = {'flagged': flag, 'points': pts}
        total_points += pts
        
        flag, pts = self.check_active_default(accounts)
        indicators['active_default'] = {'flagged': flag, 'points': pts}
        total_points += pts
        
        flag, pts = self.check_debt_collection(accounts)
        indicators['debt_collection'] = {'flagged': flag, 'points': pts}
        total_points += pts
        
        flag, pts = self.check_ap_marker(accounts)
        indicators['ap_marker'] = {'flagged': flag, 'points': pts}
        total_points += pts
        
        flag, pts = self.check_arrears(accounts)
        indicators['arrears_last_6_months'] = {'flagged': flag, 'points': pts}
        total_points += pts
        
        flag, pts = self.check_utilisation(accounts)
        indicators['credit_utilisation_over_80'] = {'flagged': flag, 'points': pts}
        total_points += pts
        
        flag, pts = self.check_rapid_borrowing(accounts)
        indicators['rapid_borrowing'] = {'flagged': flag, 'points': pts}
        total_points += pts
        
        flag, pts = self.check_repeat_lending(accounts)
        indicators['repeat_lending'] = {'flagged': flag, 'points': pts}
        total_points += pts
        
        traffic_light = self.calculate_traffic_light(total_points)
        
        claims_data = self.categorize_accounts_for_claims(accounts, ccjs)
        
        return {
            "client_info": client_info,
            "indicators": indicators,
            "total_points": total_points,
            "traffic_light": traffic_light,
            "claims_analysis": claims_data
        }