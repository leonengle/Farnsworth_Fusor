from typing import Optional
from gpio_handler import GPIOHandler
from adc import MCP3008ADC
from arduino_interface import ArduinoInterface
from arduino_command_validator import ArduinoCommandValidator
from logging_setup import setup_logging, get_logger

setup_logging()
logger = get_logger("BundledInterface")


class BundledInterface:
    def __init__(
        self,
        gpio_handler: Optional[GPIOHandler] = None,
        adc: Optional[MCP3008ADC] = None,
        arduino_interface: Optional[ArduinoInterface] = None,
    ):
        self.gpio_handler = gpio_handler
        self.adc = adc
        self.arduino_interface = arduino_interface
        self.validator = ArduinoCommandValidator()
        
        logger.info("Bundled Interface initialized")
        logger.info(f"  GPIO: {'Available' if gpio_handler else 'Not available'}")
        logger.info(f"  SPI (ADC): {'Available' if adc else 'Not available'}")
        logger.info(f"  USB (Arduino): {'Available' if arduino_interface else 'Not available'}")

    def get_gpio(self) -> Optional[GPIOHandler]:
        return self.gpio_handler

    def get_adc(self) -> Optional[MCP3008ADC]:
        return self.adc

    def get_arduino(self) -> Optional[ArduinoInterface]:
        return self.arduino_interface

    def send_motor_command(self, motor_id: int, command: str, *args) -> Optional[str]:
        if not self.arduino_interface:
            logger.error("Motor control requires Arduino interface (not available)")
            return None
        
        if not self.arduino_interface.is_connected():
            logger.error("Motor control requires Arduino interface (not connected)")
            return None
        
        arduino_cmd = self.validator.build_motor_command_string(motor_id, command, *args)
        if not arduino_cmd:
            logger.error(f"Motor command validation failed for motor {motor_id}, command {command}")
            return None
        
        if self.arduino_interface.send_command(arduino_cmd):
            response = self.arduino_interface.read_data(timeout=2.0)
            return response
        return None

    def send_motor_object(self, motor_id: int, percentage_or_power: float) -> bool:
        if not self.arduino_interface:
            logger.error("Motor control requires Arduino interface (not available)")
            return False
        
        if not self.arduino_interface.is_connected():
            logger.error("Motor control requires Arduino interface (not connected)")
            return False
        
        if motor_id < 1 or motor_id > 6:
            logger.error(f"Invalid motor ID: {motor_id} (must be 1-6)")
            return False
        
        component_name = f"MOTOR_{motor_id}"
        motor_degree = self.validator.map_percentage_to_degree(percentage_or_power)
        
        is_valid, error = self.validator.validate_motor_degree_object(component_name, motor_degree)
        if not is_valid:
            logger.error(f"Motor degree object validation failed: {error}")
            return False
        
        logger.info(f"Sending motor object to Arduino: {component_name} -> {motor_degree}° (from {percentage_or_power}%)")
        result = self.arduino_interface.send_motor_object(component_name, motor_degree)
        if result:
            logger.info(f"Motor object sent successfully: {component_name} -> {motor_degree}°")
        else:
            logger.error(f"Failed to send motor object: {component_name} -> {motor_degree}°")
        return result

    def send_analog_to_arduino(self, label: str, value) -> bool:
        if not self.arduino_interface:
            return False
        
        if not self.arduino_interface.is_connected():
            return False
        
        try:
            arduino_cmd = self.validator.build_analog_command_string(label, value)
            if not arduino_cmd:
                logger.error(f"Analog command validation failed for label {label}, value {value}")
                return False
            
            return self.arduino_interface.send_command(arduino_cmd)
        except Exception as e:
            logger.error(f"Failed to send analog command to Arduino: {e}")
            return False

    def cleanup(self):
        if self.gpio_handler:
            try:
                self.gpio_handler.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up GPIO: {e}")
        
        if self.adc:
            try:
                self.adc.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up ADC: {e}")
        
        if self.arduino_interface:
            try:
                self.arduino_interface.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up Arduino: {e}")
        
        logger.info("Bundled Interface cleaned up")

