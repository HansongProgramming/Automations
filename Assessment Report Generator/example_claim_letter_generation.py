"""
Example: Using the Enhanced Claim Letter Generator

This script demonstrates how to use the enhanced claim letter generator
with automatic metric extraction and conditional section removal.
"""

from app.claim_letters.generator import ClaimLetterGenerator
from pathlib import Path
import json


def example_usage():
    """Demonstrate basic usage of the claim letter generator."""
    
    # Path to your template
    template_path = 'app/templates/Affordability_Letter_of_Claim_.docx'
    
    # Initialize generator
    generator = ClaimLetterGenerator(template_path)
    
    # Example 1: Generate from JSON file
    print("=" * 70)
    print("Example 1: Generate letters from JSON file")
    print("=" * 70)
    
    json_file = 'credit_analysis_output.json'
    output_dir = 'generated_letters'
    
    if Path(json_file).exists():
        stats = generator.generate_all(
            json_input=json_file,
            output_dir=output_dir,
            debug=True  # Shows detailed metric extraction
        )
        
        print(f"\n✓ Generated {stats['total_letters']} letters from {stats['total_reports']} reports")
        print(f"✓ Output directory: {output_dir}")
    else:
        print(f"⚠ JSON file not found: {json_file}")
    
    # Example 2: Test metric extraction with sample data
    print("\n" + "=" * 70)
    print("Example 2: Extract metrics from credit data")
    print("=" * 70)
    
    sample_credit_data = {
        'credit_analysis': {
            'client_info': {
                'name': 'John Smith',
                'address': '123 Main Street\nLondon\nSW1A 1AA'
            },
            'claims_analysis': {
                'in_scope': [
                    {
                        'name': 'VANQUIS BANK',
                        'type': 'Credit Card',
                        'account_number': '12345678',
                        'start_date': '01/01/2020'
                    }
                ],
                'out_of_scope': [],
                'credit_timeline': {
                    'ccjs': [
                        {'date': '2023-01-15', 'amount': 500, 'court_name': 'County Court'}
                    ],
                    'defaults': [
                        {'date': '15/06/2023', 'account': '12345', 'lender': 'Test Lender'}
                    ],
                    'arrears_pattern': [
                        {'account': '12345', 'lender': 'Test Lender', 'arrears_months': 6}
                    ]
                }
            },
            'indicators': {
                'active_ccj': {'flagged': True, 'points': 40},
                'active_default': {'flagged': True, 'points': 30},
                'arrears_last_6_months': {'flagged': True, 'points': 20},
                'ap_marker': {'flagged': False, 'points': 0}
            }
        }
    }
    
    # Extract metrics
    metrics = generator.extract_claim_metrics(sample_credit_data)
    
    print("\nExtracted Metrics:")
    print(f"  CCJs: {metrics['total_ccjs']} (Has data: {metrics['has_ccjs']})")
    print(f"  Defaults (12 months): {metrics['totalDefaults12Months']} (Has data: {metrics['has_defaults']})")
    print(f"  Arrears (12 months): {metrics['totalArrears12Months']} (Has data: {metrics['has_arrears']})")
    print(f"  AP Marker: {metrics['has_ap_marker']}")
    print(f"  Gambling data: {metrics['has_gambling']} (requires bank statements)")
    print(f"  Overdraft data: {metrics['has_overdraft']} (requires bank statements)")
    
    print("\nConditional Sections Status:")
    sections = {
        '22.1 Additional Loan Commitments': metrics['has_loan_commitments'],
        '22.2 Personal Borrowing (P2P)': metrics['has_peer_to_peer'],
        '23.1 Personal Insolvency/Debt Management': metrics['has_ap_marker'],
        '23.2 County Court Judgments': metrics['has_ccjs'],
        '23.3 Defaults': metrics['has_defaults'],
        '23.4 Arrears': metrics['has_arrears'],
        '23.5 Gambling': metrics['has_gambling'],
        '23.6 Overdraft Usage': metrics['has_overdraft']
    }
    
    for section, has_data in sections.items():
        status = "✓ INCLUDED" if has_data else "✗ REMOVED"
        print(f"  {status}: {section}")


def example_custom_usage():
    """
    Example of processing specific credit data with custom settings.
    """
    print("\n" + "=" * 70)
    print("Example 3: Custom Processing")
    print("=" * 70)
    
    # You can also process individual reports
    template_path = 'app/templates/Affordability_Letter_of_Claim_.docx'
    generator = ClaimLetterGenerator(template_path)
    
    # Load your credit report data
    credit_data = {...}  # Your credit analysis JSON
    
    # Process just this report
    output_dir = 'custom_letters'
    letters_generated = generator.process_credit_report(
        report_data=credit_data,
        output_dir=output_dir,
        debug=True
    )
    
    print(f"Generated {letters_generated} letter(s)")


if __name__ == '__main__':
    print("Enhanced Claim Letter Generator - Examples\n")
    example_usage()
    
    print("\n" + "=" * 70)
    print("For more information, see CLAIM_LETTER_GENERATOR_README.md")
    print("=" * 70)
