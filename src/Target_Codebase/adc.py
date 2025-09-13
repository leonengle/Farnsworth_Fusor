import time
import sys
from Adafruit_GPIO import SPI
import Adafruit_MCP3008
import argparse

HW_SPI_PORT = 0
HW_SPI_DEV = 0
mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(HW_SPI_PORT, HW_SPI_DEV))

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
            print(f"Value: {value}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nExiting")

def main():
    parser = argparse.ArgumentParser(description="Read MCP3008 ADC channel repeatedly.")
    parser.add_argument("channel", type=int, help="ADC channel number (0-7)")
    args = parser.parse_args()
    read_adc(args.channel)

if __name__ == "__main__":
    main()