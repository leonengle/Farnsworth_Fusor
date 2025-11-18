import time
import sys
import argparse
from base_classes import ADCInterface
from logging_setup import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger("MCP3008ADC")

# Only import RPi libraries when not in test mode
try:
    import lgpio
    from Adafruit_GPIO import SPI
    import Adafruit_MCP3008

    RPI_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    # Mock modules for testing
    RPI_AVAILABLE = False
    lgpio = None
    SPI = None
    Adafruit_MCP3008 = None

PIN = 16
PIN2 = 23
PIN3 = 26

HW_SPI_PORT = 0
HW_SPI_DEV = 0

# GPIO chip handle for LED control (optional, only used in test functions)
# GPIO pins should NOT be claimed here at import time — GPIOHandler manages all GPIO.
# This prevents GPIO conflicts (e.g., PIN3=26 conflicts with LED pin in GPIOHandler)
_gpio_chip = None


class MCP3008ADC(ADCInterface):
    def __init__(self, spi_port=0, spi_device=0):
        super().__init__(spi_port, spi_device)
        self.mcp = None

    def initialize(self):
        if not RPI_AVAILABLE or Adafruit_MCP3008 is None or SPI is None:
            logger.error("ADC libraries not available (likely in test environment)")
            return False
        
        # Check SPI device permissions before attempting initialization
        import os
        spi_device_path = f"/dev/spidev{self.spi_port}.{self.spi_device}"
        
        if not os.path.exists(spi_device_path):
            logger.error(f"ADC error: SPI device {spi_device_path} not found")
            logger.error("SPI interface may not be enabled. Enable it with: sudo raspi-config")
            logger.error("  Navigate to: Interface Options -> SPI -> Enable")
            return False
        
        # Check permissions (even as root, this helps diagnose issues)
        try:
            if not os.access(spi_device_path, os.R_OK | os.W_OK):
                logger.error(f"ADC error: Cannot access SPI device {spi_device_path}")
                logger.error(f"Try: sudo chmod 666 {spi_device_path}")
                return False
        except Exception as perm_err:
            logger.error(f"ADC permission check error: {perm_err}")
        
        try:
            logger.info(f"Attempting to initialize MCP3008 ADC on {spi_device_path}")
            self.mcp = Adafruit_MCP3008.MCP3008(
                spi=SPI.SpiDev(self.spi_port, self.spi_device)
            )
            self._is_initialized = True
            logger.info("MCP3008 ADC initialized successfully")
            return True
        except PermissionError as e:
            logger.error(f"ADC permission error: {e}")
            logger.error(f"SPI device {spi_device_path} requires proper permissions")
            logger.error(f"Try: sudo chmod 666 {spi_device_path}")
            logger.error("Or ensure SPI is enabled: sudo raspi-config -> Interface Options -> SPI")
            return False
        except OSError as e:
            logger.error(f"ADC OS error: {e}")
            logger.error("This usually means SPI interface is not enabled or hardware is not connected")
            logger.error("Enable SPI with: sudo raspi-config -> Interface Options -> SPI -> Enable")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize ADC: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error("Check:")
            logger.error("  1. SPI is enabled: sudo raspi-config")
            logger.error("  2. MCP3008 is properly wired to SPI0 (CE0 or CE1)")
            logger.error("  3. Adafruit_MCP3008 library is installed")
            return False

    def read_channel(self, channel):
        if not self._is_initialized:
            print("ADC not initialized")
            return 0

        if not self.validate_channel(channel):
            print(f"Invalid channel: {channel}")
            return 0

        try:
            return self.mcp.read_adc(channel)
        except Exception as e:
            print(f"Error reading channel {channel}: {e}")
            return 0

    def read_multiple_channels(self, channels):
        if not self._is_initialized:
            print("ADC not initialized")
            return [0] * len(channels)

        results = []
        for channel in channels:
            results.append(self.read_channel(channel))
        return results

    def read_all_channels(self):
        return self.read_multiple_channels(list(range(8)))

    def convert_to_voltage(self, adc_value, reference_voltage=3.3):
        return (adc_value / 1023.0) * reference_voltage

    def cleanup(self):
        self._is_initialized = False
        self.mcp = None


