from datetime import datetime
from typing import Dict, List

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
            },
            'insufficient_credit_evidence': {
                'title': 'Insufficient evidence in credit file',
                'body': 'At the time of lending ({lending_date}), the credit file showed minimal adverse information. Without evidence of defaults, CCJs, or significant payment issues visible in the credit report, there is insufficient basis to establish a claim for irresponsible lending. Any affordability concerns would need to be supported by income and expenditure documentation outside the credit file.'
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
    
    def _format_date_list(self, dates: List[str]) -> str:
        """Format a list of dates for display"""
        if not dates:
            return "Unknown dates"
        if len(dates) == 1:
            return dates[0]
        if len(dates) == 2:
            return f"{dates[0]} and {dates[1]}"
        return f"{', '.join(dates[:-1])}, and {dates[-1]}"
    
    def _format_account_number_list(self, account_numbers: List[str]) -> str:
        """Format a list of account numbers for display"""
        if not account_numbers:
            return "Unknown"
        if len(account_numbers) == 1:
            return account_numbers[0]
        if len(account_numbers) == 2:
            return f"{account_numbers[0]} and {account_numbers[1]}"
        return f"{', '.join(account_numbers[:-1])}, and {account_numbers[-1]}"
    
    def summarize_out_of_scope(self, account: Dict) -> Dict[str, str]:
        """Generate summary for out-of-scope account"""
        lender = account['lender']
        account_type = account['account_type']
        account_number = account.get('account_number', 'Unknown')
        start_date = account.get('start_date', 'Unknown')
        exclusion_reason = account['exclusion_reason']
        
        template = self.out_of_scope_templates.get(exclusion_reason, {
            'title': 'Out of scope',
            'body': 'This account falls outside the scope of irresponsible lending claims.'
        })
        
        # Determine color based on exclusion reason
        color = 'orange' if exclusion_reason == 'insufficient_credit_evidence' else 'gray'
        
        return {
            'name': lender,
            'type': account_type,
            'account_number': account_number,
            'start_date': start_date,
            'title': template['title'],
            'body': template['body'].format(
                account_type_lower=self._format_account_type(account_type),
                lending_date=start_date
            ),
            'color': color
        }
    
    def summarize_out_of_scope_grouped(self, lender: str, accounts: List[Dict], dates: List[str]) -> Dict[str, str]:
        """Generate grouped summary for multiple out-of-scope accounts from same lender"""
        first_account = accounts[0]
        account_type = first_account['account_type']
        exclusion_reason = first_account['exclusion_reason']
        
        # Collect all account numbers
        account_numbers = [acc.get('account_number', 'Unknown') for acc in accounts]
        
        template = self.out_of_scope_templates.get(exclusion_reason, {
            'title': 'Out of scope',
            'body': 'This account falls outside the scope of irresponsible lending claims.'
        })
        
        # Modify title to indicate multiple accounts
        title = f"{template['title']} ({len(accounts)} accounts)"
        
        # Enhance body with date information
        date_info = f" Multiple accounts were opened on {self._format_date_list(dates)}." if dates else ""
        
        # Use first date for template formatting if available
        lending_date = dates[0] if dates else 'Unknown'
        
        body = template['body'].format(
            account_type_lower=self._format_account_type(account_type),
            lending_date=lending_date
        )
        
        # Add date info for insufficient_credit_evidence reason
        if exclusion_reason == 'insufficient_credit_evidence' and date_info:
            body = body.replace('At the time of lending', f'At the time of lending across multiple accounts')
            body += date_info
        else:
            body += date_info
        
        # Determine color based on exclusion reason
        color = 'orange' if exclusion_reason == 'insufficient_credit_evidence' else 'gray'
        
        return {
            'name': lender,
            'type': account_type,
            'account_numbers': account_numbers,  # List of all account numbers
            'start_dates': dates,  # List of all start dates
            'title': title,
            'body': body,
            'color': color
        }
    
    def summarize_in_scope(self, account: Dict) -> Dict[str, str]:
        """Generate summary for in-scope account"""
        lender = account['lender']
        account_type = account['account_type']
        account_number = account.get('account_number', 'Unknown')
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
            'account_number': account_number,
            'start_date': lending_date,
            'title': template['title'],
            'body': body
        }
    
    def summarize_in_scope_grouped(self, lender: str, accounts: List[Dict], dates: List[str]) -> Dict[str, str]:
        """Generate grouped summary for multiple in-scope accounts from same lender"""
        # Analyze all accounts to find the most concerning pattern
        has_any_default = any(acc.get('default_date', 'N/A') != 'N/A' for acc in accounts)
        is_subprime = any(acc.get('is_subprime_lender', False) for acc in accounts)
        
        # Collect all account numbers
        account_numbers = [acc.get('account_number', 'Unknown') for acc in accounts]
        
        # Calculate average/aggregate risk
        risk_levels = [self._calculate_risk_level(acc.get('risk_indicators_at_lending', {})) for acc in accounts]
        highest_risk = 'high' if 'high' in risk_levels else ('moderate' if 'moderate' in risk_levels else 'low')
        
        # Use the most representative account for base template
        representative = accounts[0]
        account_type = representative['account_type']
        
        # Select template based on aggregate analysis
        if has_any_default and highest_risk in ['high', 'moderate']:
            template_key = 'default_pattern'
            title_suffix = f'Pattern of irresponsible lending ({len(accounts)} accounts)'
        elif highest_risk == 'high':
            template_key = 'high_risk_approved'
            title_suffix = f'Multiple high-risk approvals ({len(accounts)} accounts)'
        elif highest_risk == 'moderate':
            template_key = 'moderate_risk_approved'
            title_suffix = f'Repeated questionable lending ({len(accounts)} accounts)'
        elif is_subprime:
            template_key = 'subprime_pattern'
            title_suffix = f'Sub-prime lending pattern ({len(accounts)} accounts)'
        else:
            template_key = 'clean_profile'
            title_suffix = f'Multiple accounts opened ({len(accounts)} accounts)'
        
        # Build aggregated body text
        date_text = f"Accounts were opened on {self._format_date_list(dates)}." if dates else f"{len(accounts)} accounts were opened with this lender."
        
        default_count = sum(1 for acc in accounts if acc.get('default_date', 'N/A') != 'N/A')
        if default_count > 0:
            outcome_text = f" {default_count} of these accounts subsequently defaulted."
        else:
            total_arrears = sum(acc.get('payment_history_summary', {}).get('arrears', 0) for acc in accounts)
            if total_arrears > 0:
                outcome_text = f" The accounts showed payment difficulties across {total_arrears} months."
            else:
                outcome_text = ""
        
        # Get risk summary from first account that has high/moderate risk
        risk_account = next((acc for acc in accounts if self._calculate_risk_level(acc.get('risk_indicators_at_lending', {})) in ['high', 'moderate']), accounts[0])
        risk_summary = self._build_risk_summary(risk_account.get('risk_indicators_at_lending', {}))
        
        body = f"{date_text}{outcome_text} This pattern of repeat lending raises concerns about whether proper affordability checks were conducted. "
        
        if highest_risk in ['high', 'moderate']:
            body += f"The credit file at the time showed {risk_summary}, yet credit continued to be extended."
        
        if is_subprime:
            body += " As a sub-prime lender, there were heightened obligations to ensure responsible lending practices."
        
        return {
            'name': lender,
            'type': account_type,
            'account_numbers': account_numbers,  
            'start_dates': dates,
            'title': title_suffix,
            'body': body.strip()
        }