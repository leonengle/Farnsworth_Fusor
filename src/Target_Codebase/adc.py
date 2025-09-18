import time
import sys
import RPi.GPIO as GPIO
from Adafruit_GPIO import SPI
import Adafruit_MCP3008
import argparse

PIN = 16
PIN2 = 23 
PIN3 = 26
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.OUT)
GPIO.setup(PIN2, GPIO.OUT)
GPIO.setup(PIN3, GPIO.OUT)
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
