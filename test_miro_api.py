#!/usr/bin/env python
"""Test Miro API on production"""
import requests

BASE_URL = "https://lectio.space/api"

# Test miro status endpoint (should work without auth)
print("=== Testing Miro Status API ===")
r = requests.get(f"{BASE_URL}/materials/miro/status/", timeout=10)
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:500]}")

# Test materials list (needs auth)
print("\n=== Testing Materials List API ===")
r2 = requests.get(f"{BASE_URL}/materials/", timeout=10)
print(f"Status: {r2.status_code}")
print(f"Response: {r2.text[:200]}")
