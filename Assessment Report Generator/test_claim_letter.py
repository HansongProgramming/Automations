"""Test the enhanced claim letter generator with sample data"""
from app.claim_letters.generator import ClaimLetterGenerator
import json
from pathlib import Path

# Load the sample data
with open('test_output/analysis_results.json', 'r') as f:
    data = json.load(f)

# Initialize generator
template_path = 'app/templates/Affordability_Letter_of_Claim_.docx'
if not Path(template_path).exists():
    print(f"❌ Template not found: {template_path}")
    exit(1)

generator = ClaimLetterGenerator(template_path)

# Test metric extraction
print("="*70)
print("METRIC EXTRACTION TEST")
print("="*70)
metrics = generator.extract_claim_metrics(data[0])

print(f"\nExtracted metrics for {data[0]['credit_analysis']['client_info']['name']}:")
print(f"  CCJs: {metrics['has_ccjs']} (Total: {metrics['total_ccjs']})")
print(f"  Defaults (12m): {metrics['has_defaults']} (Total: {metrics['totalDefaults12Months']})")
print(f"  Arrears (12m): {metrics['has_arrears']} (Total: {metrics['totalArrears12Months']})")
print(f"  AP Marker: {metrics['has_ap_marker']}")
print(f"  Loan Commitments: {metrics['has_loan_commitments']}")
print(f"  Peer-to-Peer: {metrics['has_peer_to_peer']}")
print(f"  Gambling: {metrics['has_gambling']}")
print(f"  Overdraft: {metrics['has_overdraft']}")

print("\n" + "="*70)
print("CONDITIONAL SECTIONS STATUS")
print("="*70)
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
    status = "✓ KEEP (has data)" if has_data else "✗ REMOVE (no data)"
    print(f"  {status}: {section}")

# Generate letters
print("\n" + "="*70)
print("GENERATING LETTERS")
print("="*70)

output_dir = 'test_claim_letters'
stats = generator.generate_all(
    json_input='test_output/analysis_results.json',
    output_dir=output_dir,
    debug=True
)

print(f"\n✓ Test completed!")
print(f"  Generated: {stats['total_letters']} letters")
print(f"  Output directory: {output_dir}")
print(f"\nPlease check the generated documents to verify sections were removed correctly.")
