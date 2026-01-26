"""
Test script for HTML report generation
Run this after setting up the new endpoint
"""
import requests
import json
from pathlib import Path

# Your test URLs
TEST_URLS = [
    "https://api.boshhhfintech.com/File/CreditReport/95d1ce7e-2c3c-49d5-a303-6a4727f91005?Auth=af26383640b084af4d2895307480ed795c334405b786d7419d78be541fcc0656",
    "https://api.boshhhfintech.com/File/CreditReport/e5f86646-9227-4f4e-839e-5a3437b36a45?Auth=72372a1d2fb8b8e5c78b3d4096a53b853dc22422676f789fc888986b82847cf1",
    "https://api.boshhhfintech.com/File/CreditReport/70f05ac1-4806-4d37-afed-52630f845d65?Auth=ce39264e377782c82ed70d69d405eea6e9471c679bb18cbf814f5db483ada838",
]

def test_pdf_endpoint():
    """Test the /analyze-pdf endpoint"""
    
    print("🚀 Testing PDF Report Generation")
    print("=" * 60)
    
    # Create output directory
    output_dir = Path("pdf_reports")
    output_dir.mkdir(exist_ok=True)
    
    # Make request
    print(f"\n📡 Sending request for {len(TEST_URLS)} PDF reports...")
    print("⏳ This may take a while (rendering + PDF conversion)...")
    
    try:
        response = requests.post(
            "http://localhost:8000/analyze-pdf",
            json={"urls": TEST_URLS},
            timeout=600  # 10 minutes timeout (PDF generation is slower)
        )
        response.raise_for_status()
        
        results = response.json()
        
        print(f"✅ Received {len(results)} results\n")
        
        # Process each result
        success_count = 0
        error_count = 0
        total_size = 0
        
        for i, result in enumerate(results, 1):
            print(f"\n📄 Report {i}/{len(results)}")
            print("-" * 60)
            
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
                print(f"   URL: {result.get('url', 'unknown')}")
                error_count += 1
                
            elif 'pdf_base64' in result:
                client_name = result.get('client_name', f'unknown_{i}')
                filename = result.get('filename', f'{client_name}.pdf')
                
                # Decode base64 and save PDF
                pdf_bytes = base64.b64decode(result['pdf_base64'])
                pdf_path = output_dir / filename
                
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                
                file_size = len(pdf_bytes)
                total_size += file_size
                
                print(f"✅ Client: {client_name}")
                print(f"   Saved: {pdf_path}")
                print(f"   Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
                success_count += 1
            
            else:
                print(f"⚠️  Unexpected result format")
                print(f"   Keys: {list(result.keys())}")
                error_count += 1
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Summary")
        print("=" * 60)
        print(f"✅ Successful: {success_count}")
        print(f"❌ Errors: {error_count}")
        print(f"📁 Output directory: {output_dir.absolute()}")
        print(f"💾 Total size: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
        
        if success_count > 0:
            avg_size = total_size / success_count
            print(f"📏 Average PDF size: {avg_size:,.0f} bytes ({avg_size/1024:.1f} KB)")
            print(f"\n💡 Open the PDF files to view the reports!")
        
    except requests.exceptions.Timeout:
        print(f"\n❌ Request timeout - PDF generation takes longer than expected")
        print("   Try reducing the number of URLs or increase the timeout")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        print("\n💡 Make sure:")
        print("   1. Server is running: uvicorn app.main:app --reload")
        print("   2. Playwright is installed: playwright install chromium")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


def test_single_pdf():
    """Test with a single URL for faster testing"""
    
    print("\n\n🔬 Quick Test: Single PDF")
    print("=" * 60)
    
    try:
        response = requests.post(
            "http://localhost:8000/analyze-pdf",
            json={"urls": [TEST_URLS[0]]},
            timeout=300
        )
        response.raise_for_status()
        
        results = response.json()
        result = results[0]
        
        if 'pdf_base64' in result:
            # Save the PDF
            pdf_bytes = base64.b64decode(result['pdf_base64'])
            test_path = Path("quick_test.pdf")
            
            with open(test_path, 'wb') as f:
                f.write(pdf_bytes)
            
            print(f"✅ Quick test successful!")
            print(f"   Client: {result['client_name']}")
            print(f"   File: {test_path}")
            print(f"   Size: {len(pdf_bytes):,} bytes")
        else:
            print(f"❌ Error: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Quick test failed: {e}")


def compare_endpoints():
    """Compare performance of HTML vs PDF endpoints"""
    
    print("\n\n⚡ Performance Comparison")
    print("=" * 60)
    
    import time
    
    # Test HTML endpoint
    print("\n📊 Testing HTML endpoint...")
    start = time.time()
    try:
        response = requests.post(
            "http://localhost:8000/analyze-html",
            json={"urls": [TEST_URLS[0]]},
            timeout=120
        )
        html_time = time.time() - start
        print(f"✅ HTML generation: {html_time:.2f}s")
    except Exception as e:
        print(f"❌ HTML test failed: {e}")
        html_time = None
    
    # Test PDF endpoint
    print("\n📄 Testing PDF endpoint...")
    start = time.time()
    try:
        response = requests.post(
            "http://localhost:8000/analyze-pdf",
            json={"urls": [TEST_URLS[0]]},
            timeout=300
        )
        pdf_time = time.time() - start
        print(f"✅ PDF generation: {pdf_time:.2f}s")
    except Exception as e:
        print(f"❌ PDF test failed: {e}")
        pdf_time = None
    
    # Summary
    if html_time and pdf_time:
        print(f"\n📈 Performance:")
        print(f"   HTML: {html_time:.2f}s")
        print(f"   PDF:  {pdf_time:.2f}s")
        print(f"   Overhead: {pdf_time - html_time:.2f}s ({(pdf_time/html_time - 1)*100:.0f}% slower)")


if __name__ == "__main__":
    # Run quick test first
    test_single_pdf()
    
    # Then full test
    test_pdf_endpoint()
    
    # Optional: performance comparison
    # compare_endpoints()
    
    print("\n\n✨ Testing complete!")