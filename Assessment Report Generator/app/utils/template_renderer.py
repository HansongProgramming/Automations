from jinja2 import Template
from datetime import datetime
from typing import Dict, Any, List
from app.utils.case_number_manager import CaseNumberManager


class HTMLTemplateRenderer:
    """Renders credit analysis data into HTML template"""
    
    def __init__(self):
        self.template_str = self._get_template()
        self.case_manager = CaseNumberManager()
    
    def _get_template(self) -> str:
        """Returns the HTML template with Jinja2 syntax"""
        return '''<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Affordability Triage Report</title>
    <style>
        @import "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap";

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: ui-sans-serif, system-ui, sans-serif, Apple Color Emoji, Segoe UI Emoji, Segoe UI Symbol, Noto Color Emoji;
            background-color: #ffffff;
            color: #1f2937;
            line-height: 1.6;
        }

        .container {
            max-width: 1024px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }

        .header {
            background: white;
            border-bottom: 2px solid #3b82f6;
            padding: 1.2rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 980px;
            margin: 0 auto;
        }

        .logo-section {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .logo {
            height: 48px;
            width: auto;
        }

        .header-title h1 {
            font-size: 1.5rem;
            font-weight: 700;
            color: #111827;
        }

        .header-title .subtitle {
            font-size: 0.875rem;
            color: #3b82f6;
        }

        .header-title .powered-by {
            font-size: 0.75rem;
            color: #6b7280;
        }

        .header-actions {
            display: flex;
            gap: 0.5rem;
        }

        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 0.375rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }

        .bt~mary {
            background-color: #3b82f6;
            color: white;
        }

        .btn-primary:hover {
            background-color: #2563eb;
        }

        .status-badge {
            text-align: center;
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            font-weight: 700;
            font-size: 1.125rem;
            margin-bottom: 1.5rem;
        }

        .status-strong {
            background-color: #10b981;
            color: white;
        }

        .status-amber {
            background-color: #f59e0b;
            color: white;
        }

        .status-red {
            background-color: #ef4444;
            color: white;
        }

        .card {
            background: #1e293b;
            border-radius: 0.6rem;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 1.5rem;
        }

        .card-header {
            background: #1e293b;
            padding: 1rem 1.5rem;
            border-bottom: 2px solid #3b82f6;
        }

        .card-header h2 {
            font-size: 1.125rem;
            font-weight: 700;
            color: white;
        }

        .card-header p {
            font-size: 0.875rem;
            color: #93c5fd;
            margin-top: 0.25rem;
        }

        .card-body {
            background: #334155;
            padding: 1.5rem;
            color: #f3f4f6;
        }

        .card-description {
            font-size: 0.875rem;
            color: #d1d5db;
            margin-bottom: 1rem;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }

        .info-box {
            background: #475569;
            padding: 0.75rem;
            border-radius: 4px;
            border: 1px solid #64748b;
        }

        .info-label {
            font-size: 0.75rem;
            color: #93c5fd;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
            line-height: 30%;
        }

        .info-value {
            font-weight: 600;
            color: white;
        }

        .indicator-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .indicator {
            border-radius: 0.5rem;
            padding: 1rem;
            border: 2px solid;
            display: flex;
            gap: 0.75rem;
        }

        .indicator-red {
            background: #fee2e2;
            border-color: #fecaca;
        }

        .indicator-green {
            background: #dcfce7;
            border-color: #bbf7d0;
        }

        .indicator-orange {
            background: #ffedd5;
            border-color: #fed7aa;
        }

        .indicator-gray {
            background: white;
            border-color: #e5e7eb;
        }

        .indicator-dot {
            width: 0.5rem;
            height: 0.5rem;
            border-radius: 50%;
            margin-top: 0.25rem;
            flex-shrink: 0;
        }

        .dot-red {
            background: #ef4444;
        }

        .dot-green {
            background: #22c55e;
        }

        .dot-orange {
            background: #f97316;
        }

        .dot-gray {
            background: #9ca3af;
        }

        .indicator-content h3 {
            font-weight: 600;
            color: #111827;
            margin-bottom: 0.25rem;
        }

        .indicator-content p {
            font-size: 0.875rem;
            color: #374151;
        }

        .indicator-content .reason {
            font-weight: 600;
            margin-top: 0.5rem;
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 0.5rem;
        }

        .badge-blue {
            background: #dbeafe;
            color: #1e40af;
        }

        .footer {
            text-align: center;
            padding: 2rem 0;
            border-top: 2px solid #3b82f6;
            color: #3b82f6;
            font-size: 0.875rem;
        }

        @media print {
            .no-print {
                display: none !important;
            }

            .header {
                position: static;
            }
        }

        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }

            .header-content {
                flex-direction: column;
                gap: 1rem;
            }
        }
    </style>
</head>

<body>
    <div class="header">
        <div class="header-content">
            <div class="logo-section">
                <img src="https://raw.githubusercontent.com/HansongProgramming/Automations/main/Assessment%20Report%20Generator/Main%20Logo.png"
                    alt="Company Logo" class="logo">
                <div class="header-title">
                    <h1>Affordability Assessment</h1>
                    <p class="subtitle">Systemize Affordability Analysis</p>
                    <p class="powered-by">Powered by Systemize</p>
                </div>
            </div>
            <div class="header-actions">
                <button class="btn btn-primary no-print" onclick="window.print()">Print</button>
                <button class="btn btn-primary no-print">Export</button>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="card">
            <div class="card-header">
                <h2>Case Information</h2>
                <p>{{ case_number }} | {{ client_info.name }}</p>
            </div>
            <div class="card-body">
                <p class="card-description">Summary of the lending transaction and key dates for reference.</p>
                <div class="grid">
                    <div class="info-box">
                        <p class="info-label">Case ID</p>
                        <p class="info-value">{{ case_number }}</p>
                    </div>
                    <div class="info-box">
                        <p class="info-label">Applicant</p>
                        <p class="info-value">{{ client_info.name }}</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="status-badge {% if traffic_light == 'GREEN' %}status-strong{% elif traffic_light == 'AMBER' %}status-amber{% elif traffic_light == 'RED' %}status-red{% else %}status-strong{% endif %}">
            {% if traffic_light == 'GREEN' %}STRONG{% elif traffic_light == 'AMBER' %}MEDIUM{% elif traffic_light == 'RED' %}WEAK{% else %}{{ traffic_light }}{% endif %} CASE
        </div>

        <div class="card">
            <div class="card-header">
                <h2>Credit File Indicators</h2>
                <p>Analysis of adverse credit indicators found on applicant's credit file</p>
            </div>
            <div class="card-body">
                <div class="indicator-list">
                    <div class="indicator {% if indicators.active_ccj.flagged %}indicator-red{% else %}indicator-gray{% endif %}">
                        <div class="indicator-dot {% if indicators.active_ccj.flagged %}dot-red{% else %}dot-gray{% endif %}"></div>
                        <div class="indicator-content">
                            <h3>Active CCJ</h3>
                            <p>Court judgment against applicant is active and unresolved. Strong indicator of inability to meet financial obligations.</p>
                        </div>
                    </div>

                    <div class="indicator {% if indicators.multiple_ccjs.flagged %}indicator-red{% else %}indicator-gray{% endif %}">
                        <div class="indicator-dot {% if indicators.multiple_ccjs.flagged %}dot-red{% else %}dot-gray{% endif %}"></div>
                        <div class="indicator-content">
                            <h3>Multiple CCJs</h3>
                            <p>Multiple court judgments show pattern of legal debt enforcement. Demonstrates persistent inability to manage credit responsibly.</p>
                        </div>
                    </div>

                    <div class="indicator {% if indicators.active_default.flagged %}indicator-red{% else %}indicator-gray{% endif %}">
                        <div class="indicator-dot {% if indicators.active_default.flagged %}dot-red{% else %}dot-gray{% endif %}"></div>
                        <div class="indicator-content">
                            <h3>Active Default</h3>
                            <p>Current unsettled default on credit account. Applicant is actively failing to meet payment obligations.</p>
                        </div>
                    </div>

                    <div class="indicator {% if indicators.debt_collection.flagged %}indicator-red{% else %}indicator-gray{% endif %}">
                        <div class="indicator-dot {% if indicators.debt_collection.flagged %}dot-red{% else %}dot-gray{% endif %}"></div>
                        <div class="indicator-content">
                            <h3>Debt Collection Account</h3>
                            <p>Account has been passed to debt collection agency (Lowell, Cabot, PRA). Indicates serious payment failure and debt enforcement action.</p>
                        </div>
                    </div>

                    <div class="indicator {% if indicators.ap_marker.flagged %}indicator-red{% else %}indicator-gray{% endif %}">
                        <div class="indicator-dot {% if indicators.ap_marker.flagged %}dot-red{% else %}dot-gray{% endif %}"></div>
                        <div class="indicator-content">
                            <h3>AP Marker</h3>
                            <p>Payment arrangement marker shows applicant negotiated reduced payments. Indicates financial stress and inability to meet original obligations.</p>
                        </div>
                    </div>

                    <div class="indicator {% if indicators.arrears_last_6_months.flagged %}indicator-red{% else %}indicator-gray{% endif %}">
                        <div class="indicator-dot {% if indicators.arrears_last_6_months.flagged %}dot-red{% else %}dot-gray{% endif %}"></div>
                        <div class="indicator-content">
                            <h3>Arrears in Last 6 Months</h3>
                            <p>Recent missed payments within 6 months. Shows ongoing payment difficulties and deteriorating financial position.</p>
                        </div>
                    </div>

                    <div class="indicator {% if indicators.credit_utilisation_over_80.flagged %}indicator-red{% else %}indicator-gray{% endif %}">
                        <div class="indicator-dot {% if indicators.credit_utilisation_over_80.flagged %}dot-red{% else %}dot-gray{% endif %}"></div>
                        <div class="indicator-content">
                            <h3>Credit Utilisation >80%</h3>
                            <p>Applicant using over 80% of available credit. Indicates over-reliance on credit and limited financial buffer.</p>
                        </div>
                    </div>

                    <div class="indicator {% if indicators.rapid_borrowing.flagged %}indicator-red{% else %}indicator-gray{% endif %}">
                        <div class="indicator-dot {% if indicators.rapid_borrowing.flagged %}dot-red{% else %}dot-gray{% endif %}"></div>
                        <div class="indicator-content">
                            <h3>Rapid Borrowing Acceleration</h3>
                            <p>Multiple new credit applications in short period. Suggests applicant seeking additional credit to manage existing debt.</p>
                        </div>
                    </div>

                    <div class="indicator {% if indicators.repeat_lending.flagged %}indicator-red{% else %}indicator-gray{% endif %}">
                        <div class="indicator-dot {% if indicators.repeat_lending.flagged %}dot-red{% else %}dot-gray{% endif %}"></div>
                        <div class="indicator-content">
                            <h3>Repeat Lending</h3>
                            <p>Multiple agreements with same lender or refinancing/top-ups. Pattern suggests lender not reassessing affordability despite worsening profile.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h2>In-Scope: Potential Claims</h2>
                <p>Lenders that can be pursued for irresponsible lending</p>
            </div>
            <div class="card-body">
                <div class="indicator-list">
                    {% for item in claims_analysis.in_scope %}
                    <div class="indicator indicator-green">
                        <div class="indicator-dot dot-green"></div>
                        <div class="indicator-content">
                            <h3>
                                {{ item.name }}
                                <span class="badge badge-blue">{{ item.type }}</span>
                            </h3>
                            <p class="reason">{{ item.title }}</p>
                            <p>{{ item.body }}</p>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h2>Out-of-Scope: Not Defendants</h2>
                <p>Entities that cannot be pursued for irresponsible lending</p>
            </div>
            <div class="card-body">
                <div class="indicator-list">
                    {% for item in claims_analysis.out_of_scope %}
                    <div class="indicator indicator-{{ item.color | default('gray') }}">
                        <div class="indicator-dot dot-{{ item.color | default('gray') }}"></div>
                        <div class="indicator-content">
                            <h3>
                                {{ item.name }}
                                <span class="badge badge-blue">{{ item.type }}</span>
                            </h3>
                            <p class="reason">{{ item.title }}</p>
                            <p>{{ item.body }}</p>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <div class="footer">
            <p> Credit Report Analysis | Systemize</p>
            <p>Generated: {{ current_date }}</p>
        </div>
    </div>
</body>

</html>'''
    
    def render(self, credit_analysis: Dict[str, Any]) -> str:
        """
        Render the HTML template with credit analysis data.
        
        Args:
            credit_analysis: The credit analysis data structure
            
        Returns:
            Rendered HTML string
        """
        template = Template(self.template_str)
        
        # Generate case number
        client_name = credit_analysis.get('client_info', {}).get('name', 'Unknown Client')
        case_number = self.case_manager.generate_case_number(client_name)
        
        # Prepare the context with current date and case number
        context = {
            **credit_analysis,
            'current_date': datetime.now().strftime('%d %b %Y'),
            'case_number': case_number
        }
        
        return template.render(**context)
    
    def render_multiple(self, analysis_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Render multiple credit analyses into HTML.
        
        Args:
            analysis_results: List of analysis results from the /analyze endpoint
            
        Returns:
            List of dicts containing URL, HTML, and any errors
        """
        rendered_results = []
        
        for result in analysis_results:
            if 'error' in result:
                # Pass through errors
                rendered_results.append(result)
            else:
                try:
                    credit_analysis = result.get('credit_analysis', {})
                    html = self.render(credit_analysis)
                    
                    rendered_results.append({
                        'url': result.get('url', 'unknown'),
                        'html': html,
                        'client_name': credit_analysis.get('client_info', {}).get('name', 'Unknown')
                    })
                except Exception as e:
                    rendered_results.append({
                        'url': result.get('url', 'unknown'),
                        'error': f'Template rendering failed: {str(e)}'
                    })
        
        return rendered_results