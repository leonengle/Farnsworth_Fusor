import RPi.GPIO as GPIO
from logging_setup import setup_logging, get_logger
from base_classes import GPIOInterface
from typing import Optional

# Setup logging
setup_logging()
logger = get_logger("GPIOHandler")


class GPIOHandler(GPIOInterface):
    def __init__(self, led_pin: int = 26, input_pin: int = 6, name: str = "GPIOHandler"):
        super().__init__(name)
        self.led_pin = led_pin
        self.input_pin = input_pin
        self.initialized = False
        
        self._setup_gpio()
    
    def _setup_gpio(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.led_pin, GPIO.OUT)
            GPIO.setup(self.input_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
            # Start with LED off
            GPIO.output(self.led_pin, GPIO.LOW)
            self.initialized = True
            
            logger.info(f"GPIO setup complete - LED pin {self.led_pin}, Input pin {self.input_pin}")
        except Exception as e:
            logger.error(f"GPIO setup error: {e}")
            self.initialized = False
    
    def led_on(self) -> bool:
        if not self.initialized:
            logger.error("GPIO not initialized")
            return False
        
        try:
            GPIO.output(self.led_pin, GPIO.HIGH)
            logger.info(f"LED turned ON (pin {self.led_pin})")
            return True
        except Exception as e:
            logger.error(f"Error turning LED on: {e}")
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
    
    def cleanup(self):
                if self.initialized:
            try:
                # Turn off LED before cleanup
                GPIO.output(self.led_pin, GPIO.LOW)
                GPIO.cleanup()
                self.initialized = False
                logger.info("GPIO cleanup complete")
            except Exception as e:
                logger.error(f"Error during GPIO cleanup: {e}")

