"""
Test script for Credit Report Analysis + PDF + Claim Letters
Run this after setting up all endpoints
"""
import requests
import json
import base64
from pathlib import Path
import time
import zipfile
from io import BytesIO
import os
import shutil

from app import claim_letters
# Your test URLs - Add multiple URLs to test batch processing
TEST_URLS = [
    "https://api.boshhhfintech.com/File/CreditReport/95d1ce7e-2c3c-49d5-a303-6a4727f91005?Auth=af26383640b084af4d2895307480ed795c334405b786d7419d78be541fcc0656",
    # Add more URLs here to test multiple cases:
    # "https://api.boshhhfintech.com/File/CreditReport/ANOTHER-ID?Auth=...",
    # "https://api.boshhhfintech.com/File/CreditReport/THIRD-ID?Auth=...",
]

BASE_URL = "http://localhost:8000"


def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title):
    """Print a section divider"""
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")


def test_health():
    """Test the health endpoint"""
    print_header("🏥 HEALTH CHECK")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ Server is healthy")
        print(f"   Status: {result.get('status')}")
        print(f"   Service: {result.get('service')}")
        return True
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        print(f"\n💡 Make sure server is running:")
        print(f"   uvicorn app.main:app --reload")
        return False


def test_analyze():
    """Test the basic /analyze endpoint"""
    print_header("📊 TEST 1: BASIC ANALYSIS (/analyze)")
    
    print(f"\n📡 Analyzing {len(TEST_URLS)} credit report(s)...")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/analyze",
            json={"urls": TEST_URLS},
            timeout=300
        )
        response.raise_for_status()
        
        elapsed = time.time() - start_time
        results = response.json()
        
        print(f"✅ Analysis complete in {elapsed:.2f}s")
        print(f"   Received {len(results)} result(s)")
        
        # Count in-scope lenders
        total_in_scope = 0
        for result in results:
            if 'error' not in result:
                client = result['credit_analysis']['client_info']['name']
                in_scope = len(result['credit_analysis']['claims_analysis']['in_scope'])
                total_in_scope += in_scope
                print(f"   • {client}: {in_scope} in-scope lender(s)")
        
        print(f"\n📋 Total in-scope lenders: {total_in_scope}")
        
        # Save analysis JSON for later tests
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        
        with open(output_dir / "analysis_results.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"💾 Saved to: {output_dir / 'analysis_results.json'}")
        
        return results
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_pdf_generation():
    """Test the /analyze-pdf endpoint"""
    print_header("📄 TEST 2: PDF GENERATION (/analyze-pdf)")
    
    print(f"\n📡 Generating PDF reports for {len(TEST_URLS)} report(s)...")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/analyze-pdf",
            json={"urls": TEST_URLS},
            timeout=300
        )
        response.raise_for_status()
        
        elapsed = time.time() - start_time
        results = response.json()
        
        print(f"✅ PDF generation complete in {elapsed:.2f}s")
        
        # Save PDFs
        output_dir = Path("pdf_reports")
        output_dir.mkdir(exist_ok=True)
        
        success_count = 0
        total_size = 0
        
        for result in results:
            if 'pdf_base64' in result:
                client_name = result['client_name']
                filename = result['filename']
                
                # Decode and save
                pdf_bytes = base64.b64decode(result['pdf_base64'])
                pdf_path = output_dir / filename
                
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                
                file_size = len(pdf_bytes)
                total_size += file_size
                success_count += 1
                
                print(f"   ✅ {client_name}: {file_size/1024:.1f} KB")
            elif 'error' in result:
                print(f"   ❌ Error: {result['error']}")
        
        print(f"\n📊 Summary:")
        print(f"   • PDFs generated: {success_count}")
        print(f"   • Total size: {total_size/1024:.1f} KB")
        print(f"   • Saved to: {output_dir.absolute()}")
        
        return True
        
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_html_generation():
    """Test the /analyze-html endpoint"""
    print_header("🌐 TEST 3: HTML REPORT GENERATION (/analyze-html)")
    
    print(f"\n📡 Generating HTML reports for {len(TEST_URLS)} report(s)...")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/analyze-html",
            json={"urls": TEST_URLS},
            timeout=300
        )
        response.raise_for_status()
        
        elapsed = time.time() - start_time
        results = response.json()
        
        print(f"✅ HTML generation complete in {elapsed:.2f}s")
        
        # Save HTML files
        output_dir = Path("html_reports")
        output_dir.mkdir(exist_ok=True)
        
        success_count = 0
        total_size = 0
        
        for result in results:
            if 'html' in result and 'error' not in result:
                client_name = result.get('client_name', 'Unknown')
                html_content = result['html']
                
                # Create filename
                safe_name = client_name.replace(' ', '_').replace('/', '_')
                filename = f"{safe_name}_report.html"
                html_path = output_dir / filename
                
                # Save HTML
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                file_size = len(html_content)
                total_size += file_size
                success_count += 1
                
                print(f"   ✅ {client_name}: {file_size/1024:.1f} KB")
            elif 'error' in result:
                print(f"   ❌ Error: {result['error']}")
        
        print(f"\n📊 Summary:")
        print(f"   • HTML reports generated: {success_count}")
        print(f"   • Total size: {total_size/1024:.1f} KB")
        print(f"   • Saved to: {output_dir.absolute()}")
        
        return True
        
    except Exception as e:
        print(f"❌ HTML generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_claim_letters(analysis_results=None):
    """Test the /generate-claim-letters endpoint"""
    print_header("📝 TEST 4: CLAIM LETTER GENERATION (/generate-claim-letters)")
    
    # Use provided analysis or load from file
    if analysis_results is None:
        print("📂 Loading analysis from file...")
        try:
            with open("test_output/analysis_results.json", 'r') as f:
                analysis_results = json.load(f)
        except FileNotFoundError:
            print("❌ No analysis results found. Run test_analyze() first.")
            return False
    
    print(f"\n📡 Generating claim letters for {len(analysis_results)} report(s)...")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/generate-claim-letters",
            json=analysis_results,
            timeout=300
        )
        response.raise_for_status()
        
        elapsed = time.time() - start_time
        
        print(f"✅ Letter generation complete in {elapsed:.2f}s")
        
        # Save ZIP file
        output_dir = Path("claim_letters")
        output_dir.mkdir(exist_ok=True)
        
        zip_path = output_dir / "claim_letters.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        # Extract and list contents
        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_list = zf.namelist()
            print(f"\n📦 ZIP Contents ({len(file_list)} files):")
            
            for filename in file_list:
                file_info = zf.getinfo(filename)
                print(f"   • {filename} ({file_info.file_size/1024:.1f} KB)")
            
            # Extract all files
            zf.extractall(output_dir)
        
        print(f"\n💾 Saved to: {output_dir.absolute()}")
        print(f"   • ZIP file: {zip_path.name}")
        print(f"   • Extracted: {len(file_list)} letter(s)")
        
        return True
        
    except requests.exceptions.HTTPException as e:
        print(f"❌ Letter generation failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Letter generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_combined_endpoint():
    """Test the /analyze-pdf-and-letters combined endpoint"""
    print_header("🚀 TEST 5: COMBINED ENDPOINT (/analyze-pdf-and-letters)")
    
    print(f"\n📡 Running combined analysis for {len(TEST_URLS)} report(s)...")
    print("⏳ This will:")
    print("   1. Fetch and analyze credit reports")
    print("   2. Generate PDF reports")
    print("   3. Generate claim letters")
    print("   4. Package everything into one ZIP")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/analyze-pdf-and-letters",
            json={"urls": TEST_URLS},
            timeout=600  # 10 minutes for everything
        )
        response.raise_for_status()
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ Combined generation complete in {elapsed:.2f}s")
        
        # Save ZIP file
        output_dir = Path("complete_package")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        zip_path = output_dir / f"analysis_complete_{timestamp}.zip"
        
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        print(f"💾 Saved ZIP: {zip_path}")
        
        # Extract and analyze contents
        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_list = zf.namelist()
            
            # Separate by type
            pdf_files = [f for f in file_list if f.startswith('pdfs/')]
            letter_files = [f for f in file_list if f.startswith('claim_letters/')]
            
            print(f"\n📦 Package Contents:")
            print(f"   • Total files: {len(file_list)}")
            print(f"   • PDF reports: {len(pdf_files)}")
            print(f"   • Claim letters: {len(letter_files)}")
            
            # Show PDFs
            if pdf_files:
                print(f"\n📄 PDF Reports:")
                for pdf in pdf_files:
                    file_info = zf.getinfo(pdf)
                    print(f"   • {pdf} ({file_info.file_size/1024:.1f} KB)")
            
            # Show letters
            if letter_files:
                print(f"\n📝 Claim Letters:")
                for letter in letter_files:
                    file_info = zf.getinfo(letter)
                    print(f"   • {letter} ({file_info.file_size/1024:.1f} KB)")
            
            # Extract all
            extract_dir = output_dir / f"extracted_{timestamp}"
            zf.extractall(extract_dir)
            print(f"\n📂 Extracted to: {extract_dir.absolute()}")
        
        # Calculate totals
        total_size = sum(zf.getinfo(f).file_size for f in file_list)
        print(f"\n📊 Statistics:")
        print(f"   • Processing time: {elapsed:.2f}s")
        print(f"   • Total size: {total_size/1024:.1f} KB ({total_size/1024/1024:.2f} MB)")
        print(f"   • Average per file: {total_size/len(file_list)/1024:.1f} KB")
        
        return True
        
    except requests.exceptions.Timeout:
        print(f"❌ Request timeout - processing took too long")
        return False
    except Exception as e:
        print(f"❌ Combined endpoint failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_quick():
    """Quick test with just one URL"""
    print_header("⚡ QUICK TEST: Single Report (All Features)")
    
    print(f"\n📡 Testing with single URL...")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/analyze-pdf-and-letters",
            json={"urls": [TEST_URLS[0]]},
            timeout=120
        )
        response.raise_for_status()
        
        elapsed = time.time() - start_time
        
        # Save to quick test folder
        output_dir = Path("quick_test")
        output_dir.mkdir(exist_ok=True)
        
        zip_path = output_dir / "quick_test.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(output_dir)
            file_list = zf.namelist()
        
        print(f"✅ Quick test successful!")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Files: {len(file_list)}")
        print(f"   Location: {output_dir.absolute()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False


def run_performance_benchmark():
    """Benchmark all endpoints"""
    print_header("⏱️  PERFORMANCE BENCHMARK")
    
    results = {}
    
    print("\n🏃 Running benchmarks with single URL...")
    
    # Test /analyze
    print_section("/analyze")
    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/analyze", json={"urls": [TEST_URLS[0]]}, timeout=120)
        response.raise_for_status()
        results['analyze'] = time.time() - start
        print(f"✅ {results['analyze']:.2f}s")
    except Exception as e:
        print(f"❌ Failed: {e}")
        results['analyze'] = None
    
    # Test /analyze-pdf
    print_section("/analyze-pdf")
    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/analyze-pdf", json={"urls": [TEST_URLS[0]]}, timeout=120)
        response.raise_for_status()
        results['analyze-pdf'] = time.time() - start
        print(f"✅ {results['analyze-pdf']:.2f}s")
    except Exception as e:
        print(f"❌ Failed: {e}")
        results['analyze-pdf'] = None
    
    # Test /analyze-pdf-and-letters
    print_section("/analyze-pdf-and-letters")
    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/analyze-pdf-and-letters", json={"urls": [TEST_URLS[0]]}, timeout=120)
        response.raise_for_status()
        results['combined'] = time.time() - start
        print(f"✅ {results['combined']:.2f}s")
    except Exception as e:
        print(f"❌ Failed: {e}")
        results['combined'] = None
    
    # Summary
    print_section("Summary")
    if all(results.values()):
        print(f"Endpoint Performance (single report):")
        print(f"  • Analysis only:    {results['analyze']:.2f}s")
        print(f"  • Analysis + PDF:   {results['analyze-pdf']:.2f}s")
        print(f"  • Full (+ Letters): {results['combined']:.2f}s")
        print(f"\nOverheads:")
        print(f"  • PDF overhead:     +{results['analyze-pdf'] - results['analyze']:.2f}s")
        print(f"  • Letters overhead: +{results['combined'] - results['analyze-pdf']:.2f}s")
    else:
        print("⚠️  Some benchmarks failed")


def run_all_tests():
    """Run the complete test suite"""
    print("\n" + "=" * 70)
    print("  🧪 CREDIT REPORT ANALYZER - COMPLETE TEST SUITE")
    print("=" * 70)
    print(f"\nTesting server at: {BASE_URL}")
    print(f"Test URLs: {len(TEST_URLS)}")
    
    # Track results
    test_results = {}
    
    # 1. Health check
    if not test_health():
        print("\n❌ Server is not healthy. Stopping tests.")
        return
    
    # 2. Basic analysis
    analysis_results = test_analyze()
    test_results['analyze'] = analysis_results is not None
    
    # 3. PDF generation
    test_results['pdf'] = test_pdf_generation()
    
    # 4. HTML generation
    test_results['html'] = test_html_generation()
    
    # 5. Claim letters (using analysis from step 2)
    test_results['letters'] = test_claim_letters(analysis_results)
    
    # 6. Combined endpoint
    test_results['combined'] = test_combined_endpoint()
    
    # Final summary
    print_header("📊 TEST SUMMARY")
    
    passed = sum(1 for v in test_results.values() if v)
    total = len(test_results)
    
    print(f"\nResults: {passed}/{total} tests passed\n")
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {test_name}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        print("\n💡 Output locations:")
        print("   • test_output/       - Analysis JSON")
        print("   • html_reports/      - HTML reports")
        print("   • pdf_reports/       - PDF reports")
        print("   • claim_letters/     - Individual claim letters")
        print("   • complete_package/  - Combined packages")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    print("\n" + "=" * 70)


def interactive_menu():
    """Interactive test menu"""
    while True:
        print("\n" + "=" * 70)
        print("  🧪 CREDIT REPORT ANALYZER - TEST MENU")
        print("=" * 70)
        print("\n  Select a test to run:")
        print("\n  1. Quick Test (Single Report - All Features)")
        print("  2. Test Analysis Only (/analyze)")
        print("  3. Test HTML Generation (/analyze-html)")
        print("  4. Test PDF Generation (/analyze-pdf)")
        print("  5. Test Claim Letters (/generate-claim-letters)")
        print("  6. Test Combined Endpoint (/analyze-pdf-and-letters)")
        print("  7. Run Complete Test Suite")
        print("  8. Performance Benchmark")
        print("  9. Health Check")
        print("  0. Exit")
        
        choice = input("\n  Enter choice (0-9): ").strip()
        
        if choice == '0':
            print("\n👋 Goodbye!")
            break
        elif choice == '1':
            test_single_quick()
        elif choice == '2':
            test_analyze()
        elif choice == '3':
            test_html_generation()
        elif choice == '4':
            test_pdf_generation()
        elif choice == '5':
            test_claim_letters()
        elif choice == '6':
            test_combined_endpoint()
        elif choice == '7':
            run_all_tests()
        elif choice == '8':
            run_performance_benchmark()
        elif choice == '9':
            test_health()
        else:
            print("\n❌ Invalid choice. Please try again.")
        
        input("\n  Press Enter to continue...")

def cleanup_outputs():
    folders = [
        "test_output",
        "claim_letters",
        "complete_package",
        "pdf_reports",
        "html_reports",
    ]

    for folder in folders:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"🧹 Removed folder: {folder}")
            except PermissionError as e:
                print(f"❌ Permission denied removing {folder}: {e}")
        else:
            print(f"ℹ️ Folder not found: {folder}")

if __name__ == "__main__":
    import sys

    cleanup_outputs()
    
    # Check if interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == '--menu':
        interactive_menu()
        cleanup_outputs()
    elif len(sys.argv) > 1 and sys.argv[1] == '--quick':
        test_single_quick()
    elif len(sys.argv) > 1 and sys.argv[1] == '--benchmark':
        run_performance_benchmark()
    elif sys.argv[1] == '--analyze':
        test_analyze()
    elif sys.argv[1] == '--pdf':
        test_pdf_generation()
    elif sys.argv[1] == '--html':
        test_html_generation()
    elif sys.argv[1] == '--letters':
        test_claim_letters()
    elif sys.argv[1] == '--combined':
        test_combined_endpoint()
    else:
        run_all_tests()

    print("\n✨ Testing complete!")