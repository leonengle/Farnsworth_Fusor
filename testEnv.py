import sys
import os
import warnings

def importChecker():
    failed = False

    # Suppress warnings (like deprecation warnings from paramiko)
    warnings.filterwarnings("ignore")

    # Redirect stdout to suppress PySimpleGUI's installation message
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')  # Redirect to null device

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

    if failed:
        print("One or more imports failed.")
    else:
        print("All imports succeeded.")

if __name__ == "__main__":
    importChecker()
