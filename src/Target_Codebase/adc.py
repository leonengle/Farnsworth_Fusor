import time
import sys
import argparse
from base_classes import ADCInterface

# Only import RPi libraries when not in test mode
try:
    import RPi.GPIO as GPIO
    from Adafruit_GPIO import SPI
    import Adafruit_MCP3008

    RPI_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    # Mock modules for testing
    RPI_AVAILABLE = False
    GPIO = None
    SPI = None
    Adafruit_MCP3008 = None

PIN = 16
PIN2 = 23
PIN3 = 26

HW_SPI_PORT = 0
HW_SPI_DEV = 0

# Setup GPIO pins only if RPi is available and not in test mode
if RPI_AVAILABLE and GPIO is not None:
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PIN, GPIO.OUT)
        GPIO.setup(PIN2, GPIO.OUT)
        GPIO.setup(PIN3, GPIO.OUT)
    except Exception:
        pass  # Fail silently in test environments


class MCP3008ADC(ADCInterface):
    def __init__(self, spi_port=0, spi_device=0):
        super().__init__(spi_port, spi_device)
        self.mcp = None

    def initialize(self):
        if not RPI_AVAILABLE or Adafruit_MCP3008 is None or SPI is None:
            print("ADC libraries not available (likely in test environment)")
            return False
        try:
            self.mcp = Adafruit_MCP3008.MCP3008(
                spi=SPI.SpiDev(self.spi_port, self.spi_device)
            )
            self._is_initialized = True
            print("MCP3008 ADC initialized successfully")
            return True
        except Exception as e:
            print(f"Failed to initialize ADC: {e}")
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
    if not validate_channel(channel):
        return

    current_mcp = get_mcp_instance() if RPI_AVAILABLE else None
    if current_mcp is None:
        print("ADC not available - cannot read")
        return

    if not RPI_AVAILABLE or GPIO is None:
        print("GPIO not available - cannot control LEDs")
        return

    try:
        while True:
            value = current_mcp.read_adc(channel)
            if value > 0 and value < 341:
                GPIO.output(PIN, GPIO.HIGH)
                GPIO.output(PIN2, GPIO.LOW)
                GPIO.output(PIN3, GPIO.LOW)
            elif value >= 341 and value < 682:
                GPIO.output(PIN, GPIO.LOW)
                GPIO.output(PIN2, GPIO.HIGH)
                GPIO.output(PIN3, GPIO.LOW)
            elif value >= 682 and value <= 1023:
                GPIO.output(PIN, GPIO.LOW)
                GPIO.output(PIN2, GPIO.LOW)
                GPIO.output(PIN3, GPIO.HIGH)
            print(f"Value: {value}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        if GPIO is not None:
            GPIO.cleanup()
        print("\nExiting")


def main():
    parser = argparse.ArgumentParser(description="Read MCP3008 ADC channel repeatedly.")
    parser.add_argument("channel", type=int, help="ADC channel number (0-7)")
    args = parser.parse_args()
    read_adc(args.channel)


if __name__ == "__main__":
    main()
