import sys
import os
import warnings

def importChecker():
    failed = False
    warnings.filterwarnings("ignore")
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')

    # Test core Python libraries
    try:
        import tkinter
        sys.stdout = original_stdout
        print("✓ tkinter imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ tkinter import failed!")
        failed = True

    try:
        import json
        sys.stdout = original_stdout
        print("✓ json imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ json import failed!")
        failed = True

    try:
        import logging
        sys.stdout = original_stdout
        print("✓ logging imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ logging import failed!")
        failed = True

    # Test external dependencies
    try:
        import PySimpleGUI
        sys.stdout = original_stdout
        print("✓ PySimpleGUI imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ PySimpleGUI import failed!")
        failed = True

    try:
        import paramiko
        sys.stdout = original_stdout
        print("✓ paramiko imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ paramiko import failed!")
        failed = True
        
    try:
        from Adafruit_GPIO import SPI
        import Adafruit_MCP3008
        sys.stdout = original_stdout
        print("✓ Adafruit GPIO/MCP3008 imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ Adafruit GPIO/MCP3008 import failed!")
        failed = True

    # Test project modules
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'Host_Codebase'))
        import base_classes
        sys.stdout = original_stdout
        print("✓ base_classes imported successfully!")
    except ImportError as e:
        sys.stdout = original_stdout
        print(f"✗ base_classes import failed: {e}")
        failed = True

    try:
        import config
        sys.stdout = original_stdout
        print("✓ config imported successfully!")
    except ImportError as e:
        sys.stdout = original_stdout
        print(f"✗ config import failed: {e}")
        failed = True

    try:
        import logging_setup
        sys.stdout = original_stdout
        print("✓ logging_setup imported successfully!")
    except ImportError as e:
        sys.stdout = original_stdout
        print(f"✗ logging_setup import failed: {e}")
        failed = True

    if failed:
        print("\n❌ One or more imports failed. Please check your environment setup.")
        return False
    else:
        print("\n✅ All imports succeeded! Environment is ready.")
        return True

if __name__ == "__main__":
    importChecker()
