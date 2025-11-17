"""
Test runner for all target codebase tests
Runs all test suites and generates a summary report
"""

import unittest
import sys
import os
from io import StringIO

# Import all test modules
from test_gpio_handler import TestGPIOHandler
from test_command_processor import TestCommandProcessor
from test_adc import TestMCP3008ADC
from test_tcp_communication import TestTCPCommunication
from test_udp_communication import TestUDPCommunication


def run_all_tests():
    """Run all test suites and generate report"""
    print("=" * 80)
    print("TARGET CODEBASE TEST SUITE")
    print("=" * 80)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestGPIOHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestMCP3008ADC))
    suite.addTests(loader.loadTestsFromTestCase(TestTCPCommunication))
    suite.addTests(loader.loadTestsFromTestCase(TestUDPCommunication))

    # Run tests
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(suite)

    # Print results
    print(stream.getvalue())

    # Calculate statistics
    passed = result.testsRun - len(result.failures) - len(result.errors)
    success_rate = (passed / result.testsRun * 100) if result.testsRun > 0 else 0

    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {result.testsRun}")
    print(f"Passed: {passed}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {success_rate:.1f}%")
    print("=" * 80)

    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")

    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")

    # Generate formatted report file
    generate_report_file(result, passed, success_rate, stream.getvalue())

    return result


def generate_report_file(result, passed, success_rate, test_output):
    """Generate a formatted test report file"""
    report_path = os.path.join(os.path.dirname(__file__), "TEST_REPORT.txt")
    
    # Extract test names and status from test output
    test_lines = test_output.split('\n')
    test_results = []
    
    for line in test_lines:
        line = line.strip()
        # Look for lines like "test_name (module.Class.test_name) ... ok"
        if '...' in line and ('test_' in line or 'Test ' in line):
            parts = line.split('...')
            if len(parts) == 2:
                # Extract just the test name (before the parentheses)
                test_part = parts[0].strip()
                status_part = parts[1].strip()
                
                # Get clean test name
                if '(' in test_part:
                    test_name = test_part.split('(')[0].strip()
                else:
                    test_name = test_part
                
                # Determine status
                if status_part == 'ok':
                    status = 'ok'
                elif 'FAIL' in status_part:
                    status = 'FAIL'
                elif 'ERROR' in status_part:
                    status = 'ERROR'
                else:
                    status = status_part
                
                test_results.append((test_name, status))
    
    with open(report_path, "w", encoding="utf-8") as f:
        for test_name, status in test_results:
            f.write(f"{test_name} ... {status}\n")
    
    print(f"\n✓ Clean report saved to: {report_path}")


if __name__ == "__main__":
    result = run_all_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
