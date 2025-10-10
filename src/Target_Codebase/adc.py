import time
import sys
import RPi.GPIO as GPIO
from Adafruit_GPIO import SPI
import Adafruit_MCP3008
import argparse
from base_classes import ADCInterface

PIN = 16
PIN2 = 23 
PIN3 = 26
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.OUT)
GPIO.setup(PIN2, GPIO.OUT)
GPIO.setup(PIN3, GPIO.OUT)
HW_SPI_PORT = 0
HW_SPI_DEV = 0

class MCP3008ADC(ADCInterface):
    """MCP3008 ADC implementation."""
    
    def __init__(self, spi_port=0, spi_device=0):
        super().__init__(spi_port, spi_device)
        self.mcp = None
    
    def initialize(self):
        """Initialize the ADC hardware."""
        try:
            self.mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(self.spi_port, self.spi_device))
            self._is_initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize ADC: {e}")
            return False
    
    def read_channel(self, channel):
        """Read a single ADC channel."""
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
        """Read multiple ADC channels."""
        if not self._is_initialized:
            print("ADC not initialized")
            return [0] * len(channels)
        
        results = []
        for channel in channels:
            results.append(self.read_channel(channel))
        return results
    
    def read_all_channels(self):
        """Read all available ADC channels."""
        return self.read_multiple_channels(list(range(8)))
    
    def convert_to_voltage(self, adc_value, reference_voltage=3.3):
        """Convert ADC reading to voltage."""
        return (adc_value / 1023.0) * reference_voltage
    
    def cleanup(self):
        """Clean up ADC resources."""
        self._is_initialized = False
        self.mcp = None

# Global instance for backward compatibility
mcp_instance = MCP3008ADC(HW_SPI_PORT, HW_SPI_DEV)
mcp_instance.initialize()
mcp = mcp_instance.mcp

def validate_channel(channel: int):
    """Ensure channel is between 0 and 7."""
    if channel < 0 or channel > 7:
        print("ERROR: Value must be between 0 and 7!", file=sys.stderr)
        sys.exit(1)

def read_adc(channel: int):
    """Read from the specified ADC channel repeatedly."""
    validate_channel(channel)
    try:
        while True:
            value = mcp.read_adc(channel)
            if value > 0 and value < 341:
                GPIO.output(PIN,GPIO.HIGH)
                GPIO.output(PIN2,GPIO.LOW)
                GPIO.output(PIN3,GPIO.LOW)
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
        GPIO.cleanup()
        print("\nExiting")

def main():
    parser = argparse.ArgumentParser(description="Read MCP3008 ADC channel repeatedly.")
    parser.add_argument("channel", type=int, help="ADC channel number (0-7)")
    args = parser.parse_args()
    read_adc(args.channel)

if __name__ == "__main__":
    main()
