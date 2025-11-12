"""
Unit tests for Command Processor module
Tests command parsing, routing, and execution
"""
import unittest
from unittest.mock import Mock, MagicMock
import sys
import os

# Add Target_Codebase to path to import target codebase modules
target_codebase_path = os.path.join(os.path.dirname(__file__), '..', 'Target_Codebase')
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
sys.modules['Adafruit_GPIO'].SPI = mock_spi
sys.modules['Adafruit_MCP3008'] = mock_mcp3008

# Import after path setup and mocking (direct import since path is added)
from command_processor import CommandProcessor
from gpio_handler import GPIOHandler


class TestCommandProcessor(unittest.TestCase):
    """Test cases for CommandProcessor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock GPIO handler
        self.mock_gpio = MagicMock()
        self.mock_gpio.led_on.return_value = True
        self.mock_gpio.led_off.return_value = True
        self.mock_gpio.read_input.return_value = 1
        
        # Mock ADC
        self.mock_adc = MagicMock()
        self.mock_adc.is_initialized.return_value = True
        self.mock_adc.read_all_channels.return_value = [512, 256, 128, 64, 32, 16, 8, 4]
        
        self.processor = CommandProcessor(
            gpio_handler=self.mock_gpio,
            adc=self.mock_adc
        )
    
    def test_led_on_command(self):
        """Test LED_ON command"""
        response = self.processor.process_command("LED_ON")
        self.assertEqual(response, "LED_ON_SUCCESS")
        self.mock_gpio.led_on.assert_called_once()
        print("✓ test_led_on_command: PASSED")
    
    def test_led_off_command(self):
        """Test LED_OFF command"""
        response = self.processor.process_command("LED_OFF")
        self.assertEqual(response, "LED_OFF_SUCCESS")
        self.mock_gpio.led_off.assert_called_once()
        print("✓ test_led_off_command: PASSED")
    
    def test_read_input_command(self):
        """Test READ_INPUT command"""
        response = self.processor.process_command("READ_INPUT")
        self.assertTrue(response.startswith("INPUT_VALUE:"))
        self.mock_gpio.read_input.assert_called_once()
        print("✓ test_read_input_command: PASSED")
    
    def test_read_adc_command(self):
        """Test READ_ADC command"""
        response = self.processor.process_command("READ_ADC")
        self.assertTrue(response.startswith("ADC_DATA:"))
        self.mock_adc.read_all_channels.assert_called_once()
        print("✓ test_read_adc_command: PASSED")
    
    def test_set_voltage_command(self):
        """Test SET_VOLTAGE command"""
        response = self.processor.process_command("SET_VOLTAGE:5000")
        self.assertEqual(response, "SET_VOLTAGE_SUCCESS:5000")
        print("✓ test_set_voltage_command: PASSED")
    
    def test_set_pump_power_command(self):
        """Test SET_PUMP_POWER command"""
        response = self.processor.process_command("SET_PUMP_POWER:75")
        self.assertEqual(response, "SET_PUMP_POWER_SUCCESS:75")
        print("✓ test_set_pump_power_command: PASSED")
    
    def test_set_pump_power_invalid_range(self):
        """Test SET_PUMP_POWER with invalid range"""
        response = self.processor.process_command("SET_PUMP_POWER:150")
        self.assertTrue("FAILED" in response)
        print("✓ test_set_pump_power_invalid_range: PASSED")
    
    def test_move_var_command(self):
        """Test MOVE_VAR command"""
        response = self.processor.process_command("MOVE_VAR:100")
        self.assertEqual(response, "MOVE_VAR_SUCCESS:100")
        print("✓ test_move_var_command: PASSED")
    
    def test_unknown_command(self):
        """Test unknown command handling"""
        response = self.processor.process_command("UNKNOWN_COMMAND")
        self.assertTrue("ERROR" in response)
        print("✓ test_unknown_command: PASSED")
    
    def test_empty_command(self):
        """Test empty command handling"""
        response = self.processor.process_command("")
        self.assertTrue("ERROR" in response)
        print("✓ test_empty_command: PASSED")
    
    def test_command_case_insensitive(self):
        """Test command case insensitivity"""
        response = self.processor.process_command("led_on")
        self.assertEqual(response, "LED_ON_SUCCESS")
        print("✓ test_command_case_insensitive: PASSED")
    
    def test_command_with_whitespace(self):
        """Test command with leading/trailing whitespace"""
        response = self.processor.process_command("  LED_ON  ")
        self.assertEqual(response, "LED_ON_SUCCESS")
        print("✓ test_command_with_whitespace: PASSED")


if __name__ == '__main__':
    print("=" * 60)
    print("Command Processor Unit Tests")
    print("=" * 60)
    unittest.main(verbosity=2)

