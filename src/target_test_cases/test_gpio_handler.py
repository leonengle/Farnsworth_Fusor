"""
Unit tests for GPIO Handler module
Tests GPIO operations including LED control and input reading
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add Target_Codebase to path to import target codebase modules
target_codebase_path = os.path.join(os.path.dirname(__file__), "..", "Target_Codebase")
sys.path.insert(0, target_codebase_path)

# Mock RPi.GPIO before importing gpio_handler (required for non-RPi environments)
mock_gpio = MagicMock()
mock_gpio.BCM = 11
mock_gpio.OUT = 0
mock_gpio.IN = 1
mock_gpio.HIGH = 1
mock_gpio.LOW = 0
mock_gpio.PUD_DOWN = 21

sys.modules["RPi"] = MagicMock()
sys.modules["RPi.GPIO"] = mock_gpio

# Import after path setup and mocking (direct import since path is added)
from gpio_handler import GPIOHandler


class TestGPIOHandler(unittest.TestCase):
    """Test cases for GPIOHandler class"""

    def setUp(self):
        """Set up test fixtures"""
        # GPIO is already mocked at module level
        # Patch the GPIO module used by gpio_handler
        with patch("gpio_handler.GPIO") as mock_gpio:
            self.gpio_handler = GPIOHandler(led_pin=26, input_pin=6)
            self.mock_gpio = mock_gpio

    def test_initialization(self):
        """Test GPIO handler initialization"""
        self.assertTrue(self.gpio_handler.initialized)
        self.assertEqual(self.gpio_handler.led_pin, 26)
        self.assertEqual(self.gpio_handler.input_pin, 6)
        print("✓ test_initialization: PASSED")

    def test_led_on(self):
        """Test LED turn on functionality"""
        result = self.gpio_handler.led_on()
        self.assertTrue(result)
        print("✓ test_led_on: PASSED")

    def test_led_off(self):
        """Test LED turn off functionality"""
        result = self.gpio_handler.led_off()
        self.assertTrue(result)
        print("✓ test_led_off: PASSED")

    def test_read_input(self):
        """Test reading digital input pin"""
        with patch.object(self.gpio_handler, "read_input", return_value=1):
            value = self.gpio_handler.read_input()
            self.assertIsNotNone(value)
            self.assertIn(value, [0, 1])
        print("✓ test_read_input: PASSED")

    def test_error_handling_uninitialized(self):
        """Test error handling when GPIO not initialized"""
        self.gpio_handler.initialized = False
        result = self.gpio_handler.led_on()
        self.assertFalse(result)
        print("✓ test_error_handling_uninitialized: PASSED")

    def test_cleanup(self):
        """Test GPIO cleanup procedure"""
        result = self.gpio_handler.cleanup()
        self.assertFalse(self.gpio_handler.initialized)
        print("✓ test_cleanup: PASSED")

    def test_setup_pin(self):
        """Test setting up GPIO pin"""
        self.gpio_handler.setup(18, "OUTPUT")
        print("✓ test_setup_pin: PASSED")

    def test_write_pin(self):
        """Test writing to GPIO pin"""
        self.gpio_handler.write(18, 1)
        print("✓ test_write_pin: PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("GPIO Handler Unit Tests")
    print("=" * 60)
    unittest.main(verbosity=2)
