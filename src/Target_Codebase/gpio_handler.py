import lgpio
import threading
from logging_setup import setup_logging, get_logger
from base_classes import GPIOInterface
from typing import Optional

# Setup logging
setup_logging()
logger = get_logger("GPIOHandler")

# IMPORTANT: lgpio uses BCM (Broadcom) pin numbering by default
# All pin numbers in this file are BCM pin numbers (e.g., 26 = BCM GPIO26 = physical pin 37)
# There is no BOARD/BCM mode selection needed with lgpio - it always uses BCM

class GPIOHandler(GPIOInterface):
    def __init__(
        self,
        led_pin: int = 26,
        input_pin: int = 6,
        name: str = "GPIOHandler",
        power_supply_pin: int = 5,
        valve_pins: list = None,
        mechanical_pump_pin: int = 27,
        turbo_pump_pin: int = 16,
    ):
        super().__init__(name)
        self.led_pin = led_pin
        self.input_pin = input_pin
        self.power_supply_pin = power_supply_pin
        if valve_pins is None:
            valve_pins = [17, 4, 22, 23, 24, 25]
        self.valve_pins = valve_pins
        self.mechanical_pump_pin = mechanical_pump_pin
        self.turbo_pump_pin = turbo_pump_pin
        self.initialized = False
        
        self.power_supply_enabled = False
        self.valve_states = [0] * len(self.valve_pins)
        self.mechanical_pump_power = 0
        self.turbo_pump_power = 0
        
        self.chip = None
        self.pwm_frequency = 1000
        self.claimed_pins = []
        
        self._state_lock = threading.Lock()
        self._chip_lock = threading.Lock()

        self._setup_gpio()

    def _setup_gpio(self):
        try:
            # Check if running with proper permissions
            import os
            if os.geteuid() != 0:
                logger.warning("Not running as root - GPIO may not work properly. Try running with 'sudo'")
            
            # Open GPIO chip (chip 0 is the main GPIO chip on Raspberry Pi)
            # Note: lgpio uses BCM pin numbering by default (no setmode needed)
            try:
                logger.info("DEBUG: Opening GPIO chip 0 (main GPIO chip)")
                self.chip = lgpio.gpiochip_open(0)
                logger.info(f"DEBUG: GPIO chip opened successfully, chip handle: {self.chip}")
            except Exception as e:
                logger.error(f"Failed to open GPIO chip: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error("This might indicate you're not running on a Raspberry Pi")
                logger.error("DEBUG: GPIO chip open failed - initialization aborted")
                self.initialized = False
                return
            
            # Claim and configure LED pin as output (BCM pin 26)
            # TEMPORARY: Only LED pin for debugging - all other pins commented out
            logger.info(f"DEBUG: Claiming LED pin {self.led_pin} (BCM) as output")
            lgpio.gpio_claim_output(self.chip, self.led_pin, 0)  # 0 = LOW
            self.claimed_pins.append(self.led_pin)
            logger.info(f"DEBUG: LED pin {self.led_pin} (BCM) successfully configured as output")
            
            # TEMPORARILY COMMENTED OUT FOR DEBUGGING - Input pin
            # try:
            #     lgpio.gpio_claim_input(self.chip, self.input_pin, lgpio.SET_PULL_DOWN)
            #     self.claimed_pins.append(self.input_pin)
            #     logger.debug(f"Input pin {self.input_pin} configured with pull-down")
            # except Exception as e:
            #     logger.error(f"Failed to configure input pin {self.input_pin}: {e}")
            #     self._cleanup_on_error()
            #     return
            
            # TEMPORARILY COMMENTED OUT FOR DEBUGGING - Power supply pin
            # try:
            #     lgpio.gpio_claim_output(self.chip, self.power_supply_pin, 0)  # 0 = LOW
            #     self.claimed_pins.append(self.power_supply_pin)
            #     logger.debug(f"Power supply pin {self.power_supply_pin} configured as output")
            # except Exception as e:
            #     logger.error(f"Failed to configure power supply pin {self.power_supply_pin}: {e}")
            #     self._cleanup_on_error()
            #     return
            
            # TEMPORARILY COMMENTED OUT FOR DEBUGGING - Valve pins with PWM
            # for i, pin in enumerate(self.valve_pins):
            #     try:
            #         lgpio.gpio_claim_output(self.chip, pin, 0)
            #         self.claimed_pins.append(pin)
            #         # Start PWM at 0% duty cycle
            #         lgpio.tx_pwm(self.chip, pin, self.pwm_frequency, 0)  # 0 = 0% duty cycle
            #         logger.debug(f"Valve pin {pin} configured with PWM")
            #     except Exception as e:
            #         logger.error(f"Failed to configure valve pin {pin}: {e}")
            #         self._cleanup_on_error()
            #         return
            
            # TEMPORARILY COMMENTED OUT FOR DEBUGGING - Mechanical pump pin with PWM
            # try:
            #     lgpio.gpio_claim_output(self.chip, self.mechanical_pump_pin, 0)
            #     self.claimed_pins.append(self.mechanical_pump_pin)
            #     lgpio.tx_pwm(self.chip, self.mechanical_pump_pin, self.pwm_frequency, 0)
            #     logger.debug(f"Mechanical pump pin {self.mechanical_pump_pin} configured with PWM")
            # except Exception as e:
            #     logger.error(f"Failed to configure mechanical pump pin {self.mechanical_pump_pin}: {e}")
            #     self._cleanup_on_error()
            #     return
            
            # TEMPORARILY COMMENTED OUT FOR DEBUGGING - Turbo pump pin with PWM
            # try:
            #     lgpio.gpio_claim_output(self.chip, self.turbo_pump_pin, 0)
            #     self.claimed_pins.append(self.turbo_pump_pin)
            #     lgpio.tx_pwm(self.chip, self.turbo_pump_pin, self.pwm_frequency, 0)
            #     logger.debug(f"Turbo pump pin {self.turbo_pump_pin} configured with PWM")
            # except Exception as e:
            #     logger.error(f"Failed to configure turbo pump pin {self.turbo_pump_pin}: {e}")
            #     self._cleanup_on_error()
            #     return

            self.initialized = True

            logger.info(f"GPIO setup complete - LED ONLY (pin {self.led_pin} BCM) - DEBUGGING MODE")
            logger.info("DEBUG: GPIO initialization successful - LED pin only configured using BCM numbering")
        except Exception as e:
            logger.error(f"GPIO setup error: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error("GPIO initialization failed - LED and other GPIO functions will not work")
            self._cleanup_on_error()
            self.initialized = False

    def _cleanup_on_error(self):
        """Clean up GPIO resources when initialization fails"""
        if self.chip is not None:
            try:
                # Free all claimed pins
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
                logger.error(f"{error_msg} - Check logs for GPIO setup errors. Ensure target is running with 'sudo'")
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
                logger.error(f"{error_msg} - Check logs for GPIO setup errors. Ensure target is running with 'sudo'")
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

    def set_valve_position(self, valve_id: int, position: int) -> bool:
        with self._chip_lock:
            if not self.initialized or self.chip is None:
                logger.error("GPIO not initialized")
                return False
            if valve_id < 1 or valve_id > len(self.valve_pins):
                logger.error(f"Invalid valve ID: {valve_id}")
                return False
            if position < 0 or position > 100:
                logger.error(f"Invalid valve position: {position} (must be 0-100)")
                return False
            try:
                valve_index = valve_id - 1
                pin = self.valve_pins[valve_index]
                duty_cycle = int(position * 10000)
                lgpio.tx_pwm(self.chip, pin, self.pwm_frequency, duty_cycle)
                with self._state_lock:
                    self.valve_states[valve_index] = position
                logger.info(f"Valve {valve_id} set to {position}% (PWM duty cycle)")
                return True
            except Exception as e:
                logger.error(f"Error setting valve {valve_id}: {e}")
                return False

    def set_mechanical_pump_power(self, power: int) -> bool:
        with self._chip_lock:
            if not self.initialized or self.chip is None:
                logger.error("GPIO not initialized")
                return False
            if power < 0 or power > 100:
                logger.error(f"Invalid pump power: {power} (must be 0-100)")
                return False
            try:
                duty_cycle = int(power * 10000)
                lgpio.tx_pwm(self.chip, self.mechanical_pump_pin, self.pwm_frequency, duty_cycle)
                with self._state_lock:
                    self.mechanical_pump_power = power
                logger.info(f"Mechanical pump set to {power}% (PWM duty cycle)")
                return True
            except Exception as e:
                logger.error(f"Error setting mechanical pump: {e}")
                return False

    def set_turbo_pump_power(self, power: int) -> bool:
        with self._chip_lock:
            if not self.initialized or self.chip is None:
                logger.error("GPIO not initialized")
                return False
            if power < 0 or power > 100:
                logger.error(f"Invalid pump power: {power} (must be 0-100)")
                return False
            try:
                duty_cycle = int(power * 10000)
                lgpio.tx_pwm(self.chip, self.turbo_pump_pin, self.pwm_frequency, duty_cycle)
                with self._state_lock:
                    self.turbo_pump_power = power
                logger.info(f"Turbo pump set to {power}% (PWM duty cycle)")
                return True
            except Exception as e:
                logger.error(f"Error setting turbo pump: {e}")
                return False

    def emergency_shutdown(self) -> bool:
        with self._chip_lock:
            if not self.initialized or self.chip is None:
                logger.error("GPIO not initialized")
                return False
            try:
                lgpio.gpio_write(self.chip, self.power_supply_pin, 0)
                
                for pin in self.valve_pins:
                    lgpio.tx_pwm(self.chip, pin, self.pwm_frequency, 0)
                
                lgpio.tx_pwm(self.chip, self.mechanical_pump_pin, self.pwm_frequency, 0)
                lgpio.tx_pwm(self.chip, self.turbo_pump_pin, self.pwm_frequency, 0)
                
                with self._state_lock:
                    self.power_supply_enabled = False
                    self.valve_states = [0] * len(self.valve_pins)
                    self.mechanical_pump_power = 0
                    self.turbo_pump_power = 0
                
                logger.warning("EMERGENCY SHUTDOWN executed - all systems disabled")
                return True
            except Exception as e:
                logger.error(f"Error during emergency shutdown: {e}")
                return False

    def cleanup(self):
        with self._chip_lock:
            if self.initialized and self.chip is not None:
                try:
                    lgpio.gpio_write(self.chip, self.power_supply_pin, 0)
                    
                    for pin in self.valve_pins:
                        try:
                            lgpio.tx_pwm(self.chip, pin, self.pwm_frequency, 0)
                        except Exception:
                            pass
                    
                    try:
                        lgpio.tx_pwm(self.chip, self.mechanical_pump_pin, self.pwm_frequency, 0)
                    except Exception:
                        pass
                    
                    try:
                        lgpio.tx_pwm(self.chip, self.turbo_pump_pin, self.pwm_frequency, 0)
                    except Exception:
                        pass
                    
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
                        self.valve_states = [0] * len(self.valve_pins)
                        self.mechanical_pump_power = 0
                        self.turbo_pump_power = 0
                    
                    logger.info("GPIO cleanup complete")
                except Exception as e:
                    logger.error(f"Error during GPIO cleanup: {e}")
