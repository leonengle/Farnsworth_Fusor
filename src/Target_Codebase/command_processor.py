import logging
from typing import Optional, Callable
from gpio_handler import GPIOHandler
from adc import MCP3008ADC

logger = logging.getLogger("CommandProcessor")


class CommandProcessor:
    
    def __init__(self, gpio_handler: GPIOHandler, adc: Optional[MCP3008ADC] = None,
                 host_callback: Optional[Callable[[str], None]] = None):
        self.gpio_handler = gpio_handler
        self.adc = adc
        self.host_callback = host_callback
        
        logger.info("Command processor initialized")
    
    def set_host_callback(self, callback: Callable[[str], None]):
        self.host_callback = callback
        logger.info("Host callback set")
    
    def process_command(self, command: str) -> str:
        if not command:
            return "ERROR: Empty command"
        
        command = command.strip().upper()
        
        try:
            # LED commands
            if command == "LED_ON":
                if self.gpio_handler.led_on():
                    return "LED_ON_SUCCESS"
                else:
                    return "LED_ON_FAILED"
            
            elif command == "LED_OFF":
                if self.gpio_handler.led_off():
                    return "LED_OFF_SUCCESS"
                else:
                    return "LED_OFF_FAILED"
            
            # Read input command
            elif command == "READ_INPUT":
                value = self.gpio_handler.read_input()
                if value is not None:
                    response = f"INPUT_VALUE:{value}"
                    # Send data to host via callback
                    if self.host_callback:
                        self.host_callback(f"GPIO_INPUT:{value}")
                    return response
                else:
                    return "READ_INPUT_FAILED"
            
            # Read ADC command
            elif command == "READ_ADC":
                if not self.adc or not self.adc.is_initialized():
                    return "READ_ADC_FAILED: ADC not initialized"
                
                try:
                    adc_values = self.adc.read_all_channels()
                    response = f"ADC_DATA:{','.join(map(str, adc_values))}"
                    # Send data to host via callback
                    if self.host_callback:
                        self.host_callback(response)
                    return response
                except Exception as e:
                    logger.error(f"ADC read error: {e}")
                    return f"READ_ADC_FAILED: {e}"
            
            # Set voltage command
            elif command.startswith("SET_VOLTAGE:"):
                try:
                    voltage = int(command.split(":")[1])
                    # TODO: Implement actual voltage setting
                    logger.info(f"Voltage set to {voltage}V")
                    return f"SET_VOLTAGE_SUCCESS:{voltage}"
                except (ValueError, IndexError):
                    return "SET_VOLTAGE_FAILED: Invalid format"
            
            # Set pump power command
            elif command.startswith("SET_PUMP_POWER:"):
                try:
                    power = int(command.split(":")[1])
                    if power < 0 or power > 100:
                        return "SET_PUMP_POWER_FAILED: Power must be 0-100"
                    # TODO: Implement actual pump power setting
                    logger.info(f"Pump power set to {power}%")
                    return f"SET_PUMP_POWER_SUCCESS:{power}"
                except (ValueError, IndexError):
                    return "SET_PUMP_POWER_FAILED: Invalid format"
            
            # Move motor command
            elif command.startswith("MOVE_VAR:"):
                try:
                    steps = int(command.split(":")[1])
                    # TODO: Implement actual motor movement
                    logger.info(f"Motor move command: {steps} steps")
                    return f"MOVE_VAR_SUCCESS:{steps}"
                except (ValueError, IndexError):
                    return "MOVE_VAR_FAILED: Invalid format"
            
            # Unknown command
            else:
                logger.warning(f"Unknown command: {command}")
                return f"ERROR: Unknown command '{command}'"
        
        except Exception as e:
            logger.error(f"Error processing command '{command}': {e}")
            return f"ERROR: {e}"

