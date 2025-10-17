#!/usr/bin/env python3
"""
Test environment setup for Farnsworth Fusor project.
This script sets up a test environment for local testing without hardware.
"""

import os
import sys
import subprocess
import tempfile
import shutil

def create_mock_modules():
    """Create mock modules for testing without hardware."""
    
    # Create mock GPIO module
    mock_gpio_content = '''
import time

class MockGPIO:
    BCM = "BCM"
    OUT = "OUT"
    IN = "IN"
    HIGH = 1
    LOW = 0
    
    @staticmethod
    def setmode(mode):
        print(f"Mock GPIO: setmode({mode})")
    
    @staticmethod
    def setup(pin, mode):
        print(f"Mock GPIO: setup({pin}, {mode})")
    
    @staticmethod
    def output(pin, value):
        print(f"Mock GPIO: output({pin}, {value})")
    
    @staticmethod
    def input(pin):
        print(f"Mock GPIO: input({pin})")
        return 0
    
    @staticmethod
    def cleanup():
        print("Mock GPIO: cleanup()")

# Make it available as GPIO
GPIO = MockGPIO()
'''
    
    # Create mock ADC module
    mock_adc_content = '''
class MockMCP3008ADC:
    def __init__(self):
        print("Mock ADC: Initialized")
    
    def read_channel(self, channel):
        print(f"Mock ADC: read_channel({channel})")
        return 512  # Return middle value
    
    def read_adc_channel(self, channel):
        return self.read_channel(channel)
'''
    
    # Write mock modules
    with open("src/Target_Codebase/mock_gpio.py", "w") as f:
        f.write(mock_gpio_content)
    
    with open("src/Target_Codebase/mock_adc.py", "w") as f:
        f.write(mock_adc_content)
    
    print("✓ Created mock modules for testing")

def setup_test_environment():
    """Set up test environment."""
    print("Setting up test environment...")
    
    # Create test directories
    test_dirs = ["test_logs", "test_data", "test_output"]
    for directory in test_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created test directory: {directory}")
    
    # Create mock modules
    create_mock_modules()
    
    print("✓ Test environment setup completed")

def run_tests():
    """Run basic tests."""
    print("Running basic tests...")
    
    # Test imports
    try:
        import sys
        sys.path.append("src/Target_Codebase")
        
        # Test mock imports
        import mock_gpio
        import mock_adc
        
        print("✓ Mock modules imported successfully")
        
        # Test basic functionality
        mock_gpio.GPIO.setmode(mock_gpio.GPIO.BCM)
        mock_gpio.GPIO.setup(26, mock_gpio.GPIO.OUT)
        mock_gpio.GPIO.output(26, mock_gpio.GPIO.HIGH)
        
        adc = mock_adc.MockMCP3008ADC()
        value = adc.read_channel(0)
        
        print("✓ Mock functionality tested successfully")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    
    return True

def main():
    """Main test environment setup."""
    print("Farnsworth Fusor Test Environment Setup")
    print("=" * 40)
    
    # Setup test environment
    setup_test_environment()
    
    # Run tests
    if run_tests():
        print("\n" + "=" * 40)
        print("Test environment setup completed successfully!")
        print("\nYou can now run:")
        print("1. Local testing: python src/Target_Codebase/target_main.py")
        print("2. Host testing: python src/Host_Codebase/ssh_datalink_host.py")
    else:
        print("\n" + "=" * 40)
        print("Test environment setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
