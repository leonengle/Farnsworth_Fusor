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
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print("=" * 80)
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result


if __name__ == '__main__':
    result = run_all_tests()
    sys.exit(0 if result.wasSuccessful() else 1)

