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

    # Test external dependencies from requirements.txt
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

    try:
        import Adafruit_PureIO
        sys.stdout = original_stdout
        print("✓ Adafruit_PureIO imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ Adafruit_PureIO import failed!")
        failed = True

    try:
        import bcrypt
        sys.stdout = original_stdout
        print("✓ bcrypt imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ bcrypt import failed!")
        failed = True

    try:
        import cffi
        sys.stdout = original_stdout
        print("✓ cffi imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ cffi import failed!")
        failed = True

    try:
        import cryptography
        sys.stdout = original_stdout
        print("✓ cryptography imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ cryptography import failed!")
        failed = True

    try:
        import pycparser
        sys.stdout = original_stdout
        print("✓ pycparser imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ pycparser import failed!")
        failed = True

    try:
        import nacl
        sys.stdout = original_stdout
        print("✓ PyNaCl imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ PyNaCl import failed!")
        failed = True

    try:
        import RPi.GPIO
        sys.stdout = original_stdout
        print("✓ RPi.GPIO imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ RPi.GPIO import failed!")
        failed = True

    try:
        import spidev
        sys.stdout = original_stdout
        print("✓ spidev imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ spidev import failed!")
        failed = True

    try:
        import pigpio
        sys.stdout = original_stdout
        print("✓ pigpio imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ pigpio import failed!")
        failed = True

    # Test development tools
    try:
        import pylint
        sys.stdout = original_stdout
        print("✓ pylint imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ pylint import failed!")
        failed = True

    try:
        import black
        sys.stdout = original_stdout
        print("✓ black imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ black import failed!")
        failed = True

    try:
        import pre_commit
        sys.stdout = original_stdout
        print("✓ pre-commit imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("✗ pre-commit import failed!")
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

    # Test Target_Codebase modules
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'Target_Codebase'))
        import base_classes as target_base_classes
        sys.stdout = original_stdout
        print("✓ Target_Codebase base_classes imported successfully!")
    except ImportError as e:
        sys.stdout = original_stdout
        print(f"✗ Target_Codebase base_classes import failed: {e}")
        failed = True

    try:
        import adc
        sys.stdout = original_stdout
        print("✓ adc imported successfully!")
    except ImportError as e:
        sys.stdout = original_stdout
        print(f"✗ adc import failed: {e}")
        failed = True

    try:
        import moveVARIAC
        sys.stdout = original_stdout
        print("✓ moveVARIAC imported successfully!")
    except ImportError as e:
        sys.stdout = original_stdout
        print(f"✗ moveVARIAC import failed: {e}")
        failed = True

    if failed:
        print("\n❌ One or more imports failed. Please check your environment setup.")
        return False
    else:
        print("\n✅ All imports succeeded! Environment is ready.")
        return True

if __name__ == "__main__":
    importChecker()
