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

def test_html_endpoint():
    """Test the /analyze-html endpoint"""
    
    print("🚀 Testing HTML Report Generation")
    print("=" * 60)
    
    # Create output directory
    output_dir = Path("html_reports")
    output_dir.mkdir(exist_ok=True)
    
    # Make request
    print(f"\n📡 Sending request for {len(TEST_URLS)} reports...")
    
    try:
        response = requests.post(
            "http://localhost:8000/analyze-html",
            json={"urls": TEST_URLS},
            timeout=300  # 5 minutes timeout
        )
        response.raise_for_status()
        
        results = response.json()
        
        print(f"✅ Received {len(results)} results\n")
        
        # Process each result
        success_count = 0
        error_count = 0
        
        for i, result in enumerate(results, 1):
            print(f"\n📄 Report {i}/{len(results)}")
            print("-" * 60)
            
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
                print(f"   URL: {result.get('url', 'unknown')}")
                error_count += 1
                
            elif 'html' in result:
                client_name = result.get('client_name', f'unknown_{i}')
                
                # Clean filename
                safe_name = client_name.replace(' ', '_').replace('/', '_')
                filename = output_dir / f"{safe_name}_report.html"
                
                # Save HTML
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(result['html'])
                
                print(f"✅ Client: {client_name}")
                print(f"   Saved: {filename}")
                print(f"   Size: {len(result['html']):,} bytes")
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
        
        if success_count > 0:
            print(f"\n💡 Open the HTML files in your browser to view the reports!")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        print("\n💡 Make sure the server is running:")
        print("   uvicorn app.main:app --reload")
        
    except json.JSONDecodeError as e:
        print(f"\n❌ Invalid JSON response: {e}")
        print(f"   Response text: {response.text[:200]}")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


def test_json_endpoint():
    """Test that the original /analyze endpoint still works"""
    
    print("\n\n🔄 Testing Original JSON Endpoint")
    print("=" * 60)
    
    try:
        response = requests.post(
            "http://localhost:8000/analyze",
            json={"urls": TEST_URLS[:1]},  # Test with just one URL
            timeout=120
        )
        response.raise_for_status()
        
        results = response.json()
        
        print(f"✅ JSON endpoint working")
        print(f"   Results: {len(results)}")
        print(f"   First result keys: {list(results[0].keys())}")
        
        # Save sample JSON
        with open("sample_json_output.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"   Saved sample: sample_json_output.json")
        
    except Exception as e:
        print(f"❌ JSON endpoint test failed: {e}")


if __name__ == "__main__":
    test_html_endpoint()
    test_json_endpoint()
    
    print("\n\n✨ Testing complete!")