#!/usr/bin/env python3
"""
Test runner script for ChatOps CLI testing framework.

This script demonstrates the testing framework capabilities and provides
easy ways to run different types of tests.
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run a command and display results."""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    print(f"Running: {cmd}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print(f"Exit Code: {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def main():
    """Main test runner function."""
    print("🧪 ChatOps CLI Testing Framework")
    print("=" * 60)
    
    # Check if pytest is available
    try:
        import pytest
        print(f"✅ Pytest version: {pytest.__version__}")
    except ImportError:
        print("❌ Pytest not found. Please install with: pip install pytest pytest-cov pytest-asyncio")
        return 1
    
    # Check if coverage is available
    try:
        import coverage
        print(f"✅ Coverage version: {coverage.__version__}")
    except ImportError:
        print("❌ Coverage not found. Please install with: pip install pytest-cov")
        return 1
    
    print("\n📋 Available Test Categories:")
    print("1. Unit Tests - Core functionality testing")
    print("2. Integration Tests - CLI and system integration")
    print("3. Security Tests - Security system validation")
    print("4. Logging Tests - Logging system validation")
    print("5. All Tests - Complete test suite")
    print("6. Coverage Report - Code coverage analysis")
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\nSelect test category (1-6): ").strip()
    
    success = True
    
    if choice == "1" or choice.lower() == "unit":
        print("\n🔧 Running Unit Tests...")
        success &= run_command(
            "python -m pytest tests/test_unit_*.py -v --tb=short",
            "Unit Tests - Core functionality testing"
        )
    
    elif choice == "2" or choice.lower() == "integration":
        print("\n🔗 Running Integration Tests...")
        success &= run_command(
            "python -m pytest tests/test_integration_*.py -v --tb=short",
            "Integration Tests - CLI and system integration"
        )
    
    elif choice == "3" or choice.lower() == "security":
        print("\n🔒 Running Security Tests...")
        success &= run_command(
            "python -m pytest tests/test_unit_security_system.py -v --tb=short -m security",
            "Security Tests - Security system validation"
        )
    
    elif choice == "4" or choice.lower() == "logging":
        print("\n📝 Running Logging Tests...")
        success &= run_command(
            "python -m pytest tests/test_unit_logging_system.py -v --tb=short -m logging",
            "Logging Tests - Logging system validation"
        )
    
    elif choice == "5" or choice.lower() == "all":
        print("\n🚀 Running All Tests...")
        success &= run_command(
            "python -m pytest tests/ -v --tb=short",
            "All Tests - Complete test suite"
        )
    
    elif choice == "6" or choice.lower() == "coverage":
        print("\n📊 Generating Coverage Report...")
        success &= run_command(
            "python -m pytest tests/ --cov=chatops_cli --cov-report=term-missing --cov-report=html:htmlcov",
            "Coverage Report - Code coverage analysis"
        )
        
        if Path("htmlcov/index.html").exists():
            print("\n📈 Coverage report generated at: htmlcov/index.html")
            print("Open this file in your browser to view detailed coverage information.")
    
    else:
        print(f"❌ Invalid choice: {choice}")
        return 1
    
    print(f"\n{'='*60}")
    if success:
        print("✅ All tests completed successfully!")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    print(f"{'='*60}")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 