import lgpio
import threading
from logging_setup import setup_logging, get_logger
from base_classes import GPIOInterface
from typing import Optional

setup_logging()
logger = get_logger("GPIOHandler")


class GPIOHandler(GPIOInterface):
    def __init__(
        self,
        led_pin: int = 26,
        input_pin: int = 6,
        name: str = "GPIOHandler",
        power_supply_pin: int = 5,
    ):
        super().__init__(name)
        self.led_pin = led_pin
        self.input_pin = input_pin
        self.power_supply_pin = power_supply_pin
        self.initialized = False

        self.power_supply_enabled = False

        self.chip = None
        self.claimed_pins = []

        self._state_lock = threading.Lock()
        self._chip_lock = threading.Lock()

        self._setup_gpio()

    def _setup_gpio(self):
        try:
            import os

            if os.geteuid() != 0:
                logger.warning(
                    "Not running as root - GPIO may not work properly. Try running with 'sudo'"
                )

            try:
                logger.info("DEBUG: Opening GPIO chip 0 (main GPIO chip)")
                self.chip = lgpio.gpiochip_open(0)
                logger.info(
                    f"DEBUG: GPIO chip opened successfully, chip handle: {self.chip}"
                )
            except Exception as e:
                logger.error(f"Failed to open GPIO chip: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error("This might indicate you're not running on a Raspberry Pi")
                logger.error("DEBUG: GPIO chip open failed - initialization aborted")
                self.initialized = False
                return

            logger.info(f"Claiming LED pin {self.led_pin} (BCM) as output")
            lgpio.gpio_claim_output(self.chip, self.led_pin, 0)
            self.claimed_pins.append(self.led_pin)
            logger.info(f"LED pin {self.led_pin} (BCM) successfully configured as output")

            self.initialized = True
            logger.info(f"GPIO setup complete - LED pin {self.led_pin} (BCM)")
        except Exception as e:
            logger.error(f"GPIO setup error: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(
                "GPIO initialization failed - LED and other GPIO functions will not work"
            )
            self._cleanup_on_error()
            self.initialized = False

    def _cleanup_on_error(self):
        if self.chip is not None:
            try:
                for pin in self.claimed_pins:
                    try:
                        lgpio.gpio_free(self.chip, pin)
                    except Exception:
                        pass
                lgpio.gpiochip_close(self.chip)
                self.chip = None
                self.claimed_pins = []
            except Exception as e:
                logger.debug(f"Error during cleanup: {e}")

    def led_on(self) -> tuple[bool, str]:
        with self._chip_lock:
            if not self.initialized or self.chip is None:
                error_msg = "GPIO not initialized - LED pin not configured"
                logger.error(
                    f"{error_msg} - Check logs for GPIO setup errors. Ensure target is running with 'sudo'"
                )
                return False, error_msg

            try:
                lgpio.gpio_write(self.chip, self.led_pin, 1)
                logger.info(f"LED turned ON (pin {self.led_pin} BCM)")
                return True, "LED_ON_SUCCESS"
            except Exception as e:
                error_msg = f"GPIO error ({type(e).__name__}): {str(e)} - GPIO may not be properly initialized"
                logger.error(f"Error turning LED on: {error_msg}")
                return False, error_msg

    def led_off(self) -> tuple[bool, str]:
        with self._chip_lock:
            if not self.initialized or self.chip is None:
                error_msg = "GPIO not initialized - LED pin not configured"
                logger.error(
                    f"{error_msg} - Check logs for GPIO setup errors. Ensure target is running with 'sudo'"
                )
                return False, error_msg

            try:
                lgpio.gpio_write(self.chip, self.led_pin, 0)
                logger.info(f"LED turned OFF (pin {self.led_pin} BCM)")
                return True, "LED_OFF_SUCCESS"
            except Exception as e:
                error_msg = f"GPIO error ({type(e).__name__}): {str(e)} - GPIO may not be properly initialized"
                logger.error(f"Error turning LED off: {error_msg}")
                return False, error_msg

    def read_input(self) -> Optional[int]:
        with self._chip_lock:
            if not self.initialized or self.chip is None:
                logger.error("GPIO not initialized")
                return None

            try:
                value = lgpio.gpio_read(self.chip, self.input_pin)
                logger.debug(f"Input pin {self.input_pin} read: {value}")
                return value
            except Exception as e:
                logger.error(f"Error reading input pin: {e}")
                return None

    def setup(self, pin: int, mode: str):
        with self._chip_lock:
            if not self.initialized or self.chip is None:
                logger.error("GPIO not initialized")
                return

            try:
                if mode.upper() == "INPUT":
                    lgpio.gpio_claim_input(self.chip, pin, lgpio.SET_PULL_DOWN)
                    if pin not in self.claimed_pins:
                        self.claimed_pins.append(pin)
                elif mode.upper() == "OUTPUT":
                    lgpio.gpio_claim_output(self.chip, pin, 0)
                    if pin not in self.claimed_pins:
                        self.claimed_pins.append(pin)
                else:
                    logger.error(f"Invalid GPIO mode: {mode}")
            except Exception as e:
                logger.error(f"Error setting up GPIO pin {pin}: {e}")

    def write(self, pin: int, value: int):
        with self._chip_lock:
            if not self.initialized or self.chip is None:
                logger.error("GPIO not initialized")
                return

            try:
                lgpio.gpio_write(self.chip, pin, 1 if value else 0)
                logger.debug(f"GPIO pin {pin} set to {value}")
            except Exception as e:
                logger.error(f"Error writing to GPIO pin {pin}: {e}")

    def read(self, pin: int) -> int:
        return self.read_input() if pin == self.input_pin else None

    def set_power_supply_enable(self, enabled: bool) -> bool:
        with self._chip_lock:
            if not self.initialized or self.chip is None:
                logger.error("GPIO not initialized")
                return False
            try:
                lgpio.gpio_write(self.chip, self.power_supply_pin, 1 if enabled else 0)
                with self._state_lock:
                    self.power_supply_enabled = enabled
                logger.info(f"Power supply {'enabled' if enabled else 'disabled'}")
                return True
            except Exception as e:
                logger.error(f"Error setting power supply: {e}")
                return False


    def emergency_shutdown(self) -> bool:
        with self._chip_lock:
            if not self.initialized or self.chip is None:
                logger.error("GPIO not initialized")
                return False
            try:
                lgpio.gpio_write(self.chip, self.power_supply_pin, 0)

                with self._state_lock:
                    self.power_supply_enabled = False

                logger.warning("EMERGENCY SHUTDOWN executed - power supply disabled")
                return True
            except Exception as e:
                logger.error(f"Error during emergency shutdown: {e}")
                return False

    def cleanup(self):
        with self._chip_lock:
            if self.initialized and self.chip is not None:
                try:
                    lgpio.gpio_write(self.chip, self.power_supply_pin, 0)
                    lgpio.gpio_write(self.chip, self.led_pin, 0)

                    for pin in self.claimed_pins:
                        try:
                            lgpio.gpio_free(self.chip, pin)
                        except Exception:
                            pass

                    lgpio.gpiochip_close(self.chip)
                    self.chip = None
                    self.claimed_pins = []
                    self.initialized = False

                    with self._state_lock:
                        self.power_supply_enabled = False

                    logger.info("GPIO cleanup complete")
                except Exception as e:
                    logger.error(f"Error during GPIO cleanup: {e}")
