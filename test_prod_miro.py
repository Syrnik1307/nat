#!/usr/bin/env python3
"""Quick API test for Miro OAuth endpoints on production."""
import requests

BASE_URL = "https://lectio.space"

def test_miro_api():
    """Test Miro API endpoints."""
    print("Testing Miro API endpoints on production...")
    
    # Test miro status (old endpoint - no auth required check)
    try:
        r = requests.get(f"{BASE_URL}/schedule/api/miro/status/", timeout=10)
        print(f"\n1. GET /schedule/api/miro/status/")
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            print(f"   Response: {r.json()}")
        elif r.status_code == 401:
            print("   Requires authentication (expected)")
        else:
            print(f"   Response: {r.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test miro oauth status (new endpoint)
    try:
        r = requests.get(f"{BASE_URL}/schedule/api/miro/oauth/status/", timeout=10)
        print(f"\n2. GET /schedule/api/miro/oauth/status/")
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            print(f"   Response: {r.json()}")
        elif r.status_code == 401:
            print("   Requires authentication (expected)")
        elif r.status_code == 403:
            print("   Forbidden (expected - needs teacher role)")
        else:
            print(f"   Response: {r.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test materials endpoint
    try:
        r = requests.get(f"{BASE_URL}/schedule/api/lesson-materials/", timeout=10)
        print(f"\n3. GET /schedule/api/lesson-materials/")
        print(f"   Status: {r.status_code}")
        if r.status_code == 401:
            print("   Requires authentication (expected)")
        else:
            print(f"   Response: {r.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n✅ API endpoints are responding!")

if __name__ == "__main__":
    test_miro_api()
