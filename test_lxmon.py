#!/usr/bin/env python3
"""
Comprehensive test script for lxmon system verification.
Tests all major components and API endpoints.
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
DASHBOARD_URL = "http://localhost:3000"

def test_endpoint(name, url, expected_status=200, timeout=10):
    """Test an API endpoint and return results."""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout)
        response_time = time.time() - start_time

        success = response.status_code == expected_status
        result = {
            "name": name,
            "url": url,
            "status_code": response.status_code,
            "response_time": f"{response_time:.2f}s",
            "success": success
        }

        if success and response.headers.get('content-type', '').startswith('application/json'):
            try:
                result["data"] = response.json()
            except:
                result["data"] = "Invalid JSON response"

        return result

    except requests.exceptions.RequestException as e:
        return {
            "name": name,
            "url": url,
            "error": str(e),
            "success": False
        }

def print_test_result(result):
    """Print formatted test result."""
    status_icon = "✅" if result["success"] else "❌"
    status_color = "\033[92m" if result["success"] else "\033[91m"
    reset_color = "\033[0m"

    print(f"{status_icon} {result['name']}")
    print(f"   URL: {result['url']}")

    if "status_code" in result:
        print(f"   Status: {result['status_code']} ({result.get('response_time', 'N/A')})")

    if "error" in result:
        print(f"   Error: {result['error']}")

    if "data" in result and isinstance(result["data"], dict):
        # Print key system info
        if "status" in result["data"]:
            print(f"   System Status: {result['data']['status']}")
        if "uptime" in result["data"]:
            print(f"   Uptime: {result['data']['uptime']}")
        if "database" in result["data"] and isinstance(result["data"]["database"], dict):
            db_status = result["data"]["database"].get("connection_status", "unknown")
            print(f"   Database: {db_status}")
        if "redis" in result["data"] and isinstance(result["data"]["redis"], dict):
            redis_status = result["data"]["redis"].get("status", "unknown")
            print(f"   Redis: {redis_status}")

    print()

def main():
    """Run comprehensive system tests."""
    print("🚀 lxmon System Verification Test")
    print("=" * 50)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Test endpoints
    tests = [
        {
            "name": "Health Check",
            "url": f"{BASE_URL}/health",
            "expected_status": 200
        },
        {
            "name": "System Info",
            "url": f"{BASE_URL}/api/system/info",
            "expected_status": 200
        },
        {
            "name": "API Documentation",
            "url": f"{BASE_URL}/docs",
            "expected_status": 200
        },
        {
            "name": "OpenAPI Schema",
            "url": f"{BASE_URL}/openapi.json",
            "expected_status": 200
        },
        {
            "name": "Prometheus Metrics",
            "url": f"{BASE_URL}/metrics",
            "expected_status": 200
        },
        {
            "name": "Dashboard",
            "url": DASHBOARD_URL,
            "expected_status": 200
        }
    ]

    results = []
    for test in tests:
        result = test_endpoint(**test)
        results.append(result)
        print_test_result(result)

    # Summary
    print("=" * 50)
    successful_tests = sum(1 for r in results if r["success"])
    total_tests = len(results)

    print(f"📊 Test Summary: {successful_tests}/{total_tests} tests passed")

    if successful_tests == total_tests:
        print("🎉 All tests passed! lxmon system is fully operational.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the system configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
