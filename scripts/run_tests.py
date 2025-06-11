#!/usr/bin/env python3
"""
Comprehensive test runner for the DPC Health Insurance Lead Generation System.

This script provides different modes for running tests:
- Unit tests only
- Integration tests only  
- End-to-end tests only
- Performance tests only
- All tests
- Custom test selection

Usage:
    python scripts/run_tests.py --mode unit
    python scripts/run_tests.py --mode integration
    python scripts/run_tests.py --mode e2e
    python scripts/run_tests.py --mode performance
    python scripts/run_tests.py --mode all
    python scripts/run_tests.py --custom "tests/unit/test_lead_scoring.py"
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime


class TestRunner:
    """Test runner for the lead generation system."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests"
        self.results_dir = self.test_dir / "results"
        self.coverage_dir = self.test_dir / "coverage"
        
        # Ensure directories exist
        self.results_dir.mkdir(exist_ok=True)
        self.coverage_dir.mkdir(exist_ok=True)
    
    def run_command(self, cmd):
        """Run a command and return the result."""
        print(f"Running: {' '.join(cmd)}")
        print("-" * 80)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Error running command: {e}")
            return False
    
    def run_unit_tests(self):
        """Run unit tests only."""
        print("🧪 Running Unit Tests")
        cmd = [
            "python", "-m", "pytest",
            "tests/unit/",
            "-v",
            "--tb=short",
            f"--html={self.results_dir}/unit_tests_report.html",
            "--self-contained-html"
        ]
        return self.run_command(cmd)
    
    def run_integration_tests(self):
        """Run integration tests only."""
        print("🔗 Running Integration Tests")
        cmd = [
            "python", "-m", "pytest", 
            "tests/integration/",
            "-v",
            "--tb=short",
            f"--html={self.results_dir}/integration_tests_report.html",
            "--self-contained-html"
        ]
        return self.run_command(cmd)
    
    def run_e2e_tests(self):
        """Run end-to-end tests only."""
        print("🚀 Running End-to-End Tests")
        cmd = [
            "python", "-m", "pytest",
            "tests/end_to_end/",
            "-v",
            "--tb=long",
            f"--html={self.results_dir}/e2e_tests_report.html",
            "--self-contained-html"
        ]
        return self.run_command(cmd)
    
    def run_performance_tests(self):
        """Run performance tests only."""
        print("⚡ Running Performance Tests")
        cmd = [
            "python", "-m", "pytest",
            "tests/performance/",
            "-v",
            "--tb=short",
            "--benchmark-only",
            "--benchmark-sort=mean",
            f"--benchmark-json={self.results_dir}/benchmark_results.json",
            f"--html={self.results_dir}/performance_tests_report.html",
            "--self-contained-html"
        ]
        return self.run_command(cmd)
    
    def run_all_tests(self):
        """Run all tests with comprehensive coverage."""
        print("🔄 Running All Tests")
        cmd = [
            "python", "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--maxfail=5",
            f"--html={self.results_dir}/all_tests_report.html",
            "--self-contained-html",
            "--cov-config=tests/pytest.ini"
        ]
        return self.run_command(cmd)
    
    def run_custom_tests(self, test_path):
        """Run custom test selection."""
        print(f"🎯 Running Custom Tests: {test_path}")
        cmd = [
            "python", "-m", "pytest",
            test_path,
            "-v",
            "--tb=short",
            f"--html={self.results_dir}/custom_tests_report.html",
            "--self-contained-html"
        ]
        return self.run_command(cmd)
    
    def run_fast_tests(self):
        """Run fast tests only (exclude slow/performance tests)."""
        print("🏃 Running Fast Tests Only")
        cmd = [
            "python", "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "-m", "not slow and not performance",
            f"--html={self.results_dir}/fast_tests_report.html",
            "--self-contained-html"
        ]
        return self.run_command(cmd)
    
    def run_parallel_tests(self):
        """Run tests in parallel for faster execution."""
        print("⚡ Running Tests in Parallel")
        cmd = [
            "python", "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "-n", "auto",  # Use all available CPUs
            "--dist=loadfile",
            f"--html={self.results_dir}/parallel_tests_report.html",
            "--self-contained-html"
        ]
        return self.run_command(cmd)
    
    def run_coverage_report(self):
        """Generate detailed coverage report."""
        print("📊 Generating Coverage Report")
        cmd = [
            "python", "-m", "pytest",
            "tests/",
            "--cov=models",
            "--cov=workers", 
            "--cov=api",
            "--cov=scrapers",
            "--cov-report=html:" + str(self.coverage_dir / "html"),
            "--cov-report=xml:" + str(self.coverage_dir / "coverage.xml"),
            "--cov-report=term-missing",
            "--cov-fail-under=80"
        ]
        return self.run_command(cmd)
    
    def run_linting(self):
        """Run linting and code quality checks."""
        print("🔍 Running Code Quality Checks")
        
        # Run flake8
        print("Running flake8...")
        flake8_cmd = ["python", "-m", "flake8", "models", "workers", "api", "scrapers", "tests"]
        flake8_success = self.run_command(flake8_cmd)
        
        # Run mypy  
        print("Running mypy...")
        mypy_cmd = ["python", "-m", "mypy", "models", "workers", "api", "scrapers"]
        mypy_success = self.run_command(mypy_cmd)
        
        return flake8_success and mypy_success
    
    def print_summary(self, results):
        """Print test execution summary."""
        print("\n" + "="*80)
        print("TEST EXECUTION SUMMARY")
        print("="*80)
        
        for test_type, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{test_type:30} {status}")
        
        total_passed = sum(results.values())
        total_tests = len(results)
        
        print("-" * 80)
        print(f"Total: {total_passed}/{total_tests} test suites passed")
        
        if total_passed == total_tests:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed. Check the reports for details.")
        
        print(f"\nReports generated in: {self.results_dir}")
        print(f"Coverage reports in: {self.coverage_dir}")
        print("="*80)


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Test runner for DPC Lead Generation System")
    parser.add_argument(
        "--mode", 
        choices=["unit", "integration", "e2e", "performance", "all", "fast", "parallel", "coverage", "lint"],
        default="all",
        help="Test execution mode"
    )
    parser.add_argument(
        "--custom",
        help="Custom test path to run specific tests"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Skip coverage reporting"
    )
    parser.add_argument(
        "--verbose",
        action="store_true", 
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    results = {}
    
    print("🧪 DPC Health Insurance Lead Generation System - Test Runner")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    try:
        if args.custom:
            results["Custom Tests"] = runner.run_custom_tests(args.custom)
        elif args.mode == "unit":
            results["Unit Tests"] = runner.run_unit_tests()
        elif args.mode == "integration":
            results["Integration Tests"] = runner.run_integration_tests()
        elif args.mode == "e2e":
            results["End-to-End Tests"] = runner.run_e2e_tests()
        elif args.mode == "performance":
            results["Performance Tests"] = runner.run_performance_tests()
        elif args.mode == "fast":
            results["Fast Tests"] = runner.run_fast_tests()
        elif args.mode == "parallel":
            results["Parallel Tests"] = runner.run_parallel_tests()
        elif args.mode == "coverage":
            results["Coverage Report"] = runner.run_coverage_report()
        elif args.mode == "lint":
            results["Code Quality"] = runner.run_linting()
        elif args.mode == "all":
            print("Running comprehensive test suite...\n")
            
            # Run linting first
            results["Code Quality"] = runner.run_linting()
            
            # Run all test types
            results["Unit Tests"] = runner.run_unit_tests()
            results["Integration Tests"] = runner.run_integration_tests()
            results["End-to-End Tests"] = runner.run_e2e_tests()
            results["Performance Tests"] = runner.run_performance_tests()
            
            # Generate coverage report if not skipped
            if not args.no_coverage:
                results["Coverage Report"] = runner.run_coverage_report()
        
        runner.print_summary(results)
        
        # Exit with error code if any tests failed
        if not all(results.values()):
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n❌ Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()