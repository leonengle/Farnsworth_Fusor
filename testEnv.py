import sys
import os
import warnings

def importChecker():
    failed = False
    warnings.filterwarnings("ignore")
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')

    try:
        import PySimpleGUI
        sys.stdout = original_stdout
        print("PySimpleGUI imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("PySimpleGUI import failed!")
        failed = True

    try:
        import paramiko
        sys.stdout = original_stdout
        print("Paramiko imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("Paramiko import failed!")
        failed = True
        
    try:
        from Adafruit_GPIO import SPI
        import Adafruit_MCP3008
        sys.stdout = original_stdout
        print("Adafruit GPIO/MCP3008 imported successfully!")
    except ImportError:
        sys.stdout = original_stdout
        print("Adafruit GPIO/MCP3008 import failed!")
        failed = True

    if failed:
        print("One or more imports failed.")
    else:
        print("All imports succeeded.")

if __name__ == "__main__":
    importChecker()
