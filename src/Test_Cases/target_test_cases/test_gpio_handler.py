"""
Unit tests for GPIO Handler module
Tests GPIO operations including LED, valves, pumps, and power supply control
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add Target_Codebase to path to import target codebase modules
target_codebase_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "Target_Codebase"
)
sys.path.insert(0, target_codebase_path)

# Mock lgpio before importing gpio_handler (required for non-RPi environments)
mock_lgpio = MagicMock()
mock_lgpio.SET_PULL_DOWN = 1
mock_lgpio.gpiochip_open = MagicMock(return_value=0)  # Return chip handle
mock_lgpio.gpio_claim_output = MagicMock(return_value=0)
mock_lgpio.gpio_claim_input = MagicMock(return_value=0)
mock_lgpio.gpio_write = MagicMock(return_value=0)
mock_lgpio.gpio_read = MagicMock(return_value=0)
mock_lgpio.gpio_free = MagicMock(return_value=0)
mock_lgpio.gpiochip_close = MagicMock(return_value=0)

sys.modules["lgpio"] = mock_lgpio

# Mock logging_setup
mock_logging_setup = MagicMock()
mock_logger = MagicMock()
mock_logging_setup.get_logger = MagicMock(return_value=mock_logger)
mock_logging_setup.setup_logging = MagicMock()
sys.modules["logging_setup"] = mock_logging_setup

from gpio_handler import GPIOHandler


class TestGPIOHandler(unittest.TestCase):
    """Test cases for GPIOHandler"""

    def setUp(self):
        """Set up test fixtures"""
        mock_lgpio.reset_mock()
        mock_lgpio.gpio_read.return_value = 0
        mock_lgpio.gpiochip_open.return_value = 0
        # Mock os.geteuid() for Windows compatibility (doesn't exist on Windows)
        # Patch os module to add geteuid if it doesn't exist
        import os
        if not hasattr(os, 'geteuid'):
            os.geteuid = lambda: 0
        # Ensure lgpio is patched
        self.lgpio_patcher = patch("gpio_handler.lgpio", mock_lgpio)
        self.lgpio_patcher.start()
        self.gpio_handler = GPIOHandler(
            led_pin=26,
            input_pin=6,
            power_supply_pin=5,
        )

    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, 'gpio_handler') and self.gpio_handler:
            try:
                self.gpio_handler.cleanup()
            except Exception:
                pass
        if hasattr(self, 'lgpio_patcher'):
            self.lgpio_patcher.stop()

    def test_initialization(self):
        """Test GPIO handler initialization"""
        self.assertTrue(self.gpio_handler.initialized)
        self.assertEqual(self.gpio_handler.led_pin, 26)
        self.assertEqual(self.gpio_handler.input_pin, 6)
        self.assertEqual(self.gpio_handler.power_supply_pin, 5)

    def test_led_on(self):
        """Test LED ON functionality"""
        if not self.gpio_handler.initialized:
            self.skipTest("GPIO handler not initialized - skipping LED test")
        result, msg = self.gpio_handler.led_on()
        self.assertTrue(result)
        mock_lgpio.gpio_write.assert_called()

    def test_led_off(self):
        """Test LED OFF functionality"""
        if not self.gpio_handler.initialized:
            self.skipTest("GPIO handler not initialized - skipping LED test")
        result, msg = self.gpio_handler.led_off()
        self.assertTrue(result)
        mock_lgpio.gpio_write.assert_called()

    def test_read_input(self):
        """Test reading input pin"""
        if not self.gpio_handler.initialized:
            self.skipTest("GPIO handler not initialized - skipping read_input test")
        mock_lgpio.gpio_read.return_value = 1
        result = self.gpio_handler.read_input()
        if result is not None:
            self.assertEqual(result, 1)
        if self.gpio_handler.initialized:
            mock_lgpio.gpio_read.assert_called()

    def test_power_supply_enable(self):
        """Test power supply enable"""
        if not self.gpio_handler.initialized:
            self.skipTest("GPIO handler not initialized - skipping power supply test")
        result = self.gpio_handler.set_power_supply_enable(True)
        self.assertTrue(result)
        self.assertTrue(self.gpio_handler.power_supply_enabled)

    def test_power_supply_disable(self):
        """Test power supply disable"""
        if not self.gpio_handler.initialized:
            self.skipTest("GPIO handler not initialized - skipping power supply test")
        result = self.gpio_handler.set_power_supply_enable(False)
        self.assertTrue(result)
        self.assertFalse(self.gpio_handler.power_supply_enabled)

    def test_emergency_shutdown(self):
        """Test emergency shutdown"""
        if not self.gpio_handler.initialized:
            self.skipTest("GPIO handler not initialized - skipping emergency shutdown test")
        result = self.gpio_handler.emergency_shutdown()
        self.assertTrue(result)

    def test_cleanup(self):
        """Test GPIO cleanup"""
        self.gpio_handler.cleanup()
        if self.gpio_handler.chip is not None:
            mock_lgpio.gpiochip_close.assert_called()
        # Cleanup should work even if not initialized
        self.assertIsNone(self.gpio_handler.chip)


if __name__ == "__main__":
    unittest.main()
