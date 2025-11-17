import logging
from typing import Optional, Callable, Dict
from gpio_handler import GPIOHandler
from adc import MCP3008ADC

logger = logging.getLogger("CommandProcessor")

VALVE_ANALOG_LABELS: Dict[int, str] = {
    1: "ATM_DEPRESSURE_VALVE",
    2: "FORELINE_VALVE",
    3: "VACUUM_SYSTEM_VALVE",
    4: "DEUTERIUM_SUPPLY_VALVE",
    5: "RESERVED_VALVE_5",
    6: "RESERVED_VALVE_6",
}

ANALOG_COMPONENT_LABELS = {
    "POWER_SUPPLY": "POWER_SUPPLY_VOLTAGE_SETPOINT",
    "MECHANICAL_PUMP": "ROUGHING_PUMP_POWER",
    "TURBO_PUMP": "TURBO_PUMP_POWER",
    "LEGACY_PUMP": "LEGACY_PUMP_POWER",
}


class CommandProcessor:

    def __init__(
        self,
        gpio_handler: GPIOHandler,
        adc: Optional[MCP3008ADC] = None,
        arduino_interface=None,
        host_callback: Optional[Callable[[str], None]] = None,
    ):
        self.gpio_handler = gpio_handler
        self.adc = adc
        self.arduino_interface = arduino_interface
        self.host_callback = host_callback

        logger.info(
            f"Command processor initialized (Arduino: {'Enabled' if arduino_interface else 'Disabled'})"
        )

    def _forward_analog_command(self, label: Optional[str], value) -> None:
        if not label or self.arduino_interface is None:
            return
        try:
            if not hasattr(self.arduino_interface, "is_connected") or not self.arduino_interface.is_connected():
                return
        except Exception as exc:
            logger.debug(f"Arduino interface connection check failed for {label}: {exc}")
            return
        send_method = getattr(self.arduino_interface, "send_analog_command", None)
        try:
            if callable(send_method):
                send_method(label, value)
            else:
                fallback_command = f"ANALOG:{label}:{value}"
                if hasattr(self.arduino_interface, "send_command"):
                    self.arduino_interface.send_command(fallback_command)
        except Exception as exc:
            logger.error(f"Failed to forward analog command '{label}' to Arduino: {exc}")

    def _resolve_valve_label(self, valve_id: int) -> str:
        return VALVE_ANALOG_LABELS.get(valve_id, f"VALVE_{valve_id}")

    def set_host_callback(self, callback: Callable[[str], None]):
        self.host_callback = callback
        logger.info("Host callback set")

    def process_command(self, command: str) -> str:
        if not command:
            return "ERROR: Empty command"

        command = command.strip().upper()

        try:
            if command == "LED_ON":
                success, message = self.gpio_handler.led_on()
                if success:
                    return "LED_ON_SUCCESS"
                else:
                    return f"LED_ON_FAILED: {message}"

            elif command == "LED_OFF":
                success, message = self.gpio_handler.led_off()
                if success:
                    return "LED_OFF_SUCCESS"
                else:
                    return f"LED_OFF_FAILED: {message}"

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
                    self._forward_analog_command(
                        ANALOG_COMPONENT_LABELS["POWER_SUPPLY"],
                        voltage,
                    )
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
                        self._forward_analog_command(
                            self._resolve_valve_label(valve_id),
                            position,
                        )
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
                        self._forward_analog_command(
                            ANALOG_COMPONENT_LABELS["MECHANICAL_PUMP"],
                            power,
                        )
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
                        self._forward_analog_command(
                            ANALOG_COMPONENT_LABELS["TURBO_PUMP"],
                            power,
                        )
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

            elif command == "READ_INPUT":
                value = self.gpio_handler.read_input()
                if value is not None:
                    response = f"INPUT_VALUE:{value}"
                    if self.host_callback:
                        self.host_callback(f"GPIO_INPUT:{value}")
                    return response
                else:
                    return "READ_INPUT_FAILED"

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

            elif command.startswith("SET_PUMP_POWER:"):
                try:
                    power = int(command.split(":")[1])
                    if power < 0 or power > 100:
                        return "SET_PUMP_POWER_FAILED: Power must be 0-100"
                    if self.gpio_handler.set_mechanical_pump_power(power):
                        self._forward_analog_command(
                            ANALOG_COMPONENT_LABELS["LEGACY_PUMP"],
                            power,
                        )
                        return f"SET_MECHANICAL_PUMP_SUCCESS:{power}"
                    else:
                        return "SET_PUMP_POWER_FAILED"
                except (ValueError, IndexError):
                    return "SET_PUMP_POWER_FAILED: Invalid format"

            elif command.startswith("MOVE_MOTOR:"):
                try:
                    parts = command.split(":")
                    if len(parts) < 3:
                        return "MOVE_MOTOR_FAILED: Invalid format (expected: MOVE_MOTOR:ID:STEPS[:DIRECTION])"
                    
                    motor_id = int(parts[1])
                    steps = int(parts[2])
                    direction = parts[3].upper() if len(parts) > 3 else "FORWARD"
                    
                    if motor_id < 1 or motor_id > 5:
                        return f"MOVE_MOTOR_FAILED: Motor ID must be 1-5"
                    
                    if motor_id >= 1 and motor_id <= 4:
                        if not self.arduino_interface:
                            return f"MOVE_MOTOR_FAILED: Motor {motor_id} requires Arduino interface (not available)"
                        if not self.arduino_interface.is_connected():
                            return f"MOVE_MOTOR_FAILED: Motor {motor_id} requires Arduino interface (not connected)"
                        
                        arduino_cmd = f"MOVE_MOTOR:{motor_id}:{steps}:{direction}"
                        if self.arduino_interface.send_command(arduino_cmd):
                            response = self.arduino_interface.read_data(timeout=2.0)
                            if response:
                                return f"MOVE_MOTOR{motor_id}_SUCCESS:{response}"
                            else:
                                return f"MOVE_MOTOR{motor_id}_COMMAND_SENT"
                        else:
                            return f"MOVE_MOTOR{motor_id}_FAILED: Send error"
                    
                    elif motor_id == 5:
                        logger.info(f"Motor 5 move command: {steps} steps, direction: {direction}")
                        return f"MOVE_MOTOR5_SUCCESS:{steps} (GPIO control - implementation pending)"
                    
                except (ValueError, IndexError) as e:
                    return f"MOVE_MOTOR_FAILED: Invalid format - {e}"

            elif command.startswith("ENABLE_MOTOR:"):
                try:
                    motor_id = int(command.split(":")[1])
                    if motor_id < 1 or motor_id > 5:
                        return f"ENABLE_MOTOR_FAILED: Motor ID must be 1-5"
                    
                    if motor_id >= 1 and motor_id <= 4:
                        if not self.arduino_interface or not self.arduino_interface.is_connected():
                            return f"ENABLE_MOTOR_FAILED: Motor {motor_id} requires Arduino interface"
                        arduino_cmd = f"ENABLE_MOTOR:{motor_id}"
                        if self.arduino_interface.send_command(arduino_cmd):
                            response = self.arduino_interface.read_data(timeout=1.0)
                            return f"ENABLE_MOTOR{motor_id}_SUCCESS" if not response else f"ENABLE_MOTOR{motor_id}_SUCCESS:{response}"
                        return f"ENABLE_MOTOR{motor_id}_FAILED"
                    
                    elif motor_id == 5:
                        logger.info(f"Motor 5 enable command")
                        return f"ENABLE_MOTOR5_SUCCESS (GPIO control - implementation pending)"
                    
                except (ValueError, IndexError):
                    return "ENABLE_MOTOR_FAILED: Invalid format"

            elif command.startswith("DISABLE_MOTOR:"):
                try:
                    motor_id = int(command.split(":")[1])
                    if motor_id < 1 or motor_id > 5:
                        return f"DISABLE_MOTOR_FAILED: Motor ID must be 1-5"
                    
                    if motor_id >= 1 and motor_id <= 4:
                        if not self.arduino_interface or not self.arduino_interface.is_connected():
                            return f"DISABLE_MOTOR_FAILED: Motor {motor_id} requires Arduino interface"
                        arduino_cmd = f"DISABLE_MOTOR:{motor_id}"
                        if self.arduino_interface.send_command(arduino_cmd):
                            response = self.arduino_interface.read_data(timeout=1.0)
                            return f"DISABLE_MOTOR{motor_id}_SUCCESS" if not response else f"DISABLE_MOTOR{motor_id}_SUCCESS:{response}"
                        return f"DISABLE_MOTOR{motor_id}_FAILED"
                    
                    elif motor_id == 5:
                        logger.info(f"Motor 5 disable command")
                        return f"DISABLE_MOTOR5_SUCCESS (GPIO control - implementation pending)"
                    
                except (ValueError, IndexError):
                    return "DISABLE_MOTOR_FAILED: Invalid format"

            elif command.startswith("SET_MOTOR_SPEED:"):
                try:
                    parts = command.split(":")
                    if len(parts) < 3:
                        return "SET_MOTOR_SPEED_FAILED: Invalid format (expected: SET_MOTOR_SPEED:ID:SPEED)"
                    motor_id = int(parts[1])
                    speed = float(parts[2])
                    
                    if motor_id < 1 or motor_id > 5:
                        return f"SET_MOTOR_SPEED_FAILED: Motor ID must be 1-5"
                    
                    if motor_id >= 1 and motor_id <= 4:
                        if not self.arduino_interface or not self.arduino_interface.is_connected():
                            return f"SET_MOTOR_SPEED_FAILED: Motor {motor_id} requires Arduino interface"
                        arduino_cmd = f"SET_MOTOR_SPEED:{motor_id}:{speed}"
                        if self.arduino_interface.send_command(arduino_cmd):
                            response = self.arduino_interface.read_data(timeout=1.0)
                            return f"SET_MOTOR_SPEED{motor_id}_SUCCESS:{speed}" if not response else f"SET_MOTOR_SPEED{motor_id}_SUCCESS:{response}"
                        return f"SET_MOTOR_SPEED{motor_id}_FAILED"
                    
                    elif motor_id == 5:
                        logger.info(f"Motor 5 speed set to {speed}")
                        return f"SET_MOTOR_SPEED5_SUCCESS:{speed} (GPIO control - implementation pending)"
                    
                except (ValueError, IndexError):
                    return "SET_MOTOR_SPEED_FAILED: Invalid format"

            elif command.startswith("MOVE_VAR:"):
                try:
                    steps = int(command.split(":")[1])
                    if self.arduino_interface and self.arduino_interface.is_connected():
                        arduino_cmd = f"MOVE_MOTOR:1:{steps}:FORWARD"
                        if self.arduino_interface.send_command(arduino_cmd):
                            response = self.arduino_interface.read_data(timeout=2.0)
                            return f"MOVE_VAR_SUCCESS:{steps}" if not response else f"MOVE_VAR_SUCCESS:{response}"
                        return f"MOVE_VAR_FAILED: Arduino send error"
                    else:
                        logger.warning("MOVE_VAR command requires Arduino interface")
                        return f"MOVE_VAR_FAILED: Arduino interface not available"
                except (ValueError, IndexError):
                    return "MOVE_VAR_FAILED: Invalid format"

            elif command.startswith("ARDUINO:"):
                if not self.arduino_interface:
                    return "ARDUINO_COMMAND_FAILED: Arduino interface not available"
                if not self.arduino_interface.is_connected():
                    return "ARDUINO_COMMAND_FAILED: Arduino not connected"
                try:
                    arduino_cmd = command[8:]
                    if self.arduino_interface.send_command(arduino_cmd):
                        response = self.arduino_interface.read_data(timeout=1.0)
                        if response:
                            return f"ARDUINO_RESPONSE:{response}"
                        else:
                            return "ARDUINO_COMMAND_SENT"
                    else:
                        return "ARDUINO_COMMAND_FAILED: Send error"
                except Exception as e:
                    logger.error(f"Error forwarding command to Arduino: {e}")
                    return f"ARDUINO_COMMAND_FAILED: {e}"

            else:
                logger.warning(f"Unknown command: {command}")
                return f"ERROR: Unknown command '{command}'"

        except Exception as e:
            logger.error(f"Error processing command '{command}': {e}")
            return f"ERROR: {e}"
