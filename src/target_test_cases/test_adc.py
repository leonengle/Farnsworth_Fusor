"""
Unit tests for ADC (MCP3008) module
Tests ADC initialization, channel reading, and validation
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add Target_Codebase to path to import target codebase modules
target_codebase_path = os.path.join(os.path.dirname(__file__), "..", "Target_Codebase")
sys.path.insert(0, target_codebase_path)

# Mock Adafruit libraries and RPi.GPIO (required for non-RPi environments)
# Must mock before importing adc module
mock_spi = MagicMock()
mock_spi_dev = MagicMock()
mock_spi.SpiDev = MagicMock(return_value=mock_spi_dev)

mock_mcp3008 = MagicMock()
mock_mcp_instance = MagicMock()
mock_mcp_instance.read_adc.return_value = 512
mock_mcp3008.MCP3008 = MagicMock(return_value=mock_mcp_instance)

mock_gpio = MagicMock()
mock_gpio.BCM = 11
mock_gpio.OUT = 0
mock_gpio.HIGH = 1
mock_gpio.LOW = 0

sys.modules["Adafruit_GPIO"] = MagicMock()
sys.modules["Adafruit_GPIO"].SPI = mock_spi
sys.modules["Adafruit_MCP3008"] = mock_mcp3008
sys.modules["RPi"] = MagicMock()
sys.modules["RPi.GPIO"] = mock_gpio

# Import after path setup and mocking (direct import since path is added)
from adc import MCP3008ADC


class TestMCP3008ADC(unittest.TestCase):
    """Test cases for MCP3008ADC class"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock is already set up at module level
        # Create a fresh ADC instance for each test
        self.adc = MCP3008ADC(spi_port=0, spi_device=0)
        # Manually set mcp for testing since initialize will fail without real hardware
        self.adc.mcp = MagicMock()
        self.adc.mcp.read_adc.return_value = 512
        self.adc._is_initialized = True

    def test_initialization(self):
        """Test ADC initialization"""
        # Create a fresh ADC instance and test initialization
        # The mocks are already set up at module level
        test_adc = MCP3008ADC(spi_port=0, spi_device=0)
        result = test_adc.initialize()
        # With mocked libraries, initialization should succeed
        self.assertTrue(result)
        self.assertTrue(test_adc.is_initialized())
        print("✓ test_initialization: PASSED")

    def test_validate_channel_valid(self):
        """Test channel validation with valid channels"""
        self.assertTrue(self.adc.validate_channel(0))
        self.assertTrue(self.adc.validate_channel(7))
        self.assertTrue(self.adc.validate_channel(4))
        print("✓ test_validate_channel_valid: PASSED")

    def test_validate_channel_invalid(self):
        """Test channel validation with invalid channels"""
        self.assertFalse(self.adc.validate_channel(-1))
        self.assertFalse(self.adc.validate_channel(8))
        self.assertFalse(self.adc.validate_channel(10))
        print("✓ test_validate_channel_invalid: PASSED")

    def test_read_channel(self):
        """Test reading single ADC channel"""
        self.adc.initialize()
        value = self.adc.read_channel(0)
        self.assertIsInstance(value, int)
        self.assertGreaterEqual(value, 0)
        self.assertLessEqual(value, 1023)
        print("✓ test_read_channel: PASSED")

    def test_read_channel_uninitialized(self):
        """Test reading channel when ADC not initialized"""
        self.adc._is_initialized = False
        value = self.adc.read_channel(0)
        self.assertEqual(value, 0)
        print("✓ test_read_channel_uninitialized: PASSED")

    def test_read_all_channels(self):
        """Test reading all ADC channels"""
        self.adc.initialize()
        values = self.adc.read_all_channels()
        self.assertEqual(len(values), 8)
        for value in values:
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 1023)
        print("✓ test_read_all_channels: PASSED")

    def test_read_multiple_channels(self):
        """Test reading multiple specific channels"""
        self.adc.initialize()
        channels = [0, 2, 5]
        values = self.adc.read_multiple_channels(channels)
        self.assertEqual(len(values), 3)
        print("✓ test_read_multiple_channels: PASSED")

    def test_convert_to_voltage(self):
        """Test ADC value to voltage conversion"""
        # Test with 512 (midpoint) should be ~1.65V
        voltage = self.adc.convert_to_voltage(512, 3.3)
        self.assertAlmostEqual(voltage, 1.65, places=2)

        # Test with 0 should be 0V
        voltage = self.adc.convert_to_voltage(0, 3.3)
        self.assertEqual(voltage, 0.0)

        # Test with 1023 (max) should be ~3.3V
        voltage = self.adc.convert_to_voltage(1023, 3.3)
        self.assertAlmostEqual(voltage, 3.3, places=2)
        print("✓ test_convert_to_voltage: PASSED")

    def test_cleanup(self):
        """Test ADC cleanup"""
        self.adc.initialize()
        self.adc.cleanup()
        self.assertFalse(self.adc.is_initialized())
        self.assertIsNone(self.adc.mcp)
        print("✓ test_cleanup: PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("ADC (MCP3008) Unit Tests")
    print("=" * 60)
    unittest.main(verbosity=2)
