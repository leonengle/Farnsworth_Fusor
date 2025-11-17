import RPi.GPIO as GPIO
from logging_setup import setup_logging, get_logger
from base_classes import GPIOInterface
from typing import Optional

# Setup logging
setup_logging()
logger = get_logger("GPIOHandler")
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
        
        self.valve_pwms = [None] * len(self.valve_pins)
        self.mechanical_pump_pwm = None
        self.turbo_pump_pwm = None
        self.pwm_frequency = 1000

        self._setup_gpio()

    def _setup_gpio(self):
        try:
            # Check if running with proper permissions
            import os
            if os.geteuid() != 0:
                logger.warning("Not running as root - GPIO may not work properly. Try running with 'sudo'")
            
            # Try to cleanup any existing GPIO state first
            try:
                GPIO.cleanup()
                logger.debug("Cleaned up existing GPIO state")
            except Exception:
                # Ignore cleanup errors - GPIO might not be initialized yet
                pass
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.led_pin, GPIO.OUT)
            GPIO.setup(self.input_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
            GPIO.setup(self.power_supply_pin, GPIO.OUT)
            GPIO.output(self.power_supply_pin, GPIO.LOW)
            
            for i, pin in enumerate(self.valve_pins):
                GPIO.setup(pin, GPIO.OUT)
                self.valve_pwms[i] = GPIO.PWM(pin, self.pwm_frequency)
                self.valve_pwms[i].start(0)
            
            GPIO.setup(self.mechanical_pump_pin, GPIO.OUT)
            GPIO.setup(self.turbo_pump_pin, GPIO.OUT)
            self.mechanical_pump_pwm = GPIO.PWM(self.mechanical_pump_pin, self.pwm_frequency)
            self.mechanical_pump_pwm.start(0)
            self.turbo_pump_pwm = GPIO.PWM(self.turbo_pump_pin, self.pwm_frequency)
            self.turbo_pump_pwm.start(0)

            GPIO.output(self.led_pin, GPIO.LOW)
            self.initialized = True

            logger.info(
                f"GPIO setup complete - LED: {self.led_pin}, Input: {self.input_pin}, "
                f"Power Supply: {self.power_supply_pin}, Valves: {self.valve_pins}, "
                f"Pumps: Mech={self.mechanical_pump_pin}, Turbo={self.turbo_pump_pin}"
            )
        except RuntimeError as e:
            if "GPIO channels already in use" in str(e) or "GPIO channel" in str(e):
                logger.error(f"GPIO setup error: GPIO channels already in use")
                logger.error("Attempting to cleanup and retry...")
                try:
                    GPIO.cleanup()
                    # Retry setup once
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(self.led_pin, GPIO.OUT)
                    GPIO.setup(self.input_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                    GPIO.setup(self.power_supply_pin, GPIO.OUT)
                    GPIO.output(self.power_supply_pin, GPIO.LOW)
                    GPIO.output(self.led_pin, GPIO.LOW)
                    self.initialized = True
                    logger.info("GPIO setup successful after cleanup retry")
                    logger.info(
                        f"GPIO setup complete - LED: {self.led_pin}, Input: {self.input_pin}, "
                        f"Power Supply: {self.power_supply_pin}"
                    )
                    return  # Success after retry
                except Exception as retry_error:
                    logger.error(f"GPIO setup retry failed: {retry_error}")
                    logger.error("Try manually: sudo python3 -c 'import RPi.GPIO as GPIO; GPIO.cleanup()'")
            else:
                logger.error(f"GPIO setup error (RuntimeError): {e}")
            logger.error("GPIO initialization failed - LED and other GPIO functions will not work")
            self.initialized = False
        except PermissionError as e:
            logger.error(f"GPIO setup error: Permission denied. You must run with 'sudo' to access GPIO pins.")
            logger.error(f"Try: sudo python3 target_main.py")
            self.initialized = False
        except Exception as e:
            logger.error(f"GPIO setup error: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error("GPIO initialization failed - LED and other GPIO functions will not work")
            self.initialized = False

    def led_on(self) -> bool:
        if not self.initialized:
            logger.error("GPIO not initialized - cannot turn LED on")
            logger.error("Check logs for GPIO setup errors. Ensure target is running with 'sudo'")
            return False

        try:
            GPIO.output(self.led_pin, GPIO.HIGH)
            logger.info(f"LED turned ON (pin {self.led_pin})")
            return True
        except RuntimeError as e:
            logger.error(f"Error turning LED on (RuntimeError): {e}")
            logger.error("GPIO may not be properly initialized or pins are in use")
            return False
        except Exception as e:
            logger.error(f"Error turning LED on: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            return False

    def led_off(self) -> bool:
        if not self.initialized:
            logger.error("GPIO not initialized")
            return False

        try:
            GPIO.output(self.led_pin, GPIO.LOW)
            logger.info(f"LED turned OFF (pin {self.led_pin})")
            return True
        except Exception as e:
            logger.error(f"Error turning LED off: {e}")
            return False

    def read_input(self) -> Optional[int]:
        if not self.initialized:
            logger.error("GPIO not initialized")
            return None

        try:
            value = GPIO.input(self.input_pin)
            logger.debug(f"Input pin {self.input_pin} read: {value}")
            return value
        except Exception as e:
            logger.error(f"Error reading input pin: {e}")
            return None

    def setup(self, pin: int, mode: str):
        if not self.initialized:
            GPIO.setmode(GPIO.BCM)
            self.initialized = True

        try:
            if mode.upper() == "INPUT":
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            elif mode.upper() == "OUTPUT":
                GPIO.setup(pin, GPIO.OUT)
            else:
                logger.error(f"Invalid GPIO mode: {mode}")
        except Exception as e:
            logger.error(f"Error setting up GPIO pin {pin}: {e}")

    def write(self, pin: int, value: int):
        if not self.initialized:
            logger.error("GPIO not initialized")
            return

        try:
            GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)
            logger.debug(f"GPIO pin {pin} set to {value}")
        except Exception as e:
            logger.error(f"Error writing to GPIO pin {pin}: {e}")

    def read(self, pin: int) -> int:
        return self.read_input() if pin == self.input_pin else None

    def set_power_supply_enable(self, enabled: bool) -> bool:
        if not self.initialized:
            logger.error("GPIO not initialized")
            return False
        try:
            GPIO.output(self.power_supply_pin, GPIO.HIGH if enabled else GPIO.LOW)
            self.power_supply_enabled = enabled
            logger.info(f"Power supply {'enabled' if enabled else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Error setting power supply: {e}")
            return False

    def set_valve_position(self, valve_id: int, position: int) -> bool:
        if not self.initialized:
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
            if self.valve_pwms[valve_index] is not None:
                self.valve_pwms[valve_index].ChangeDutyCycle(position)
                self.valve_states[valve_index] = position
                logger.info(f"Valve {valve_id} set to {position}% (PWM duty cycle)")
                return True
            else:
                logger.error(f"PWM not initialized for valve {valve_id}")
                return False
        except Exception as e:
            logger.error(f"Error setting valve {valve_id}: {e}")
            return False

    def set_mechanical_pump_power(self, power: int) -> bool:
        if not self.initialized:
            logger.error("GPIO not initialized")
            return False
        if power < 0 or power > 100:
            logger.error(f"Invalid pump power: {power} (must be 0-100)")
            return False
        try:
            if self.mechanical_pump_pwm is not None:
                self.mechanical_pump_pwm.ChangeDutyCycle(power)
                self.mechanical_pump_power = power
                logger.info(f"Mechanical pump set to {power}% (PWM duty cycle)")
                return True
            else:
                logger.error("PWM not initialized for mechanical pump")
                return False
        except Exception as e:
            logger.error(f"Error setting mechanical pump: {e}")
            return False

    def set_turbo_pump_power(self, power: int) -> bool:
        if not self.initialized:
            logger.error("GPIO not initialized")
            return False
        if power < 0 or power > 100:
            logger.error(f"Invalid pump power: {power} (must be 0-100)")
            return False
        try:
            if self.turbo_pump_pwm is not None:
                self.turbo_pump_pwm.ChangeDutyCycle(power)
                self.turbo_pump_power = power
                logger.info(f"Turbo pump set to {power}% (PWM duty cycle)")
                return True
            else:
                logger.error("PWM not initialized for turbo pump")
                return False
        except Exception as e:
            logger.error(f"Error setting turbo pump: {e}")
            return False

    def emergency_shutdown(self) -> bool:
        if not self.initialized:
            logger.error("GPIO not initialized")
            return False
        try:
            GPIO.output(self.power_supply_pin, GPIO.LOW)
            self.power_supply_enabled = False
            
            for i, pwm in enumerate(self.valve_pwms):
                if pwm is not None:
                    pwm.ChangeDutyCycle(0)
            self.valve_states = [0] * len(self.valve_pins)
            
            if self.mechanical_pump_pwm is not None:
                self.mechanical_pump_pwm.ChangeDutyCycle(0)
            if self.turbo_pump_pwm is not None:
                self.turbo_pump_pwm.ChangeDutyCycle(0)
            self.mechanical_pump_power = 0
            self.turbo_pump_power = 0
            
            logger.warning("EMERGENCY SHUTDOWN executed - all systems disabled")
            return True
        except Exception as e:
            logger.error(f"Error during emergency shutdown: {e}")
            return False

    def cleanup(self):
        if self.initialized:
            try:
                self.emergency_shutdown()
                
                for pwm in self.valve_pwms:
                    if pwm is not None:
                        pwm.stop()
                
                if self.mechanical_pump_pwm is not None:
                    self.mechanical_pump_pwm.stop()
                if self.turbo_pump_pwm is not None:
                    self.turbo_pump_pwm.stop()
                
                GPIO.output(self.led_pin, GPIO.LOW)
                GPIO.cleanup()
                self.initialized = False
                logger.info("GPIO cleanup complete")
            except Exception as e:
                logger.error(f"Error during GPIO cleanup: {e}")
