"""
Enhanced Letter of Claim Generator
Supports multiple JSON inputs, batch processing, and integration with existing systems
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from docx import Document
from typing import List, Dict, Any, Optional
import argparse


# Try to import config, fall back to defaults if not available
try:
    from config_claim_letters import (
        BANK_DETAILS, 
        DEFAULT_OUTPUT_DIR, 
        DEFENDANT_ADDRESSES,
        AGREEMENT_TYPES
    )
except ImportError:
    BANK_DETAILS = {
        'bank_name': 'TBC',
        'account_name': 'TBC',
        'account_number': 'TBC',
        'sort_code': 'TBC'
    }
    DEFAULT_OUTPUT_DIR = 'claim_letters'
    DEFENDANT_ADDRESSES = {}
    AGREEMENT_TYPES = {}


class ClaimLetterGenerator:
    """Generator for Letters of Claim from credit report JSON data."""
    
    def __init__(self, template_path: str, bank_details: Optional[Dict[str, str]] = None):
        """
        Initialize the generator.
        
        Args:
            template_path: Path to the Word template file
            bank_details: Optional override for bank details
        """
        self.template_path = template_path
        self.bank_details = bank_details or BANK_DETAILS
        self.stats = {
            'total_reports': 0,
            'total_letters': 0,
            'by_client': {}
        }
    
    @staticmethod
    def parse_client_name(full_name: str) -> Dict[str, str]:
        """Parse full name into first name and surname."""
        parts = full_name.strip().split()
        if len(parts) >= 2:
            return {
                'first_name': parts[0],
                'surname': ' '.join(parts[1:])
            }
        return {
            'first_name': full_name,
            'surname': ''
        }
    
    @staticmethod
    def parse_address(address: str) -> Dict[str, str]:
        """Parse address into components."""
        lines = [line.strip() for line in address.split('\n') if line.strip()]
        
        postcode = ''
        address_lines = lines.copy()
        
        # Extract postcode (typically last line with numbers)
        if lines:
            last_line = lines[-1]
            if any(char.isdigit() for char in last_line) and len(last_line) <= 10:
                postcode = last_line
                address_lines = lines[:-1]
        
        # Pad to 3 lines
        while len(address_lines) < 3:
            address_lines.append('')
        
        return {
            'line1': address_lines[0] if len(address_lines) > 0 else '',
            'line2': address_lines[1] if len(address_lines) > 1 else '',
            'line3': address_lines[2] if len(address_lines) > 2 else '',
            'postcode': postcode if postcode else (address_lines[-1] if address_lines else '')
        }
    
    @staticmethod
    def replace_in_paragraph(paragraph, old_text: str, new_text: str):
        """Replace text in a paragraph while preserving formatting."""
        if old_text in paragraph.text:
            full_text = ''.join([run.text for run in paragraph.runs])
            
            if old_text in full_text:
                new_text_str = str(new_text) if new_text is not None else ''
                
                for i, run in enumerate(paragraph.runs):
                    if i == 0:
                        run.text = full_text.replace(old_text, new_text_str)
                    else:
                        run.text = ''
    
    @staticmethod
    def replace_in_table(table, old_text: str, new_text: str):
        """Replace text in a table."""
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    ClaimLetterGenerator.replace_in_paragraph(paragraph, old_text, new_text)
    
    def replace_placeholders(self, doc: Document, replacements: Dict[str, str]):
        """Replace all placeholders in the document."""
        # Replace in paragraphs
        for paragraph in doc.paragraphs:
            for old_text, new_text in replacements.items():
                self.replace_in_paragraph(paragraph, old_text, new_text)
        
        # Replace in tables
        for table in doc.tables:
            for old_text, new_text in replacements.items():
                self.replace_in_table(table, old_text, new_text)
        
        # Replace in headers and footers
        for section in doc.sections:
            for header in [section.header, section.first_page_header, section.even_page_header]:
                if header:
                    for paragraph in header.paragraphs:
                        for old_text, new_text in replacements.items():
                            self.replace_in_paragraph(paragraph, old_text, new_text)
                    for table in header.tables:
                        for old_text, new_text in replacements.items():
                            self.replace_in_table(table, old_text, new_text)
            
            for footer in [section.footer, section.first_page_footer, section.even_page_footer]:
                if footer:
                    for paragraph in footer.paragraphs:
                        for old_text, new_text in replacements.items():
                            self.replace_in_paragraph(paragraph, old_text, new_text)
                    for table in footer.tables:
                        for old_text, new_text in replacements.items():
                            self.replace_in_table(table, old_text, new_text)
    
    def generate_letter(self, output_path: str, credit_data: Dict[str, Any], 
                       in_scope_item: Dict[str, Any]) -> bool:
        """
        Generate a single letter of claim.
        
        Args:
            output_path: Where to save the generated letter
            credit_data: Full credit report data
            in_scope_item: The specific in-scope lender data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load template
            doc = Document(self.template_path)
            
            # Parse client information
            client_info = credit_data['credit_analysis']['client_info']
            client_name_parts = self.parse_client_name(client_info['name'])
            client_address = self.parse_address(client_info['address'])
            
            # Get defendant address
            defendant_name = in_scope_item['name']
            defendant_address = DEFENDANT_ADDRESSES.get(defendant_name, 'Address TBC')
            
            # Get current date
            current_date = datetime.now().strftime('%d/%m/%Y')
            
            # Prepare replacements
            replacements = {
                '{Date}': current_date,
                '{Defendant Name}': defendant_name,
                '{Defendant Address}': defendant_address,
                '{Client First Name}': client_name_parts['first_name'],
                '{Client Surname}': client_name_parts['surname'],
                '{Address Line 1}': client_address['line1'],
                '{Address Line 2}': client_address['line2'],
                '{Address Line 3}': client_address['line3'],
                '{Postcode}': client_address['postcode'],
                '{Bank}': self.bank_details.get('bank_name', 'TBC'),
                '{Account Name}': self.bank_details.get('account_name', 'TBC'),
                '{Account Number}': self.bank_details.get('account_number', 'TBC'),
                '{Sort Code}': self.bank_details.get('sort_code', 'TBC'),
                '{Agreement Number}': 'TBC',
                '{Agreement Start Date}': 'TBC',
                '{Report Received Date}': current_date,
                '{Report Outcome}': 'unaffordable',
            }
            
            # Replace all placeholders
            self.replace_placeholders(doc, replacements)
            
            # Save document
            doc.save(output_path)
            return True
            
        except Exception as e:
            print(f"✗ Error generating {output_path}: {str(e)}")
            return False
    
    def process_credit_report(self, report_data: Dict[str, Any], output_dir: str) -> int:
        """
        Process a single credit report and generate letters for all in-scope lenders.
        
        Args:
            report_data: Credit report JSON data
            output_dir: Directory to save generated letters
            
        Returns:
            int: Number of letters generated
        """
        credit_analysis = report_data.get('credit_analysis', {})
        client_info = credit_analysis.get('client_info', {})
        client_name = client_info.get('name', 'Unknown_Client')
        
        # Clean client name for filename
        safe_client_name = ''.join(c if c.isalnum() or c in [' ', '_'] else '_' for c in client_name)
        safe_client_name = safe_client_name.replace(' ', '_')
        
        claims_analysis = credit_analysis.get('claims_analysis', {})
        in_scope_lenders = claims_analysis.get('in_scope', [])
        
        letters_generated = 0
        
        if in_scope_lenders:
            print(f"\n📄 {client_name}: {len(in_scope_lenders)} in-scope lender(s)")
            
            for lender in in_scope_lenders:
                lender_name = lender.get('name', 'Unknown_Lender')
                safe_lender_name = ''.join(c if c.isalnum() or c in [' ', '_'] else '_' for c in lender_name)
                safe_lender_name = safe_lender_name.replace(' ', '_')
                
                output_filename = f"{safe_client_name}_{safe_lender_name}_LOC.docx"
                output_path = os.path.join(output_dir, output_filename)
                
                if self.generate_letter(output_path, report_data, lender):
                    print(f"  ✓ {lender_name}")
                    letters_generated += 1
                else:
                    print(f"  ✗ {lender_name} - Failed")
        else:
            print(f"\n⚠ {client_name}: No in-scope lenders found")
        
        # Update stats
        self.stats['by_client'][client_name] = letters_generated
        
        return letters_generated
    
    def load_json_data(self, json_input: str) -> List[Dict[str, Any]]:
        """
        Load JSON data from file, directory, or string.
        
        Args:
            json_input: Path to file/directory or JSON string
            
        Returns:
            List of credit report dictionaries
        """
        json_files = []
        json_path = Path(json_input)
        
        if json_path.is_file() and json_path.suffix == '.json':
            with open(json_path, 'r') as f:
                data = json.load(f)
                json_files = data if isinstance(data, list) else [data]
        elif json_path.is_dir():
            for file_path in sorted(json_path.glob('*.json')):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        json_files.extend(data)
                    else:
                        json_files.append(data)
        else:
            try:
                data = json.loads(json_input)
                json_files = data if isinstance(data, list) else [data]
            except:
                raise ValueError(f"Invalid JSON input: {json_input}")
        
        return json_files
    
    def generate_all(self, json_input: str, output_dir: str) -> Dict[str, Any]:
        """
        Generate letters for all credit reports in the input.
        
        Args:
            json_input: Path to JSON file/directory or JSON string
            output_dir: Directory to save generated letters
            
        Returns:
            Dictionary with generation statistics
        """
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Load data
        print("📂 Loading credit report data...")
        credit_reports = self.load_json_data(json_input)
        self.stats['total_reports'] = len(credit_reports)
        print(f"   Found {len(credit_reports)} credit report(s)\n")
        
        # Process each report
        for report_data in credit_reports:
            letters_count = self.process_credit_report(report_data, output_dir)
            self.stats['total_letters'] += letters_count
        
        # Print summary
        self.print_summary(output_dir)
        
        return self.stats
    
    def print_summary(self, output_dir: str):
        """Print generation summary."""
        print(f"\n{'='*70}")
        print(f"📊 GENERATION SUMMARY")
        print(f"{'='*70}")
        print(f"Total Reports Processed: {self.stats['total_reports']}")
        print(f"Total Letters Generated: {self.stats['total_letters']}")
        print(f"Output Directory: {output_dir}")
        print(f"{'='*70}\n")


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Generate Letters of Claim for in-scope lenders from credit report JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single JSON file
  python generate_claim_letters_v2.py data.json
  
  # Process all JSON files in a directory
  python generate_claim_letters_v2.py ./json_files/ -o ./letters
  
  # Specify custom template
  python generate_claim_letters_v2.py data.json -t custom_template.docx
  
  # Override bank details
  python generate_claim_letters_v2.py data.json --bank-name "My Bank" --account-number "12345678"
        """
    )
    
    parser.add_argument('json_input', help='Path to JSON file, directory, or JSON string')
    parser.add_argument('-o', '--output', default=DEFAULT_OUTPUT_DIR,
                       help=f'Output directory (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('-t', '--template', 
                       default='/mnt/user-data/uploads/Affordability_Letter_of_Claim_.docx',
                       help='Path to Word template')
    parser.add_argument('--bank-name', help='Override bank name')
    parser.add_argument('--account-name', help='Override account name')
    parser.add_argument('--account-number', help='Override account number')
    parser.add_argument('--sort-code', help='Override sort code')
    
    args = parser.parse_args()
    
    # Override bank details if provided
    bank_details = BANK_DETAILS.copy()
    if args.bank_name:
        bank_details['bank_name'] = args.bank_name
    if args.account_name:
        bank_details['account_name'] = args.account_name
    if args.account_number:
        bank_details['account_number'] = args.account_number
    if args.sort_code:
        bank_details['sort_code'] = args.sort_code
    
    # Generate letters
    generator = ClaimLetterGenerator(args.template, bank_details)
    generator.generate_all(args.json_input, args.output)


if __name__ == '__main__':
    main()