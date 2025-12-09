#!/usr/bin/env python3
"""
Run all host test cases
"""

import unittest
import sys
import os

test_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, test_dir)

loader = unittest.TestLoader()
suite = unittest.TestSuite()

test_modules = [
    "test_host_main",
]

for module_name in test_modules:
    try:
        module = __import__(module_name)
        suite.addTests(loader.loadTestsFromModule(module))
        print(f"[OK] Loaded {module_name}")
    except ImportError as e:
        print(f"[FAIL] Failed to import {module_name}: {e}")

if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback.split(chr(10))[-2]}")

    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback.split(chr(10))[-2]}")

    sys.exit(0 if result.wasSuccessful() else 1)

