#!/usr/bin/env python3
"""
Quick test script for local development
Run this to test the API with your credit report URL
"""
import requests
import json

# Your test URL
TEST_URL = "https://api.boshhhfintech.com/File/CreditReport/70f05ac1-4806-4d37-afed-52630f845d65?Auth=ce39264e377782c82ed70d69d405eea6e9471c679bb18cbf814f5db483ada838"

# API endpoint (local)
API_URL = "http://localhost:8000/analyze"

def test_single_url():
    """Test with a single URL"""
    print("🧪 Testing with single URL...")
    print(f"📄 Report URL: {TEST_URL[:80]}...")
    
    payload = {
        "urls": [TEST_URL]
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        print("\n✅ SUCCESS!")
        print(f"\n📊 Summary:")
        print(f"  Total: {result['summary']['total']}")
        print(f"  Successful: {result['summary']['successful']}")
        print(f"  Failed: {result['summary']['failed']}")
        
        # Print first result details
        if result['results']:
            first_result = result['results'][0]
            print(f"\n📋 First Result:")
            print(f"  Status: {first_result['status']}")
            
            if first_result['status'] == 'success':
                data = first_result['data']
                print(f"\n👤 Client Info:")
                print(f"  Name: {data['client_info']['name']}")
                print(f"  Address: {data['client_info']['address']}")
                
                print(f"\n🚦 Traffic Light: {data['traffic_light']}")
                print(f"  Total Points: {data['total_points']}")
                
                print(f"\n📈 Indicators:")
                for indicator, details in data['indicators'].items():
                    if details['flagged']:
                        print(f"  ⚠️  {indicator}: {details['points']} points")
                
                print(f"\n💼 Claims Analysis:")
                print(f"  In-scope accounts: {len(data['claims_analysis']['in_scope'])}")
                print(f"  Out-of-scope accounts: {len(data['claims_analysis']['out_of_scope'])}")
                
                # Show first in-scope account if any
                if data['claims_analysis']['in_scope']:
                    first_account = data['claims_analysis']['in_scope'][0]
                    print(f"\n  Example in-scope account:")
                    print(f"    Lender: {first_account['name']}")
                    print(f"    Title: {first_account['title']}")
            else:
                print(f"  Error: {first_result.get('error', 'Unknown error')}")
        
        # Save full JSON to file
        with open('test_result.json', 'w') as f:
            json.dump(result, indent=2, fp=f)
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
            TEST_URL,
            # Add more URLs here to test concurrent processing
            # "https://api.boshhhfintech.com/File/CreditReport/another-id?Auth=...",
        ]
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        
        print(f"\n✅ Processed {result['summary']['total']} reports")
        print(f"  Successful: {result['summary']['successful']}")
        print(f"  Failed: {result['summary']['failed']}")
        
        with open('test_multiple_results.json', 'w') as f:
            json.dump(result, indent=2, fp=f)
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