# Global instance for backward compatibility (lazy initialization)
_mcp_instance = None
_mcp = None


def get_mcp_instance():
    """Get or create global MCP instance (lazy initialization)"""
    global _mcp_instance, _mcp
    if _mcp_instance is None:
        _mcp_instance = MCP3008ADC(HW_SPI_PORT, HW_SPI_DEV)
        if _mcp_instance.initialize():
            _mcp = _mcp_instance.mcp
        else:
            _mcp = None
            print("Warning: ADC initialization failed")
    return _mcp


# For backward compatibility, try to initialize if RPi is available
# Use lazy initialization to avoid issues during import
try:
    if RPI_AVAILABLE:
        mcp = get_mcp_instance()
    else:
        mcp = None
except Exception:
    # Fail silently during import if initialization fails
    mcp = None


def validate_channel(channel: int):
    if channel < 0 or channel > 7:
        print("ERROR: Value must be between 0 and 7!", file=sys.stderr)
        return False
    return True


def read_adc(channel: int):
    """
    Standalone test function to read ADC and control LEDs.
    NOTE: This function sets up its own GPIO chip and pins.
    It should NOT be used when GPIOHandler is active (GPIO conflicts).
    """
    if not validate_channel(channel):
        return

    current_mcp = get_mcp_instance() if RPI_AVAILABLE else None
    if current_mcp is None:
        print("ADC not available - cannot read")
        return

    if not RPI_AVAILABLE or lgpio is None:
        print("GPIO not available - cannot control LEDs")
        return

    # Set up GPIO chip and pins only when this function is called (not at import time)
    global _gpio_chip
    try:
        _gpio_chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(_gpio_chip, PIN, 0)
        lgpio.gpio_claim_output(_gpio_chip, PIN2, 0)
        lgpio.gpio_claim_output(_gpio_chip, PIN3, 0)
    except Exception as e:
        print(f"Warning: Could not set up GPIO for LED control: {e}")
        print("Note: This function conflicts with GPIOHandler if both are active")
        return

    try:
        while True:
            value = current_mcp.read_adc(channel)
            if value > 0 and value < 341:
                lgpio.gpio_write(_gpio_chip, PIN, 1)
                lgpio.gpio_write(_gpio_chip, PIN2, 0)
                lgpio.gpio_write(_gpio_chip, PIN3, 0)
            elif value >= 341 and value < 682:
                lgpio.gpio_write(_gpio_chip, PIN, 0)
                lgpio.gpio_write(_gpio_chip, PIN2, 1)
                lgpio.gpio_write(_gpio_chip, PIN3, 0)
            elif value >= 682 and value <= 1023:
                lgpio.gpio_write(_gpio_chip, PIN, 0)
                lgpio.gpio_write(_gpio_chip, PIN2, 0)
                lgpio.gpio_write(_gpio_chip, PIN3, 1)
            print(f"Value: {value}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        if lgpio is not None and _gpio_chip is not None:
            try:
                lgpio.gpio_free(_gpio_chip, PIN)
                lgpio.gpio_free(_gpio_chip, PIN2)
                lgpio.gpio_free(_gpio_chip, PIN3)
                lgpio.gpiochip_close(_gpio_chip)
                _gpio_chip = None
            except Exception:
                pass
        print("\nExiting")


def main():
    parser = argparse.ArgumentParser(description="Read MCP3008 ADC channel repeatedly.")
    parser.add_argument("channel", type=int, help="ADC channel number (0-7)")
    args = parser.parse_args()
    read_adc(args.channel)


if __name__ == "__main__":
    main()
