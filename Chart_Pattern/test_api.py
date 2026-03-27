#!/usr/bin/env python3
"""Test API endpoints to verify JSON serialization fix"""

import urllib.request
import json
import sys

def test_endpoint(url):
    """Test an API endpoint"""
    try:
        print(f"\n📍 Testing: {url}")
        response = urllib.request.urlopen(url, timeout=5)
        data = response.read().decode()
        
        # Try to parse as JSON
        result = json.loads(data)
        print(f"✅ Success (status {response.status})")
        print(f"   Response preview: {str(result)[:200]}...")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ JSON Error: {e}")
        print(f"   Response: {data[:200]}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Test all critical endpoints"""
    base_url = "http://localhost:8000"
    
    endpoints = [
        f"{base_url}/api/health",
        f"{base_url}/api/signals",
        f"{base_url}/api/stats",
        f"{base_url}/api/patterns",
        f"{base_url}/api/status",
    ]
    
    print("=" * 50)
    print("ET Markets - API Test Suite")
    print("=" * 50)
    
    results = []
    for endpoint in endpoints:
        results.append(test_endpoint(endpoint))
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} passed")
    print("=" * 50)
    
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
