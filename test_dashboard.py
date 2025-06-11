#!/usr/bin/env python3
"""
Test script for the Lead Generation Dashboard

This script tests all major dashboard endpoints and functionality.
"""

import requests
import json
import sys
import time
from typing import Dict, Any

class DashboardTester:
    """Test class for dashboard endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
    
    def test_endpoint(self, endpoint: str, method: str = "GET", expected_status: int = 200) -> Dict[str, Any]:
        """Test a single endpoint."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            response = self.session.request(method, url, timeout=10)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            result = {
                "endpoint": endpoint,
                "method": method,
                "status_code": response.status_code,
                "response_time_ms": round(response_time, 2),
                "success": response.status_code == expected_status,
                "error": None,
                "data_size": len(response.content)
            }
            
            # Try to parse JSON response
            try:
                data = response.json()
                result["has_data"] = bool(data)
                if isinstance(data, dict):
                    result["keys"] = list(data.keys())
            except:
                result["has_data"] = False
            
        except requests.exceptions.RequestException as e:
            result = {
                "endpoint": endpoint,
                "method": method,
                "status_code": None,
                "response_time_ms": None,
                "success": False,
                "error": str(e),
                "data_size": 0,
                "has_data": False
            }
        
        self.results.append(result)
        return result
    
    def run_all_tests(self):
        """Run all dashboard tests."""
        print("🧪 Testing Lead Generation Dashboard")
        print("=" * 50)
        
        # Test endpoints
        endpoints = [
            ("/health", 200),
            ("/", 200),
            ("/api/metrics/leads", 200),
            ("/api/metrics/api-usage", 200),
            ("/api/metrics/system-health", 200),
            ("/api/metrics/queues", 200),
            ("/api/charts/leads-trend", 200),
            ("/api/charts/score-distribution", 200),
            ("/api/charts/api-costs", 200),
            ("/api/charts/error-rates", 200),
            ("/nonexistent", 404)  # Test 404 handling
        ]
        
        for endpoint, expected_status in endpoints:
            result = self.test_endpoint(endpoint, expected_status=expected_status)
            self.print_result(result)
        
        print("\n" + "=" * 50)
        self.print_summary()
    
    def print_result(self, result: Dict[str, Any]):
        """Print test result."""
        status_icon = "✅" if result["success"] else "❌"
        endpoint = result["endpoint"]
        status = result["status_code"] or "ERROR"
        response_time = result["response_time_ms"]
        
        if response_time:
            time_str = f"{response_time}ms"
        else:
            time_str = "N/A"
        
        print(f"{status_icon} {endpoint:<30} [{status}] {time_str}")
        
        if result["error"]:
            print(f"   Error: {result['error']}")
        elif result["has_data"] and "keys" in result:
            print(f"   Data: {', '.join(result['keys'][:5])}")
    
    def print_summary(self):
        """Print test summary."""
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - successful_tests
        
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"📊 Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {successful_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   📈 Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"   • {result['endpoint']}: {result['error'] or f'Status {result['status_code']}'}")
        
        # Performance summary
        response_times = [r["response_time_ms"] for r in self.results if r["response_time_ms"] is not None]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            print(f"\n⚡ Performance:")
            print(f"   Average Response Time: {avg_response_time:.2f}ms")
            print(f"   Max Response Time: {max_response_time:.2f}ms")

def test_dashboard_connectivity():
    """Test basic dashboard connectivity."""
    tester = DashboardTester()
    
    print("🔍 Testing dashboard connectivity...")
    health_result = tester.test_endpoint("/health")
    
    if health_result["success"]:
        print("✅ Dashboard is running and accessible")
        return True
    else:
        print("❌ Dashboard is not accessible")
        print(f"   Error: {health_result['error']}")
        return False

def main():
    """Main test function."""
    print("🚀 Dashboard Test Suite")
    print("=" * 50)
    
    # Check if dashboard is running
    if not test_dashboard_connectivity():
        print("\n💡 Make sure the dashboard is running:")
        print("   python run_dashboard.py")
        sys.exit(1)
    
    print()
    
    # Run all tests
    tester = DashboardTester()
    tester.run_all_tests()
    
    # Exit with error code if tests failed
    failed_tests = sum(1 for r in tester.results if not r["success"])
    if failed_tests > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()