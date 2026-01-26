#!/usr/bin/env python3
"""
Quick test script for local development
Run this to test the API with your credit report URL
"""
import requests
import json

# Your test URL
TEST_URLS = [
    "https://api.boshhhfintech.com/File/CreditReport/95d1ce7e-2c3c-49d5-a303-6a4727f91005?Auth=af26383640b084af4d2895307480ed795c334405b786d7419d78be541fcc0656",
    "https://api.boshhhfintech.com/File/CreditReport/e5f86646-9227-4f4e-839e-5a3437b36a45?Auth=72372a1d2fb8b8e5c78b3d4096a53b853dc22422676f789fc888986b82847cf1",
    "https://api.boshhhfintech.com/File/CreditReport/70f05ac1-4806-4d37-afed-52630f845d65?Auth=ce39264e377782c82ed70d69d405eea6e9471c679bb18cbf814f5db483ada838",
    "https://api.boshhhfintech.com/File/CreditReport/193db969-faaf-4eb0-8cc3-b35ad5d7085d?Auth=673f48f1399a4bdad4a66f3ed01db9ce620754375f9a19f579aa43888095d4db",
    "https://api.boshhhfintech.com/File/CreditReport/d2584f54-e597-44cc-a87c-92d252dbfbdb?Auth=7c76a1aa73f2df04cbe9d374db273ca2d1c1fd21abb5733b01e9db183699fb2e"
]

# API endpoint (local)
API_URL = "http://localhost:8000/analyze"

def test_single_url():
    """Test with a single URL"""
    print("🧪 Testing with single URL...")
    print(f"📄 Report URL: {TEST_URLS[:80]}...")
    
    payload = {"urls": TEST_URLS}


    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        results = response.json()
        
        print("\n✅ SUCCESS!")
        print(f"\n📊 Received {len(results)} result(s)")
        
        # Print first result details
        if results:
            first_result = results[0]
            
            if 'error' in first_result:
                print(f"\n❌ Error: {first_result['error']}")
            elif 'credit_analysis' in first_result:
                analysis = first_result['credit_analysis']
                
                print(f"\n👤 Client Info:")
                print(f"  Name: {analysis['client_info']['name']}")
                print(f"  Address: {analysis['client_info']['address']}")
                
                print(f"\n🚦 Traffic Light: {analysis['traffic_light']}")
                print(f"  Total Points: {analysis['total_points']}")
                
                print(f"\n📈 Indicators:")
                for indicator, details in analysis['indicators'].items():
                    if details['flagged']:
                        print(f"  ⚠️  {indicator}: {details['points']} points")
                
                print(f"\n💼 Claims Analysis:")
                print(f"  In-scope accounts: {len(analysis['claims_analysis']['in_scope'])}")
                print(f"  Out-of-scope accounts: {len(analysis['claims_analysis']['out_of_scope'])}")
                
                # Show first in-scope account if any
                if analysis['claims_analysis']['in_scope']:
                    first_account = analysis['claims_analysis']['in_scope'][0]
                    print(f"\n  Example in-scope account:")
                    print(f"    Lender: {first_account['name']}")
                    print(f"    Title: {first_account['title']}")
        
        # Save full JSON to file
        with open('test_result.json', 'w') as f:
            json.dump(results, indent=2, fp=f)
        print(f"\n💾 Full result saved to: test_result.json")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API")
        print("   Make sure the server is running:")
        print("   uvicorn app.main:app --reload")
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timeout")
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP ERROR: {e}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")


def test_multiple_urls():
    """Test with multiple URLs (add more URLs here)"""
    print("\n🧪 Testing with multiple URLs...")
    
    payload = {
        "urls": [
            TEST_URLS,
            # Add more URLs here to test concurrent processing
            # "https://api.boshhhfintech.com/File/CreditReport/another-id?Auth=...",
        ]
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=120)
        response.raise_for_status()
        
        results = response.json()
        
        print(f"\n✅ Processed {len(results)} report(s)")
        
        successful = sum(1 for r in results if 'credit_analysis' in r)
        failed = len(results) - successful
        
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        
        with open('test_multiple_results.json', 'w') as f:
            json.dump(results, indent=2, fp=f)
        print(f"\n💾 Results saved to: test_multiple_results.json")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Credit Report Analyzer - Local Test")
    print("=" * 60)
    
    # Test single URL
    test_single_url()
    
    # Uncomment to test multiple URLs
    # test_multiple_urls()
    
    print("\n" + "=" * 60)