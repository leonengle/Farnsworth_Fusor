import logging
from typing import Optional, Callable
from gpio_handler import GPIOHandler
from adc import MCP3008ADC

logger = logging.getLogger("CommandProcessor")


class CommandProcessor:

    def __init__(
        self,
        gpio_handler: GPIOHandler,
        adc: Optional[MCP3008ADC] = None,
        host_callback: Optional[Callable[[str], None]] = None,
    ):
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
            # LED commands (legacy support)
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

            elif command == "POWER_SUPPLY_ENABLE" or command == "POWER_SUPPLY_ENABLE:1" or command == "POWER_SUPPLY_ENABLE:ON":
                if self.gpio_handler.set_power_supply_enable(True):
                    return "POWER_SUPPLY_ENABLE_SUCCESS"
                else:
                    return "POWER_SUPPLY_ENABLE_FAILED"
            
            elif command == "POWER_SUPPLY_DISABLE" or command == "POWER_SUPPLY_ENABLE:0" or command == "POWER_SUPPLY_ENABLE:OFF":
                if self.gpio_handler.set_power_supply_enable(False):
                    return "POWER_SUPPLY_DISABLE_SUCCESS"
                else:
                    return "POWER_SUPPLY_DISABLE_FAILED"

            elif command.startswith("SET_VOLTAGE:"):
                try:
                    voltage = float(command.split(":")[1])
                    if voltage < 0:
                        return "SET_VOLTAGE_FAILED: Voltage must be >= 0"
                    logger.info(f"Voltage set to {voltage}V")
                    return f"SET_VOLTAGE_SUCCESS:{voltage}"
                except (ValueError, IndexError):
                    return "SET_VOLTAGE_FAILED: Invalid format"

            elif command.startswith("SET_VALVE"):
                try:
                    parts = command.split(":")
                    if len(parts) != 2:
                        return "SET_VALVE_FAILED: Invalid format"
                    
                    valve_part = parts[0].replace("SET_VALVE", "")
                    valve_id = int(valve_part)
                    position = int(parts[1])
                    
                    if valve_id < 1 or valve_id > 6:
                        return f"SET_VALVE_FAILED: Valve ID must be 1-6"
                    
                    if self.gpio_handler.set_valve_position(valve_id, position):
                        return f"SET_VALVE{valve_id}_SUCCESS:{position}"
                    else:
                        return f"SET_VALVE{valve_id}_FAILED"
                except (ValueError, IndexError):
                    return "SET_VALVE_FAILED: Invalid format"

            elif command.startswith("SET_MECHANICAL_PUMP:"):
                try:
                    power = int(command.split(":")[1])
                    if power < 0 or power > 100:
                        return "SET_MECHANICAL_PUMP_FAILED: Power must be 0-100"
                    if self.gpio_handler.set_mechanical_pump_power(power):
                        return f"SET_MECHANICAL_PUMP_SUCCESS:{power}"
                    else:
                        return "SET_MECHANICAL_PUMP_FAILED"
                except (ValueError, IndexError):
                    return "SET_MECHANICAL_PUMP_FAILED: Invalid format"

            elif command.startswith("SET_TURBO_PUMP:"):
                try:
                    power = int(command.split(":")[1])
                    if power < 0 or power > 100:
                        return "SET_TURBO_PUMP_FAILED: Power must be 0-100"
                    if self.gpio_handler.set_turbo_pump_power(power):
                        return f"SET_TURBO_PUMP_SUCCESS:{power}"
                    else:
                        return "SET_TURBO_PUMP_FAILED"
                except (ValueError, IndexError):
                    return "SET_TURBO_PUMP_FAILED: Invalid format"

            elif command == "STARTUP":
                logger.info("Startup command received")
                return "STARTUP_SUCCESS"
            
            elif command == "SHUTDOWN":
                if self.gpio_handler.set_power_supply_enable(False):
                    for i in range(1, 7):
                        self.gpio_handler.set_valve_position(i, 0)
                    self.gpio_handler.set_mechanical_pump_power(0)
                    self.gpio_handler.set_turbo_pump_power(0)
                    logger.info("Shutdown sequence completed")
                    return "SHUTDOWN_SUCCESS"
                else:
                    return "SHUTDOWN_FAILED"
            
            elif command == "EMERGENCY_SHUTOFF":
                if self.gpio_handler.emergency_shutdown():
                    return "EMERGENCY_SHUTOFF_SUCCESS"
                else:
                    return "EMERGENCY_SHUTOFF_FAILED"

            elif command == "READ_POWER_SUPPLY_VOLTAGE":
                if not self.adc or not self.adc.is_initialized():
                    return "READ_POWER_SUPPLY_VOLTAGE_FAILED: ADC not initialized"
                try:
                    adc_value = self.adc.read_channel(0)
                    voltage = self.adc.convert_to_voltage(adc_value) * 10
                    response = f"POWER_SUPPLY_VOLTAGE:{voltage:.2f}"
                    if self.host_callback:
                        self.host_callback(response)
                    return response
                except Exception as e:
                    logger.error(f"Error reading power supply voltage: {e}")
                    return f"READ_POWER_SUPPLY_VOLTAGE_FAILED: {e}"

            elif command == "READ_POWER_SUPPLY_CURRENT":
                if not self.adc or not self.adc.is_initialized():
                    return "READ_POWER_SUPPLY_CURRENT_FAILED: ADC not initialized"
                try:
                    adc_value = self.adc.read_channel(1)
                    current = (adc_value / 1023.0) * 5.0
                    response = f"POWER_SUPPLY_CURRENT:{current:.3f}"
                    if self.host_callback:
                        self.host_callback(response)
                    return response
                except Exception as e:
                    logger.error(f"Error reading power supply current: {e}")
                    return f"READ_POWER_SUPPLY_CURRENT_FAILED: {e}"

            elif command.startswith("READ_PRESSURE_SENSOR:"):
                try:
                    sensor_id = int(command.split(":")[1])
                    if sensor_id < 1 or sensor_id > 3:
                        return "READ_PRESSURE_SENSOR_FAILED: Sensor ID must be 1-3"
                    if not self.adc or not self.adc.is_initialized():
                        return "READ_PRESSURE_SENSOR_FAILED: ADC not initialized"
                    channel = sensor_id + 1
                    adc_value = self.adc.read_channel(channel)
                    pressure = (adc_value / 1023.0) * 100.0
                    response = f"PRESSURE_SENSOR_{sensor_id}_VALUE:{pressure:.2f}"
                    if self.host_callback:
                        self.host_callback(response)
                    return response
                except (ValueError, IndexError):
                    return "READ_PRESSURE_SENSOR_FAILED: Invalid format"
                except Exception as e:
                    logger.error(f"Error reading pressure sensor: {e}")
                    return f"READ_PRESSURE_SENSOR_FAILED: {e}"

            elif command.startswith("READ_NODE_VOLTAGE:"):
                try:
                    node_id = int(command.split(":")[1])
                    if node_id < 1 or node_id > 3:
                        return "READ_NODE_VOLTAGE_FAILED: Node ID must be 1-3"
                    if not self.adc or not self.adc.is_initialized():
                        return "READ_NODE_VOLTAGE_FAILED: ADC not initialized"
                    channel = node_id + 4
                    adc_value = self.adc.read_channel(channel)
                    voltage = self.adc.convert_to_voltage(adc_value) * 10
                    response = f"NODE_{node_id}_VOLTAGE:{voltage:.2f}"
                    if self.host_callback:
                        self.host_callback(response)
                    return response
                except (ValueError, IndexError):
                    return "READ_NODE_VOLTAGE_FAILED: Invalid format"
                except Exception as e:
                    logger.error(f"Error reading node voltage: {e}")
                    return f"READ_NODE_VOLTAGE_FAILED: {e}"

            elif command.startswith("READ_NODE_CURRENT:"):
                try:
                    node_id = int(command.split(":")[1])
                    if node_id < 1 or node_id > 3:
                        return "READ_NODE_CURRENT_FAILED: Node ID must be 1-3"
                    if not self.adc or not self.adc.is_initialized():
                        return "READ_NODE_CURRENT_FAILED: ADC not initialized"
                    channel = node_id + 4
                    adc_value = self.adc.read_channel(channel)
                    current = (adc_value / 1023.0) * 5.0
                    response = f"NODE_{node_id}_CURRENT:{current:.3f}"
                    if self.host_callback:
                        self.host_callback(response)
                    return response
                except (ValueError, IndexError):
                    return "READ_NODE_CURRENT_FAILED: Invalid format"
                except Exception as e:
                    logger.error(f"Error reading node current: {e}")
                    return f"READ_NODE_CURRENT_FAILED: {e}"

            elif command == "READ_NEUTRON_COUNTS":
                logger.info("Neutron counts read requested (not yet implemented)")
                return "NEUTRON_COUNTS:0"

            # Read input command (legacy)
            elif command == "READ_INPUT":
                value = self.gpio_handler.read_input()
                if value is not None:
                    response = f"INPUT_VALUE:{value}"
                    if self.host_callback:
                        self.host_callback(f"GPIO_INPUT:{value}")
                    return response
                else:
                    return "READ_INPUT_FAILED"

            # Read ADC command (legacy - reads all channels)
            elif command == "READ_ADC":
                if not self.adc or not self.adc.is_initialized():
                    return "READ_ADC_FAILED: ADC not initialized"

                try:
                    adc_values = self.adc.read_all_channels()
                    response = f"ADC_DATA:{','.join(map(str, adc_values))}"
                    if self.host_callback:
                        self.host_callback(response)
                    return response
                except Exception as e:
                    logger.error(f"ADC read error: {e}")
                    return f"READ_ADC_FAILED: {e}"

            # Legacy pump power command (for backward compatibility)
            elif command.startswith("SET_PUMP_POWER:"):
                try:
                    power = int(command.split(":")[1])
                    if power < 0 or power > 100:
                        return "SET_PUMP_POWER_FAILED: Power must be 0-100"
                    if self.gpio_handler.set_mechanical_pump_power(power):
                        return f"SET_PUMP_POWER_SUCCESS:{power}"
                    else:
                        return "SET_PUMP_POWER_FAILED"
                except (ValueError, IndexError):
                    return "SET_PUMP_POWER_FAILED: Invalid format"

            # Move motor command (legacy)
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
