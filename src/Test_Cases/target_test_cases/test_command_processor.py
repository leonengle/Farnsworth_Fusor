"""
Unit tests for Command Processor module
Tests command parsing, routing, and execution
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add Target_Codebase to path to import target codebase modules
target_codebase_path = os.path.join(os.path.dirname(__file__), "..", "..", "Target_Codebase")
sys.path.insert(0, target_codebase_path)

# Mock RPi.GPIO and Adafruit libraries before importing (required for non-RPi environments)
mock_gpio = MagicMock()
mock_gpio.BCM = 11
mock_gpio.OUT = 0
mock_gpio.IN = 1
mock_gpio.HIGH = 1
mock_gpio.LOW = 0
mock_gpio.PUD_DOWN = 21

mock_spi = MagicMock()
mock_spi_dev = MagicMock()
mock_spi.SpiDev = MagicMock(return_value=mock_spi_dev)

mock_mcp3008 = MagicMock()
mock_mcp_instance = MagicMock()
mock_mcp3008.MCP3008 = MagicMock(return_value=mock_mcp_instance)

sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = mock_gpio
sys.modules['Adafruit_GPIO'] = MagicMock()
sys.modules['Adafruit_GPIO.SPI'] = mock_spi
sys.modules['Adafruit_MCP3008'] = mock_mcp3008

# Mock logging_setup
mock_logging_setup = MagicMock()
mock_logger = MagicMock()
mock_logging_setup.get_logger = MagicMock(return_value=mock_logger)
mock_logging_setup.setup_logging = MagicMock()
sys.modules['logging_setup'] = mock_logging_setup

from gpio_handler import GPIOHandler
from command_processor import CommandProcessor


class TestCommandProcessor(unittest.TestCase):
    """Test cases for CommandProcessor"""

    def setUp(self):
        """Set up test fixtures"""
        mock_gpio.reset_mock()
        self.patcher = patch('gpio_handler.GPIO', mock_gpio)
        self.patcher.start()
        self.gpio_handler = GPIOHandler()
        self.command_processor = CommandProcessor(
            gpio_handler=self.gpio_handler,
            adc=None,
            arduino_interface=None
        )

    def tearDown(self):
        """Clean up after tests"""
        self.patcher.stop()

    def test_empty_command(self):
        """Test processing empty command"""
        result = self.command_processor.process_command("")
        self.assertEqual(result, "ERROR: Empty command")

    def test_led_on_command(self):
        """Test LED ON command"""
        result = self.command_processor.process_command("LED_ON")
        self.assertIn("LED_ON", result)

    def test_led_off_command(self):
        """Test LED OFF command"""
        result = self.command_processor.process_command("LED_OFF")
        self.assertIn("LED_OFF", result)

    def test_power_supply_enable_command(self):
        """Test power supply enable command"""
        result = self.command_processor.process_command("POWER_SUPPLY_ENABLE")
        self.assertIn("POWER_SUPPLY", result)

    def test_power_supply_disable_command(self):
        """Test power supply disable command"""
        result = self.command_processor.process_command("POWER_SUPPLY_DISABLE")
        self.assertIn("POWER_SUPPLY", result)

    def test_set_voltage_command(self):
        """Test SET_VOLTAGE command"""
        result = self.command_processor.process_command("SET_VOLTAGE:10.5")
        self.assertIn("SET_VOLTAGE", result)

    def test_set_valve_command(self):
        """Test SET_VALVE command"""
        result = self.command_processor.process_command("SET_VALVE1:50")
        self.assertIn("SET_VALVE", result)

    def test_set_mechanical_pump_command(self):
        """Test SET_MECHANICAL_PUMP command"""
        result = self.command_processor.process_command("SET_MECHANICAL_PUMP:75")
        self.assertIn("SET_MECHANICAL_PUMP", result)

    def test_set_turbo_pump_command(self):
        """Test SET_TURBO_PUMP command"""
        result = self.command_processor.process_command("SET_TURBO_PUMP:80")
        self.assertIn("SET_TURBO_PUMP", result)

    def test_analog_command_forwarded_to_arduino(self):
        """Ensure analog commands are labeled and forwarded to Arduino"""
        mock_arduino = MagicMock()
        mock_arduino.is_connected.return_value = True
        processor = CommandProcessor(
            gpio_handler=self.gpio_handler,
            adc=None,
            arduino_interface=mock_arduino,
        )
        processor.process_command("SET_VALVE1:60")
        mock_arduino.send_analog_command.assert_called_with("ATM_DEPRESSURE_VALVE", 60)

    def test_startup_command(self):
        """Test STARTUP command"""
        result = self.command_processor.process_command("STARTUP")
        self.assertIn("STARTUP", result)

    def test_shutdown_command(self):
        """Test SHUTDOWN command"""
        result = self.command_processor.process_command("SHUTDOWN")
        self.assertIn("SHUTDOWN", result)

    def test_emergency_shutoff_command(self):
        """Test EMERGENCY_SHUTOFF command"""
        result = self.command_processor.process_command("EMERGENCY_SHUTOFF")
        self.assertIn("EMERGENCY_SHUTOFF", result)

    def test_invalid_command(self):
        """Test invalid command"""
        result = self.command_processor.process_command("INVALID_COMMAND")
        self.assertIn("ERROR", result)

    def test_set_valve_invalid_format(self):
        """Test SET_VALVE with invalid format"""
        result = self.command_processor.process_command("SET_VALVE1")
        self.assertIn("FAILED", result)

    def test_set_voltage_invalid_format(self):
        """Test SET_VOLTAGE with invalid format"""
        result = self.command_processor.process_command("SET_VOLTAGE:")
        self.assertIn("FAILED", result)


if __name__ == "__main__":
    unittest.main()

