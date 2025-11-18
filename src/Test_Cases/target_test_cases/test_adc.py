"""
Unit tests for MCP3008 ADC module
Tests ADC initialization, channel reading, and voltage conversion
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add Target_Codebase to path to import target codebase modules
target_codebase_path = os.path.join(os.path.dirname(__file__), "..", "..", "Target_Codebase")
sys.path.insert(0, target_codebase_path)

# Mock Adafruit libraries and lgpio (required for non-RPi environments)
# Must mock before importing adc module
mock_spi = MagicMock()
mock_spi_dev = MagicMock()
mock_spi.SpiDev = MagicMock(return_value=mock_spi_dev)

mock_mcp3008 = MagicMock()
mock_mcp_instance = MagicMock()
mock_mcp_instance.read_adc = MagicMock(return_value=512)
mock_mcp3008.MCP3008 = MagicMock(return_value=mock_mcp_instance)

mock_lgpio = MagicMock()
mock_lgpio.gpiochip_open = MagicMock(return_value=0)
mock_lgpio.gpio_claim_output = MagicMock(return_value=0)
mock_lgpio.gpio_write = MagicMock(return_value=0)
mock_lgpio.gpio_free = MagicMock(return_value=0)
mock_lgpio.gpiochip_close = MagicMock(return_value=0)

sys.modules['lgpio'] = mock_lgpio
sys.modules['Adafruit_GPIO'] = MagicMock()
sys.modules['Adafruit_GPIO.SPI'] = mock_spi
sys.modules['Adafruit_MCP3008'] = mock_mcp3008

from adc import MCP3008ADC


class TestMCP3008ADC(unittest.TestCase):
    """Test cases for MCP3008ADC"""

    def setUp(self):
        """Set up test fixtures"""
        with patch('adc.RPI_AVAILABLE', False):
            self.adc = MCP3008ADC()

    def test_initialization(self):
        """Test ADC initialization"""
        self.assertIsNotNone(self.adc)
        self.assertEqual(self.adc.spi_port, 0)
        self.assertEqual(self.adc.spi_device, 0)

    def test_validate_channel_valid(self):
        """Test channel validation with valid channels"""
        self.assertTrue(self.adc.validate_channel(0))
        self.assertTrue(self.adc.validate_channel(7))
        self.assertTrue(self.adc.validate_channel(4))

    def test_validate_channel_invalid(self):
        """Test channel validation with invalid channels"""
        self.assertFalse(self.adc.validate_channel(-1))
        self.assertFalse(self.adc.validate_channel(8))
        self.assertFalse(self.adc.validate_channel(10))

    def test_convert_to_voltage(self):
        """Test ADC value to voltage conversion"""
        adc_value = 512
        voltage = self.adc.convert_to_voltage(adc_value)
        expected_voltage = (512 / 1023.0) * 3.3
        self.assertAlmostEqual(voltage, expected_voltage, places=2)

    def test_convert_to_voltage_zero(self):
        """Test voltage conversion with zero ADC value"""
        voltage = self.adc.convert_to_voltage(0)
        self.assertEqual(voltage, 0.0)

    def test_convert_to_voltage_max(self):
        """Test voltage conversion with max ADC value"""
        voltage = self.adc.convert_to_voltage(1023)
        expected_voltage = (1023 / 1023.0) * 3.3
        self.assertAlmostEqual(voltage, expected_voltage, places=2)

    def test_read_channel_not_initialized(self):
        """Test reading channel when ADC is not initialized"""
        result = self.adc.read_channel(0)
        self.assertEqual(result, 0)

    def test_read_multiple_channels_not_initialized(self):
        """Test reading multiple channels when ADC is not initialized"""
        result = self.adc.read_multiple_channels([0, 1, 2])
        self.assertEqual(len(result), 3)
        self.assertEqual(result, [0, 0, 0])


if __name__ == "__main__":
    unittest.main()

