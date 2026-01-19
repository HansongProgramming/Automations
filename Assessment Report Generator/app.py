import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import json
from typing import Dict, List, Any

class AccountSummarizer:
    """
    Rule-based summarizer for generating account summaries without LLM APIs.
    """
    
    def __init__(self):
        # Templates for out-of-scope accounts
        self.out_of_scope_templates = {
            'debt_collector': {
                'title': 'Debt purchaser - not original lender',
                'body': 'This account is held by a debt collection agency or debt purchaser who acquired the debt after default. Claims for irresponsible lending must be directed at the original lender who made the lending decision, not subsequent debt owners. The original creditor would need to be identified to pursue any potential claim.'
            },
            'no_lending_decision': {
                'title': 'No lending decision made',
                'body': 'The account relates to a {account_type_lower}, not a credit agreement. As no credit was extended, the FCA\'s irresponsible lending rules do not apply. This type of account falls outside the scope of affordability assessments required for credit products.'
            }
        }
        
        # Templates for in-scope accounts
        self.in_scope_base = {
            'high_risk_approved': {
                'title': 'Potential irresponsible lending - high risk profile at approval',
                'body': 'At the time of lending ({lending_date}), the applicant\'s credit file showed {risk_summary}. Despite these red flags, credit was approved{subprime_note}. This suggests the lender may not have conducted adequate affordability checks or may have lent irresponsibly to a vulnerable customer.'
            },
            'moderate_risk_approved': {
                'title': 'Questionable lending decision - existing credit concerns',
                'body': 'When this credit was approved ({lending_date}), the credit file indicated {risk_summary}. The approval{subprime_note} raises questions about whether proper affordability assessments were conducted, particularly regarding the applicant\'s ability to repay without financial difficulty.'
            },
            'subprime_pattern': {
                'title': 'Sub-prime lending pattern observed',
                'body': 'This account was opened with a sub-prime lender known for higher-risk lending. The account subsequently {outcome_summary}, which may indicate the credit was unaffordable from the outset. Sub-prime lenders have heightened obligations to ensure lending is responsible.'
            },
            'default_pattern': {
                'title': 'Account defaulted - affordability concerns',
                'body': 'This account defaulted on {default_date} with an outstanding balance of {loan_value}. The default occurred {default_timing}, suggesting the credit may have been unaffordable at the point of lending. The lender should have identified this risk through proper affordability checks.'
            },
            'clean_profile': {
                'title': 'Credit approved with clean profile',
                'body': 'At the time of lending ({lending_date}), the credit file showed minimal adverse information. {outcome_note} While this suggests reasonable lending at origination, any subsequent affordability issues would depend on income verification and expenditure checks not visible in the credit file.'
            }
        }
    
    def _format_account_type(self, account_type: str) -> str:
        """Format account type for readability"""
        type_map = {
            'Credit Card': 'credit card',
            'Current Account': 'current account',
            'Comms Supply Account': 'communications supply service',
            'Unsecured Loan': 'unsecured personal loan',
            'Fixed Term Agreement': 'fixed-term credit agreement',
            'Hire Purchase': 'hire purchase agreement',
            'Mail Order Account': 'mail order credit account',
            'Budget Account': 'budget account',
            'Home Lending Agreement': 'secured home lending'
        }
        return type_map.get(account_type, account_type.lower())
    
    def _build_risk_summary(self, risk_indicators: Dict) -> str:
        """Build human-readable risk summary from indicators"""
        if risk_indicators.get('unable_to_determine'):
            return 'insufficient information to determine the risk profile at that time'
        
        risks = []
        
        ccj_count = risk_indicators.get('active_ccjs_at_lending', 0)
        if ccj_count > 0:
            risks.append(f"{ccj_count} active CCJ{'s' if ccj_count > 1 else ''}")
        
        default_count = risk_indicators.get('active_defaults_at_lending', 0)
        if default_count > 0:
            risks.append(f"{default_count} existing default{'s' if default_count > 1 else ''}")
        
        arrears_count = risk_indicators.get('accounts_in_arrears_at_lending', 0)
        if arrears_count > 0:
            risks.append(f"arrears on {arrears_count} account{'s' if arrears_count > 1 else ''}")
        
        if risk_indicators.get('recent_payment_issues'):
            risks.append('recent payment difficulties within the past 12 months')
        
        if not risks:
            return 'a relatively clean credit profile with minimal adverse information'
        
        if len(risks) == 1:
            return risks[0]
        elif len(risks) == 2:
            return f"{risks[0]} and {risks[1]}"
        else:
            return f"{', '.join(risks[:-1])}, and {risks[-1]}"
    
    def _calculate_risk_level(self, risk_indicators: Dict) -> str:
        """Determine overall risk level"""
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
    
    def _get_outcome_summary(self, payment_history_summary: Dict, default_date: str) -> str:
        """Summarize account outcome"""
        if default_date and default_date != 'N/A':
            return 'ended in default'
        
        defaults = payment_history_summary.get('defaults', 0)
        arrears = payment_history_summary.get('arrears', 0)
        ap = payment_history_summary.get('arrangement_to_pay', 0)
        
        if defaults > 0:
            return 'was marked as defaulted'
        elif arrears > 5:
            return 'showed persistent payment difficulties'
        elif ap > 0:
            return 'required arrangement to pay'
        elif arrears > 0:
            return 'experienced some payment issues'
        else:
            return 'maintained regular payments'
    
    def _calculate_default_timing(self, lending_date: str, default_date: str) -> str:
        """Calculate timing between lending and default"""
        try:
            lend_dt = datetime.strptime(lending_date, '%d/%m/%Y')
            def_dt = datetime.strptime(default_date, '%d/%m/%Y')
            months = (def_dt.year - lend_dt.year) * 12 + (def_dt.month - lend_dt.month)
            
            if months < 6:
                return 'within 6 months of the account opening'
            elif months < 12:
                return 'within the first year'
            elif months < 24:
                return f'approximately {months // 12} year after opening'
            else:
                return f'approximately {months // 12} years after opening'
        except:
            return 'after the account was opened'
    
    def summarize_out_of_scope(self, account: Dict) -> Dict[str, str]:
        """Generate summary for out-of-scope account"""
        lender = account['lender']
        account_type = account['account_type']
        exclusion_reason = account['exclusion_reason']
        
        template = self.out_of_scope_templates.get(exclusion_reason, {
            'title': 'Out of scope',
            'body': 'This account falls outside the scope of irresponsible lending claims.'
        })
        
        return {
            'name': lender,
            'type': account_type,
            'title': template['title'],
            'body': template['body'].format(
                account_type_lower=self._format_account_type(account_type)
            )
        }
    
    def summarize_in_scope(self, account: Dict) -> Dict[str, str]:
        """Generate summary for in-scope account"""
        lender = account['lender']
        account_type = account['account_type']
        lending_date = account.get('start_date', 'Unknown')
        default_date = account.get('default_date', 'N/A')
        loan_value = account.get('loan_value', '£0')
        is_subprime = account.get('is_subprime_lender', False)
        risk_indicators = account.get('risk_indicators_at_lending', {})
        payment_summary = account.get('payment_history_summary', {})
        
        # Determine which template to use
        risk_level = self._calculate_risk_level(risk_indicators)
        has_default = default_date and default_date != 'N/A'
        
        # Select template
        if has_default and risk_level in ['high', 'moderate']:
            template_key = 'default_pattern'
        elif risk_level == 'high':
            template_key = 'high_risk_approved'
        elif risk_level == 'moderate':
            template_key = 'moderate_risk_approved'
        elif is_subprime and has_default:
            template_key = 'subprime_pattern'
        else:
            template_key = 'clean_profile'
        
        template = self.in_scope_base[template_key]
        
        # Build context-specific variables
        risk_summary = self._build_risk_summary(risk_indicators)
        subprime_note = ' by a sub-prime lender' if is_subprime else ''
        outcome_summary = self._get_outcome_summary(payment_summary, default_date)
        
        outcome_note = ''
        if has_default:
            outcome_note = f'However, the account subsequently defaulted on {default_date}.'
        elif payment_summary.get('arrears', 0) > 0:
            outcome_note = 'The account later showed signs of payment difficulties.'
        
        default_timing = self._calculate_default_timing(lending_date, default_date) if has_default else ''
        
        body = template['body'].format(
            lending_date=lending_date,
            risk_summary=risk_summary,
            subprime_note=subprime_note,
            outcome_summary=outcome_summary,
            default_date=default_date,
            loan_value=loan_value,
            default_timing=default_timing,
            outcome_note=outcome_note
        )
        
        return {
            'name': lender,
            'type': account_type,
            'title': template['title'],
            'body': body
        }


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
        
    def parse_ccj_data(self) -> List[Dict[str, Any]]:
        """Extract County Court Judgement (CCJ) data"""
        ccjs = []
        content = self.soup.get_text()
        
        # Find the Public Records section
        ccj_section_match = re.search(r'Public Records at Supplied Address 1(.*?)(?:Public Records at Linked Address|---)', content, re.DOTALL)
        
        if not ccj_section_match:
            return ccjs
        
        ccj_section = ccj_section_match.group(1)
        
        # Split by "County Court Judgement (CCJ)" headers
        ccj_blocks = re.split(r'County Court Judgement \(CCJ\)', ccj_section)
        
        for block in ccj_blocks[1:]:  # Skip first split (before first CCJ)
            ccj_data = {}
            
            # Extract date (may be on same line as CCJ header or in data)
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', block[:50])  # Check first 50 chars
            if date_match:
                ccj_data['date'] = date_match.group(1)
            
            # Extract court name
            court_match = re.search(r'Court Name\s*([A-Z\s]+?)(?:Case Number|$)', block)
            if court_match:
                ccj_data['court_name'] = court_match.group(1).strip()
            
            # Extract case number (but not "Old Case Number")
            case_match = re.search(r'Case Number\s*([A-Z0-9]+)', block)
            if case_match:
                ccj_data['case_number'] = case_match.group(1).strip()
            
            # Extract case type
            type_match = re.search(r'Case Type\s*([A-Z]+)', block)
            if type_match:
                ccj_data['case_type'] = type_match.group(1).strip()
            
            # Extract amount
            amount_match = re.search(r'Amount\s*(\d+)\s*GBP', block)
            if amount_match:
                try:
                    ccj_data['amount'] = int(amount_match.group(1))
                except:
                    ccj_data['amount'] = 0
            
            # Only add if we found a case number
            if ccj_data.get('case_number'):
                ccjs.append(ccj_data)
        
        return ccjs
    
    def parse_credit_accounts(self) -> List[Dict[str, Any]]:
        """Extract all credit account information"""
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
                    # If can't parse date, assume active
                    active_ccjs.append(ccj)
            else:
                # No date means assume active
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
            
            # Also check payment history for 'D' code
            for payment in account.get('payment_history', []):
                if payment['code'] == 'D':
                    if account_num not in defaults_found:
                        defaults_found.append(account_num)
        
        result = len(defaults_found) > 0
        points = 30 if result else 0
        return result, points
    
    def check_debt_collection(self, accounts: List[Dict]) -> tuple[bool, int]:
        """Check if accounts are with debt collection agencies. Returns (flagged, points)"""
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
                    collection_accounts.append(account_num)
                    break
            
            # Check for Transfer marker ('X' code)
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
        
        # Check overall utilization
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
        """
        Calculate traffic light based on total penalty points.
        70+ = GREEN
        40-69 = AMBER
        <40 = RED
        """
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
        
        # Extract client name from header
        name_match = re.search(r'^([A-Z\s]+)\s+Credit File', content, re.MULTILINE)
        if name_match:
            client_info['name'] = name_match.group(1).strip()
        
        # Extract supplied address
        supplied_addr_pattern = r'Supplied Address 1\s+(\d+)\s+([A-Z\s]+)\s+([A-Z0-9\s]+)\s+([A-Z\s]+)'
        supplied_match = re.search(supplied_addr_pattern, content)
        if supplied_match:
            client_info['address'] = f"{supplied_match.group(1)} {supplied_match.group(2).strip()}, {supplied_match.group(4).strip()}, {supplied_match.group(3).strip()}"
        
        return client_info
    
    def categorize_accounts_for_claims(self, accounts: List[Dict], ccjs: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize accounts into potential in-scope and out-of-scope claims.
        Returns structured data for summarization.
        """
        # Debt collection agencies (out of scope - not original lenders)
        DEBT_COLLECTORS = [
            "LOWELL", "CABOT", "PRA", "LANTERN", "PERCH", "WESCOT",
            "INTRUM", "RESOLVE", "FAIRFAX", "PORTFOLIO", "RECOVER",
            "RECOVERY", "COLLECTION", "DEBT", "HOLDINGS"
        ]
        
        # Sub-prime lenders known for high-risk lending
        SUBPRIME_LENDERS = [
            "VANQUIS", "AQUA", "NEWDAY", "CAPITAL ONE", "JAJA",
            "ZABLE", "INDIGO", "OCEAN", "PROVIDENT", "MORSES"
        ]
        
        # Account types that are not lending decisions
        NON_LENDING_TYPES = [
            "Current Account", "Comms Supply Account"
        ]
        
        in_scope = []
        out_of_scope = []
        
        # Build credit file timeline for context
        credit_timeline = {
            'ccjs': [],
            'defaults': [],
            'arrears_pattern': []
        }
        
        # Process CCJs
        for ccj in ccjs:
            credit_timeline['ccjs'].append({
                'date': ccj.get('date', 'Unknown'),
                'amount': ccj.get('amount', 0),
                'court': ccj.get('court_name', 'Unknown')
            })
        
        # Process each account
        for account in accounts:
            lender = account.get('Lender', 'Unknown').upper()
            account_type = account.get('Account Type', 'Unknown')
            account_num = account.get('Account Number', 'Unknown')
            start_date = account.get('Agreement Start Date', 'Unknown')
            default_date = account.get('Default Date', 'N/A')
            loan_value = account.get('Loan Value', '£0')
            credit_limit = account.get('Credit Limit', 'N/A')
            
            # Track defaults for timeline
            if default_date and default_date != 'N/A':
                credit_timeline['defaults'].append({
                    'lender': lender,
                    'date': default_date,
                    'amount': loan_value
                })
            
            # Track arrears pattern
            payment_history = account.get('payment_history', [])
            arrears_count = sum(1 for p in payment_history if p['code'] in ['1', '2', '3', '4', '5', '6', 'A', 'B'])
            if arrears_count > 0:
                credit_timeline['arrears_pattern'].append({
                    'lender': lender,
                    'account': account_num,
                    'arrears_months': arrears_count
                })
            
            # Determine if out of scope
            is_debt_collector = any(keyword in lender for keyword in DEBT_COLLECTORS)
            is_non_lending = account_type in NON_LENDING_TYPES
            
            # Build account summary
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
            
            if is_debt_collector:
                # Out of scope - debt purchaser/collector
                out_of_scope.append({
                    **account_summary,
                    'exclusion_reason': 'debt_collector',
                    'notes': 'Not original lender - debt purchaser/collection agency'
                })
            
            elif is_non_lending:
                # Out of scope - not a lending decision
                out_of_scope.append({
                    **account_summary,
                    'exclusion_reason': 'no_lending_decision',
                    'notes': 'Account type does not involve credit lending decision'
                })
            
            else:
                # Potentially in scope - calculate risk indicators at time of lending
                risk_indicators = self._calculate_risk_at_lending_date(
                    start_date, ccjs, accounts, account
                )
                
                # Check if sub-prime lender
                is_subprime = any(sp in lender for sp in SUBPRIME_LENDERS)
                
                in_scope.append({
                    **account_summary,
                    'is_subprime_lender': is_subprime,
                    'risk_indicators_at_lending': risk_indicators
                })
        
        return {
            'in_scope_accounts': in_scope,
            'out_of_scope_accounts': out_of_scope,
            'credit_timeline': credit_timeline
        }
    
    def _calculate_risk_at_lending_date(self, lending_date_str: str, ccjs: List[Dict], 
                                       all_accounts: List[Dict], current_account: Dict) -> Dict[str, Any]:
        """
        Calculate what risk indicators were present at the time of lending decision.
        This helps determine if lender had red flags visible when they approved credit.
        """
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
        
        # Check CCJs active at lending date
        for ccj in ccjs:
            if ccj.get('date'):
                try:
                    ccj_date = datetime.strptime(ccj['date'], '%Y-%m-%d')
                    # CCJ active if it was within 6 years before lending
                    if ccj_date <= lending_date and (lending_date - ccj_date).days <= 6*365:
                        risk_flags['active_ccjs_at_lending'] += 1
                except:
                    pass
        
        # Check other accounts for defaults/arrears before this lending date
        for account in all_accounts:
            # Skip checking the current account against itself
            if account.get('Account Number') == current_account.get('Account Number'):
                continue
            
            # Check if default occurred before lending
            default_date_str = account.get('Default Date', 'N/A')
            if default_date_str and default_date_str != 'N/A':
                try:
                    default_date = datetime.strptime(default_date_str, '%d/%m/%Y')
                    if default_date <= lending_date:
                        risk_flags['active_defaults_at_lending'] += 1
                except:
                    pass
            
            # Check payment history for arrears before lending
            for payment in account.get('payment_history', []):
                try:
                    payment_date = datetime(payment['year'], payment['month'], 1)
                    if payment_date <= lending_date:
                        if payment['code'] in ['1', '2', '3', '4', '5', '6', 'A', 'B']:
                            risk_flags['accounts_in_arrears_at_lending'] += 1
                            # Check if recent (within 12 months of lending)
                            if (lending_date - payment_date).days <= 365:
                                risk_flags['recent_payment_issues'] = True
                except:
                    pass
        
        return risk_flags
    
    def analyze(self) -> Dict[str, Any]:
        """Main analysis method that returns JSON-ready results"""
        # Parse data
        ccjs = self.parse_ccj_data()
        accounts = self.parse_credit_accounts()
        client_info = self.extract_client_info()
        
        # Check all indicators and accumulate points
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
        
        # Calculate traffic light
        traffic_light = self.calculate_traffic_light(total_points)
        
        # Categorize accounts for claims analysis
        claims_data = self.categorize_accounts_for_claims(accounts, ccjs)
        
        # Generate summaries for each account
        in_scope_summaries = []
        for account in claims_data['in_scope_accounts']:
            summary = self.summarizer.summarize_in_scope(account)
            in_scope_summaries.append(summary)
        
        out_of_scope_summaries = []
        for account in claims_data['out_of_scope_accounts']:
            summary = self.summarizer.summarize_out_of_scope(account)
            out_of_scope_summaries.append(summary)
        
        return {
            "client_info": client_info,
            "indicators": indicators,
            "total_points": total_points,
            "traffic_light": traffic_light,
            "claims_analysis": {
                "in_scope": in_scope_summaries,
                "out_of_scope": out_of_scope_summaries,
                "credit_timeline": claims_data['credit_timeline']
            }
        }


def analyze_credit_report(url_or_html: str) -> Dict[str, Any]:
    """
    Analyze a credit report from URL or HTML string.
    
    Args:
        url_or_html: Either a URL starting with 'http' or raw HTML string
        
    Returns:
        Dictionary with indicators, total_points, traffic_light, and account summaries
    """
    if url_or_html.startswith('http'):
        html_content = requests.get(url_or_html).text
    else:
        html_content = url_or_html
    
    analyzer = CreditReportAnalyzer(html_content)
    return analyzer.analyze()


# Example usage:
if __name__ == "__main__":
    url = "https://api.boshhhfintech.com/File/CreditReport/95d1ce7e-2c3c-49d5-a303-6a4727f91005?Auth=af26383640b084af4d2895307480ed795c334405b786d7419d78be541fcc0656"
    result = analyze_credit_report(url)
    
    # Print JSON output
    print(json.dumps(result, indent=2))