# adc.py
import time
import sys
import argparse
import threading
import os
from typing import List

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
    RPI_AVAILABLE = False
    lgpio = None
    SPI = None
    Adafruit_MCP3008 = None


HW_SPI_PORT = 0
HW_SPI_DEV = 0


class MCP3008ADC(ADCInterface):
    """
    Clean, single-instance MCP3008 driver.
    - No globals / singletons
    - Thread-safe access
    - Explicit initialize() must be called once
    """

    def __init__(self, spi_port: int = HW_SPI_PORT, spi_device: int = HW_SPI_DEV):
        super().__init__(spi_port, spi_device)
        self.mcp = None
        self._mcp_lock = threading.Lock()
        self._init_lock = threading.Lock()
        self._is_initialized = False

    # ---------- Initialization ----------

    def initialize(self) -> bool:
        """Initialize SPI + MCP3008. Safe to call multiple times."""
        if not RPI_AVAILABLE or Adafruit_MCP3008 is None or SPI is None:
            logger.error("ADC libraries not available (likely in test environment)")
            return False

        spi_device_path = f"/dev/spidev{self.spi_port}.{self.spi_device}"

        if not os.path.exists(spi_device_path):
            logger.error(f"ADC error: SPI device {spi_device_path} not found")
            logger.error("SPI interface may not be enabled. Enable it with: sudo raspi-config")
            logger.error("  Interface Options -> SPI -> Enable")
            return False

        try:
            if not os.access(spi_device_path, os.R_OK | os.W_OK):
                logger.error(f"ADC error: Cannot access SPI device {spi_device_path}")
                logger.error("Try: sudo chmod 666 /dev/spidev0.0 (or correct device)")
                return False
        except Exception as perm_err:
            logger.error(f"ADC permission check error: {perm_err}")

        try:
            logger.info(f"Attempting to initialize MCP3008 ADC on {spi_device_path}")
            with self._mcp_lock:
                self.mcp = Adafruit_MCP3008.MCP3008(
                    spi=SPI.SpiDev(self.spi_port, self.spi_device)
                )
            with self._init_lock:
                self._is_initialized = True
            logger.info("MCP3008 ADC initialized successfully")
            return True
        except PermissionError as e:
            logger.error(f"ADC permission error: {e}")
            logger.error(f"SPI device {spi_device_path} requires proper permissions")
            return False
        except OSError as e:
            logger.error(f"ADC OS error: {e}")
            logger.error("Likely: SPI not enabled or hardware not wired correctly")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize ADC: {e} [{type(e).__name__}]")
            return False

    def is_initialized(self) -> bool:
        with self._init_lock:
            return self._is_initialized

    # ---------- Core reading helpers ----------

    def _validate_channel(self, channel: int) -> bool:
        if channel < 0 or channel > 7:
            logger.error(f"ADC channel out of range: {channel} (must be 0–7)")
            return False
        return True

    def read_channel(self, channel: int) -> int:
        """
        Read a single ADC channel (0–7).
        Returns an integer 0–1023.
        Returns 0 on failure, but logs the reason.
        """
        with self._init_lock:
            if not self._is_initialized:
                logger.error("ADC read attempted before initialization")
                return 0

        if not self._validate_channel(channel):
            return 0

        try:
            with self._mcp_lock:
                value = self.mcp.read_adc(channel)
            logger.debug(f"ADC read: ch{channel} -> {value}")
            return value
        except Exception as e:
            logger.error(f"Error reading ADC channel {channel}: {e}")
            return 0

    def read_multiple_channels(self, channels: List[int]) -> List[int]:
        with self._init_lock:
            if not self._is_initialized:
                logger.error("ADC multi-read attempted before initialization")
                return [0] * len(channels)

        results = []
        for ch in channels:
            results.append(self.read_channel(ch))
        return results

    def read_all_channels(self) -> List[int]:
        return self.read_multiple_channels(list(range(8)))

    def convert_to_voltage(self, adc_value: int, reference_voltage: float = 3.3) -> float:
        return (adc_value / 1023.0) * reference_voltage

    # ---------- Cleanup ----------

    def cleanup(self):
        with self._init_lock:
            self._is_initialized = False
        with self._mcp_lock:
            self.mcp = None
        logger.info("ADC cleaned up")


# --------- Simple CLI test tool (optional) ---------

def _cli_test(channel: int):
    adc = MCP3008ADC()
    if not adc.initialize():
        print("Failed to initialize ADC")
        return

    print(f"Reading MCP3008 channel {channel}. Press Ctrl+C to stop.")
    try:
        while True:
            value = adc.read_channel(channel)
            print(f"CH{channel}: {value}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        adc.cleanup()


def main():
    parser = argparse.ArgumentParser(description="Read MCP3008 ADC channel repeatedly.")
    parser.add_argument("channel", type=int, help="ADC channel number (0-7)")
    args = parser.parse_args()
    _cli_test(args.channel)


if __name__ == "__main__":
    main()
