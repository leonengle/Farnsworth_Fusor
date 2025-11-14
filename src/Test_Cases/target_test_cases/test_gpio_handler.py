"""
Unit tests for GPIO Handler module
Tests GPIO operations including LED, valves, pumps, and power supply control
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add Target_Codebase to path to import target codebase modules
target_codebase_path = os.path.join(os.path.dirname(__file__), "..", "..", "Target_Codebase")
sys.path.insert(0, target_codebase_path)

# Mock RPi.GPIO before importing gpio_handler (required for non-RPi environments)
mock_gpio = MagicMock()
mock_gpio.BCM = 11
mock_gpio.OUT = 0
mock_gpio.IN = 1
mock_gpio.HIGH = 1
mock_gpio.LOW = 0
mock_gpio.PUD_DOWN = 21

sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = mock_gpio

# Mock logging_setup
mock_logging_setup = MagicMock()
mock_logger = MagicMock()
mock_logging_setup.get_logger = MagicMock(return_value=mock_logger)
mock_logging_setup.setup_logging = MagicMock()
sys.modules['logging_setup'] = mock_logging_setup

from gpio_handler import GPIOHandler


class TestGPIOHandler(unittest.TestCase):
    """Test cases for GPIOHandler"""

    def setUp(self):
        """Set up test fixtures"""
        with patch('gpio_handler.GPIO', mock_gpio):
            self.gpio_handler = GPIOHandler(
                led_pin=26,
                input_pin=6,
                power_supply_pin=5,
                valve_pins=[17, 4, 22, 23, 24, 25],
                mechanical_pump_pin=27,
                turbo_pump_pin=16
            )

    def test_initialization(self):
        """Test GPIO handler initialization"""
        self.assertTrue(self.gpio_handler.initialized)
        self.assertEqual(self.gpio_handler.led_pin, 26)
        self.assertEqual(self.gpio_handler.input_pin, 6)
        self.assertEqual(self.gpio_handler.power_supply_pin, 5)
        self.assertEqual(len(self.gpio_handler.valve_pins), 6)
        self.assertEqual(self.gpio_handler.mechanical_pump_pin, 27)
        self.assertEqual(self.gpio_handler.turbo_pump_pin, 16)

    def test_led_on(self):
        """Test LED ON functionality"""
        result = self.gpio_handler.led_on()
        self.assertTrue(result)
        mock_gpio.output.assert_called()

    def test_led_off(self):
        """Test LED OFF functionality"""
        result = self.gpio_handler.led_off()
        self.assertTrue(result)
        mock_gpio.output.assert_called()

    def test_read_input(self):
        """Test reading input pin"""
        mock_gpio.input.return_value = 1
        result = self.gpio_handler.read_input()
        self.assertEqual(result, 1)
        mock_gpio.input.assert_called_with(6)

    def test_power_supply_enable(self):
        """Test power supply enable"""
        result = self.gpio_handler.set_power_supply_enable(True)
        self.assertTrue(result)
        self.assertTrue(self.gpio_handler.power_supply_enabled)

    def test_power_supply_disable(self):
        """Test power supply disable"""
        result = self.gpio_handler.set_power_supply_enable(False)
        self.assertTrue(result)
        self.assertFalse(self.gpio_handler.power_supply_enabled)

    def test_set_valve_position(self):
        """Test setting valve position"""
        result = self.gpio_handler.set_valve_position(1, 50)
        self.assertTrue(result)
        self.assertEqual(self.gpio_handler.valve_states[0], 50)

    def test_set_valve_position_invalid_id(self):
        """Test setting valve position with invalid ID"""
        result = self.gpio_handler.set_valve_position(0, 50)
        self.assertFalse(result)
        result = self.gpio_handler.set_valve_position(7, 50)
        self.assertFalse(result)

    def test_set_valve_position_invalid_position(self):
        """Test setting valve position with invalid position"""
        result = self.gpio_handler.set_valve_position(1, -1)
        self.assertFalse(result)
        result = self.gpio_handler.set_valve_position(1, 101)
        self.assertFalse(result)

    def test_set_mechanical_pump_power(self):
        """Test setting mechanical pump power"""
        result = self.gpio_handler.set_mechanical_pump_power(75)
        self.assertTrue(result)
        self.assertEqual(self.gpio_handler.mechanical_pump_power, 75)

    def test_set_turbo_pump_power(self):
        """Test setting turbo pump power"""
        result = self.gpio_handler.set_turbo_pump_power(80)
        self.assertTrue(result)
        self.assertEqual(self.gpio_handler.turbo_pump_power, 80)

    def test_emergency_shutdown(self):
        """Test emergency shutdown"""
        result = self.gpio_handler.emergency_shutdown()
        self.assertTrue(result)

    def test_cleanup(self):
        """Test GPIO cleanup"""
        self.gpio_handler.cleanup()
        mock_gpio.cleanup.assert_called()


if __name__ == "__main__":
    unittest.main()

