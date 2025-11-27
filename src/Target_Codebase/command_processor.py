import threading
import logging
from typing import Optional, Callable, Dict, Union
from bundled_interface import BundledInterface

logger = logging.getLogger("CommandProcessor")

PRESSURE_SENSOR_CHANNELS: Dict[int, Dict[str, Union[int, str]]] = {
    1: {"channel": 0, "name": "Turbo Pressure Sensor", "label": "P01"},
    2: {"channel": 1, "name": "Fusor Pressure Sensor", "label": "P02"},
    3: {"channel": 2, "name": "Foreline Pressure Sensor", "label": "P03"},
}

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
        bundled_interface: BundledInterface,
        host_callback: Optional[Callable[[str], None]] = None,
    ):
        self.bundled_interface = bundled_interface
        self.host_callback = host_callback
        self._callback_lock = threading.Lock()

        logger.info("Command processor initialized with Bundled Interface")

    @property
    def gpio_handler(self):
        return self.bundled_interface.get_gpio()

    @property
    def adc(self):
        return self.bundled_interface.get_adc()

    @property
    def arduino_interface(self):
        return self.bundled_interface.get_arduino()

    def _forward_analog_command(self, label: Optional[str], value) -> None:
        if not label:
            return
        self.bundled_interface.send_analog_to_arduino(label, value)

    def _resolve_valve_label(self, valve_id: int) -> str:
        return VALVE_ANALOG_LABELS.get(valve_id, f"VALVE_{valve_id}")

    def set_host_callback(self, callback: Callable[[str], None]):
        with self._callback_lock:
            self.host_callback = callback
        logger.info("Host callback set")

    def process_command(self, command: str) -> str:
        if not command:
            return "ERROR: Empty command"

        command = command.strip().upper()

        try:
            if command == "LED_ON":
                if not self.gpio_handler:
                    return "LED_ON_FAILED: GPIO not available"
                success, message = self.gpio_handler.led_on()
                if success:
                    return "LED_ON_SUCCESS"
                else:
                    return f"LED_ON_FAILED: {message}"

            elif command == "LED_OFF":
                if not self.gpio_handler:
                    return "LED_OFF_FAILED: GPIO not available"
                success, message = self.gpio_handler.led_off()
                if success:
                    return "LED_OFF_SUCCESS"
                else:
                    return f"LED_OFF_FAILED: {message}"

            elif (
                command == "POWER_SUPPLY_ENABLE"
                or command == "POWER_SUPPLY_ENABLE:1"
                or command == "POWER_SUPPLY_ENABLE:ON"
            ):
                if not self.gpio_handler:
                    return "POWER_SUPPLY_ENABLE_FAILED: GPIO not available"
                if self.gpio_handler.set_power_supply_enable(True):
                    return "POWER_SUPPLY_ENABLE_SUCCESS"
                else:
                    return "POWER_SUPPLY_ENABLE_FAILED"

            elif (
                command == "POWER_SUPPLY_DISABLE"
                or command == "POWER_SUPPLY_ENABLE:0"
                or command == "POWER_SUPPLY_ENABLE:OFF"
            ):
                if not self.gpio_handler:
                    return "POWER_SUPPLY_DISABLE_FAILED: GPIO not available"
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

                    if self.gpio_handler and self.gpio_handler.set_valve_position(
                        valve_id, position
                    ):
                        self._forward_analog_command(
                            self._resolve_valve_label(valve_id),
                            position,
                        )
                        return f"SET_VALVE{valve_id}_SUCCESS:{position}"
                    else:
                        self._forward_analog_command(
                            self._resolve_valve_label(valve_id),
                            position,
                        )
                        return f"SET_VALVE{valve_id}_SUCCESS:{position} (via Arduino)"
                except (ValueError, IndexError):
                    return "SET_VALVE_FAILED: Invalid format"

            elif command.startswith("SET_MECHANICAL_PUMP:"):
                try:
                    power = int(command.split(":")[1])
                    if power < 0 or power > 100:
                        return "SET_MECHANICAL_PUMP_FAILED: Power must be 0-100"
                    if (
                        self.gpio_handler
                        and self.gpio_handler.set_mechanical_pump_power(power)
                    ):
                        self._forward_analog_command(
                            ANALOG_COMPONENT_LABELS["MECHANICAL_PUMP"],
                            power,
                        )
                        return f"SET_MECHANICAL_PUMP_SUCCESS:{power}"
                    else:
                        self._forward_analog_command(
                            ANALOG_COMPONENT_LABELS["MECHANICAL_PUMP"],
                            power,
                        )
                        return f"SET_MECHANICAL_PUMP_SUCCESS:{power} (via Arduino)"
                except (ValueError, IndexError):
                    return "SET_MECHANICAL_PUMP_FAILED: Invalid format"

            elif command.startswith("SET_TURBO_PUMP:"):
                try:
                    power = int(command.split(":")[1])
                    if power < 0 or power > 100:
                        return "SET_TURBO_PUMP_FAILED: Power must be 0-100"
                    if self.gpio_handler and self.gpio_handler.set_turbo_pump_power(
                        power
                    ):
                        self._forward_analog_command(
                            ANALOG_COMPONENT_LABELS["TURBO_PUMP"],
                            power,
                        )
                        return f"SET_TURBO_PUMP_SUCCESS:{power}"
                    else:
                        self._forward_analog_command(
                            ANALOG_COMPONENT_LABELS["TURBO_PUMP"],
                            power,
                        )
                        return f"SET_TURBO_PUMP_SUCCESS:{power} (via Arduino)"
                except (ValueError, IndexError):
                    return "SET_TURBO_PUMP_FAILED: Invalid format"

            elif command == "STARTUP":
                logger.info("Startup command received")
                return "STARTUP_SUCCESS"

            elif command == "SHUTDOWN":
                if self.gpio_handler:
                    self.gpio_handler.set_power_supply_enable(False)
                    for i in range(1, 7):
                        self.gpio_handler.set_valve_position(i, 0)
                    self.gpio_handler.set_mechanical_pump_power(0)
                    self.gpio_handler.set_turbo_pump_power(0)

                for i in range(1, 5):
                    self._forward_analog_command(self._resolve_valve_label(i), 0)
                self._forward_analog_command(
                    ANALOG_COMPONENT_LABELS["MECHANICAL_PUMP"], 0
                )
                self._forward_analog_command(ANALOG_COMPONENT_LABELS["TURBO_PUMP"], 0)

                logger.info("Shutdown sequence completed")
                return "SHUTDOWN_SUCCESS"

            elif command == "EMERGENCY_SHUTOFF":
                if self.gpio_handler and self.gpio_handler.emergency_shutdown():
                    for i in range(1, 5):
                        self._forward_analog_command(self._resolve_valve_label(i), 0)
                    self._forward_analog_command(
                        ANALOG_COMPONENT_LABELS["MECHANICAL_PUMP"], 0
                    )
                    self._forward_analog_command(
                        ANALOG_COMPONENT_LABELS["TURBO_PUMP"], 0
                    )
                    return "EMERGENCY_SHUTOFF_SUCCESS"
                else:
                    for i in range(1, 5):
                        self._forward_analog_command(self._resolve_valve_label(i), 0)
                    self._forward_analog_command(
                        ANALOG_COMPONENT_LABELS["MECHANICAL_PUMP"], 0
                    )
                    self._forward_analog_command(
                        ANALOG_COMPONENT_LABELS["TURBO_PUMP"], 0
                    )
                    return "EMERGENCY_SHUTOFF_SUCCESS (via Arduino)"

            elif command == "READ_POWER_SUPPLY_VOLTAGE":
                if not self.adc or not self.adc.is_initialized():
                    return "READ_POWER_SUPPLY_VOLTAGE_FAILED: ADC not initialized"
                try:
                    adc_value = self.adc.read_channel(0)
                    voltage = self.adc.convert_to_voltage(adc_value) * 10
                    response = f"POWER_SUPPLY_VOLTAGE:{voltage:.2f}"
                    with self._callback_lock:
                        callback = self.host_callback
                    if callback:
                        callback(response)
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
                    with self._callback_lock:
                        callback = self.host_callback
                    if callback:
                        callback(response)
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

                    sensor_info = PRESSURE_SENSOR_CHANNELS.get(sensor_id)
                    if not sensor_info:
                        return f"READ_PRESSURE_SENSOR_FAILED: Invalid sensor ID {sensor_id}"

                    channel = sensor_info["channel"]
                    sensor_name = sensor_info["name"]
                    sensor_label = sensor_info["label"]

                    adc_value = self.adc.read_channel(channel)
                    pressure = (adc_value / 1023.0) * 100.0
                    response = f"PRESSURE_SENSOR_{sensor_id}_VALUE:{pressure:.2f}|{sensor_label}|{sensor_name}"
                    with self._callback_lock:
                        callback = self.host_callback
                    if callback:
                        callback(response)
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
                    with self._callback_lock:
                        callback = self.host_callback
                    if callback:
                        callback(response)
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
                    with self._callback_lock:
                        callback = self.host_callback
                    if callback:
                        callback(response)
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
                if not self.gpio_handler:
                    return "READ_INPUT_FAILED: GPIO not available"
                value = self.gpio_handler.read_input()
                if value is not None:
                    response = f"INPUT_VALUE:{value}"
                    with self._callback_lock:
                        callback = self.host_callback
                    if callback:
                        callback(f"GPIO_INPUT:{value}")
                    return response
                else:
                    return "READ_INPUT_FAILED"

            elif command == "READ_ADC":
                if not self.adc or not self.adc.is_initialized():
                    return "READ_ADC_FAILED: ADC not initialized"

                try:
                    adc_values = self.adc.read_all_channels()
                    response = f"ADC_DATA:{','.join(map(str, adc_values))}"
                    with self._callback_lock:
                        callback = self.host_callback
                    if callback:
                        callback(response)
                    return response
                except Exception as e:
                    logger.error(f"ADC read error: {e}")
                    return f"READ_ADC_FAILED: {e}"

            elif command.startswith("READ_PRESSURE_BY_NAME:"):
                try:
                    sensor_name = command.split(":", 1)[1].strip().upper()
                    sensor_id = None

                    for sid, info in PRESSURE_SENSOR_CHANNELS.items():
                        if (
                            sensor_name in info["name"].upper()
                            or sensor_name == info["label"]
                        ):
                            sensor_id = sid
                            break

                    if sensor_id is None:
                        return f"READ_PRESSURE_BY_NAME_FAILED: Unknown sensor name '{sensor_name}'. Use: Turbo, Fusor, Foreline, P01, P02, or P03"

                    return self.process_command(f"READ_PRESSURE_SENSOR:{sensor_id}")
                except (ValueError, IndexError):
                    return "READ_PRESSURE_BY_NAME_FAILED: Invalid format (expected: READ_PRESSURE_BY_NAME:Turbo|Fusor|Foreline|P01|P02|P03)"
                except Exception as e:
                    logger.error(f"Error reading pressure sensor by name: {e}")
                    return f"READ_PRESSURE_BY_NAME_FAILED: {e}"

            elif command.startswith("SET_PUMP_POWER:"):
                try:
                    power = int(command.split(":")[1])
                    if power < 0 or power > 100:
                        return "SET_PUMP_POWER_FAILED: Power must be 0-100"
                    if (
                        self.gpio_handler
                        and self.gpio_handler.set_mechanical_pump_power(power)
                    ):
                        self._forward_analog_command(
                            ANALOG_COMPONENT_LABELS["LEGACY_PUMP"],
                            power,
                        )
                        return f"SET_MECHANICAL_PUMP_SUCCESS:{power}"
                    else:
                        self._forward_analog_command(
                            ANALOG_COMPONENT_LABELS["LEGACY_PUMP"],
                            power,
                        )
                        return f"SET_MECHANICAL_PUMP_SUCCESS:{power} (via Arduino)"
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

                    if motor_id < 1 or motor_id > 4:
                        return f"MOVE_MOTOR_FAILED: Motor ID must be 1-4"

                    response = self.bundled_interface.send_motor_command(
                        motor_id, "MOVE_MOTOR", steps, direction
                    )
                    if response:
                        return f"MOVE_MOTOR{motor_id}_SUCCESS:{response}"
                    else:
                        return f"MOVE_MOTOR{motor_id}_FAILED"

                except (ValueError, IndexError) as e:
                    return f"MOVE_MOTOR_FAILED: Invalid format - {e}"

            elif command.startswith("ENABLE_MOTOR:"):
                try:
                    motor_id = int(command.split(":")[1])
                    if motor_id < 1 or motor_id > 4:
                        return f"ENABLE_MOTOR_FAILED: Motor ID must be 1-4"

                    response = self.bundled_interface.send_motor_command(
                        motor_id, "ENABLE_MOTOR"
                    )
                    if response:
                        return (
                            f"ENABLE_MOTOR{motor_id}_SUCCESS:{response}"
                            if response
                            else f"ENABLE_MOTOR{motor_id}_SUCCESS"
                        )
                    else:
                        return f"ENABLE_MOTOR{motor_id}_FAILED"

                except (ValueError, IndexError):
                    return "ENABLE_MOTOR_FAILED: Invalid format"

            elif command.startswith("DISABLE_MOTOR:"):
                try:
                    motor_id = int(command.split(":")[1])
                    if motor_id < 1 or motor_id > 4:
                        return f"DISABLE_MOTOR_FAILED: Motor ID must be 1-4"

                    response = self.bundled_interface.send_motor_command(
                        motor_id, "DISABLE_MOTOR"
                    )
                    if response:
                        return (
                            f"DISABLE_MOTOR{motor_id}_SUCCESS:{response}"
                            if response
                            else f"DISABLE_MOTOR{motor_id}_SUCCESS"
                        )
                    else:
                        return f"DISABLE_MOTOR{motor_id}_FAILED"

                except (ValueError, IndexError):
                    return "DISABLE_MOTOR_FAILED: Invalid format"

            elif command.startswith("SET_MOTOR_SPEED:"):
                try:
                    parts = command.split(":")
                    if len(parts) < 3:
                        return "SET_MOTOR_SPEED_FAILED: Invalid format (expected: SET_MOTOR_SPEED:ID:SPEED)"
                    motor_id = int(parts[1])
                    speed = float(parts[2])

                    if motor_id < 1 or motor_id > 4:
                        return f"SET_MOTOR_SPEED_FAILED: Motor ID must be 1-4"

                    response = self.bundled_interface.send_motor_command(
                        motor_id, "SET_MOTOR_SPEED", speed
                    )
                    if response:
                        return f"SET_MOTOR_SPEED{motor_id}_SUCCESS:{speed}"
                    else:
                        return f"SET_MOTOR_SPEED{motor_id}_FAILED"

                except (ValueError, IndexError):
                    return "SET_MOTOR_SPEED_FAILED: Invalid format"

            elif command.startswith("SET_MOTOR_POSITION:"):
                try:
                    parts = command.split(":")
                    if len(parts) < 3:
                        return "SET_MOTOR_POSITION_FAILED: Invalid format (expected: SET_MOTOR_POSITION:ID:PERCENTAGE)"

                    motor_id = int(parts[1])
                    percentage = float(parts[2])

                    if motor_id < 1 or motor_id > 4:
                        return f"SET_MOTOR_POSITION_FAILED: Motor ID must be 1-4"

                    if percentage < 0 or percentage > 100:
                        return f"SET_MOTOR_POSITION_FAILED: Percentage must be 0-100"

                    if self.bundled_interface.send_motor_object(motor_id, percentage):
                        motor_degree = (
                            self.bundled_interface.validator.map_percentage_to_degree(
                                percentage
                            )
                        )
                        return f"SET_MOTOR_POSITION{motor_id}_SUCCESS:{percentage}% ({motor_degree}°)"
                    else:
                        return f"SET_MOTOR_POSITION{motor_id}_FAILED"

                except (ValueError, IndexError) as e:
                    return f"SET_MOTOR_POSITION_FAILED: Invalid format - {e}"

            elif command.startswith("MOVE_VAR:"):
                try:
                    steps = int(command.split(":")[1])
                    if self.arduino_interface and self.arduino_interface.is_connected():
                        arduino_cmd = f"MOVE_MOTOR:1:{steps}:FORWARD"
                        if self.arduino_interface.send_command(arduino_cmd):
                            response = self.arduino_interface.read_data(timeout=2.0)
                            return (
                                f"MOVE_VAR_SUCCESS:{steps}"
                                if not response
                                else f"MOVE_VAR_SUCCESS:{response}"
                            )
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
