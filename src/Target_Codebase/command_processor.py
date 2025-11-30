import threading
import logging
import time
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


    def _resolve_valve_label(self, valve_id: int) -> str:
        return VALVE_ANALOG_LABELS.get(valve_id, f"VALVE_{valve_id}")

    def _send_status_update(self, message: str):
        with self._callback_lock:
            callback = self.host_callback
        if callback:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Error in host callback: {e}")

    def set_host_callback(self, callback: Callable[[str], None]):
        with self._callback_lock:
            self.host_callback = callback
        logger.info("Host callback set")

    def _validate_and_create_motor_object(self, motor_id: int, percentage: float) -> tuple[bool, Optional[dict], Optional[str]]:
        logger.info(f"Validating motor command: motor_id={motor_id}, percentage={percentage}")
        self._send_status_update(f"Validating motor command: motor_id={motor_id}, percentage={percentage}%")
        
        if motor_id < 1 or motor_id > 6:
            error_msg = f"Invalid motor ID: {motor_id} (must be 1-6)"
            logger.warning(f"Validation failed: {error_msg}")
            self._send_status_update(f"[ERROR] {error_msg}")
            return False, None, error_msg
        
        if percentage < 0 or percentage > 100:
            error_msg = f"Invalid percentage: {percentage} (must be 0-100)"
            logger.warning(f"Validation failed: {error_msg}")
            self._send_status_update(f"[ERROR] {error_msg}")
            return False, None, error_msg
        
        motor_degree = self.bundled_interface.validator.map_percentage_to_degree(percentage)
        component_name = f"MOTOR_{motor_id}"
        
        is_valid, error = self.bundled_interface.validator.validate_motor_degree_object(component_name, motor_degree)
        if not is_valid:
            logger.warning(f"Validation failed: {error}")
            self._send_status_update(f"[ERROR] Validation failed: {error}")
            return False, None, f"Validation failed: {error}"
        
        motor_object = {
            "motor_id": motor_id,
            "motor_degree": motor_degree,
            "component_name": component_name,
            "percentage": percentage
        }
        
        logger.info(f"Motor object created: motor_id={motor_id}, degree={motor_degree}, component={component_name}")
        self._send_status_update(f"Motor object created: {component_name} -> {motor_degree}° (from {percentage}%)")
        return True, motor_object, None

    def process_command(self, command: str) -> str:
        if not command:
            error_msg = "ERROR: Empty command"
            self._send_status_update(error_msg)
            return error_msg

        command = command.strip().upper()
        logger.info(f"Processing command from host: {command}")
        self._send_status_update(f"Processing command: {command}")

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
                return "POWER_SUPPLY_ENABLE_SUCCESS"

            elif (
                command == "POWER_SUPPLY_DISABLE"
                or command == "POWER_SUPPLY_ENABLE:0"
                or command == "POWER_SUPPLY_ENABLE:OFF"
            ):
                return "POWER_SUPPLY_DISABLE_SUCCESS"

            elif command.startswith("SET_VOLTAGE:"):
                try:
                    parts = command.split(":")
                    if len(parts) != 2:
                        return "SET_VOLTAGE_FAILED: Invalid format (expected: SET_VOLTAGE:<voltage>)"
                    
                    voltage = float(parts[1])
                    if voltage < 0 or voltage > 28000:
                        return "SET_VOLTAGE_FAILED: Voltage must be 0-28000"
                    
                    voltage_percentage = (voltage / 28000.0) * 100.0
                    motor_id = 5
                    
                    is_valid, motor_obj, error = self._validate_and_create_motor_object(motor_id, voltage_percentage)
                    if not is_valid:
                        return f"SET_VOLTAGE_FAILED: {error}"
                    
                    if self.bundled_interface.send_motor_object(motor_id, voltage_percentage):
                        logger.info(f"Motor object sent to Arduino: motor_id={motor_obj['motor_id']}, degree={motor_obj['motor_degree']}")
                        result = f"SET_VOLTAGE_SUCCESS:{voltage}V ({voltage_percentage:.1f}% = {motor_obj['motor_degree']}°)"
                        self._send_status_update(result)
                        return result
                    else:
                        error_msg = f"SET_VOLTAGE_FAILED: Could not send to Arduino"
                        self._send_status_update(error_msg)
                        return error_msg
                except (ValueError, IndexError) as e:
                    return f"SET_VOLTAGE_FAILED: Invalid format - {e}"

            elif command.startswith("SET_VALVE"):
                try:
                    parts = command.split(":")
                    if len(parts) != 2:
                        return "SET_VALVE_FAILED: Invalid format (expected: SET_VALVE<id>:<position>)"

                    valve_part = parts[0].replace("SET_VALVE", "")
                    if not valve_part:
                        return "SET_VALVE_FAILED: Missing valve ID"
                    
                    valve_id = int(valve_part)
                    position = float(parts[1])

                    if valve_id < 1 or valve_id > 6:
                        return f"SET_VALVE_FAILED: Valve ID must be 1-6"

                    if position < 0 or position > 100:
                        return f"SET_VALVE_FAILED: Position must be 0-100"

                    if valve_id == 5:
                        motor_id = 6
                    elif valve_id <= 4:
                        motor_id = valve_id
                    else:
                        return f"SET_VALVE_FAILED: Valve ID {valve_id} not mapped to a motor"
                    
                    is_valid, motor_obj, error = self._validate_and_create_motor_object(motor_id, position)
                    if not is_valid:
                        error_msg = f"SET_VALVE{valve_id}_FAILED: {error}"
                        self._send_status_update(error_msg)
                        return error_msg
                    
                    arduino = self.bundled_interface.get_arduino()
                    if not arduino:
                        error_msg = f"SET_VALVE{valve_id}_FAILED: Arduino interface not available"
                        self._send_status_update(error_msg)
                        return error_msg
                    
                    if not arduino.is_connected():
                        error_msg = f"SET_VALVE{valve_id}_FAILED: Arduino not connected"
                        self._send_status_update(error_msg)
                        return error_msg
                    
                    self._send_status_update(f"Sending motor command to Arduino: {motor_obj['component_name']} -> {motor_obj['motor_degree']}°")
                    if self.bundled_interface.send_motor_object(motor_id, position):
                        logger.info(f"Motor object sent to Arduino: motor_id={motor_obj['motor_id']}, degree={motor_obj['motor_degree']}")
                        result = f"SET_VALVE{valve_id}_SUCCESS:{int(position)}% ({motor_obj['motor_degree']}°)"
                        self._send_status_update(result)
                        self._send_status_update("Waiting for Arduino response...")
                        return result
                    else:
                        error_msg = f"SET_VALVE{valve_id}_FAILED: Could not send to Arduino"
                        self._send_status_update(error_msg)
                        return error_msg
                except (ValueError, IndexError) as e:
                    return f"SET_VALVE_FAILED: Invalid format - {e}"

            elif command.startswith("SET_MECHANICAL_PUMP:"):
                try:
                    power = int(command.split(":")[1])
                    if power < 0 or power > 100:
                        return "SET_MECHANICAL_PUMP_FAILED: Power must be 0-100"
                    return f"SET_MECHANICAL_PUMP_SUCCESS:{power}"
                except (ValueError, IndexError):
                    return "SET_MECHANICAL_PUMP_FAILED: Invalid format"

            elif command.startswith("SET_TURBO_PUMP:"):
                try:
                    power = int(command.split(":")[1])
                    if power < 0 or power > 100:
                        return "SET_TURBO_PUMP_FAILED: Power must be 0-100"
                    return f"SET_TURBO_PUMP_SUCCESS:{power}"
                except (ValueError, IndexError):
                    return "SET_TURBO_PUMP_FAILED: Invalid format"

            elif command == "STARTUP":
                logger.info("Startup command received")
                return "STARTUP_SUCCESS"

            elif command == "SHUTDOWN":
                for i in range(1, 7):
                    self.bundled_interface.send_motor_object(i, 0.0)

                logger.info("Shutdown sequence completed")
                return "SHUTDOWN_SUCCESS"

            elif command == "EMERGENCY_SHUTOFF":
                for i in range(1, 7):
                    self.bundled_interface.send_motor_object(i, 0.0)
                
                return "EMERGENCY_SHUTOFF_SUCCESS"

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
                    return f"SET_MECHANICAL_PUMP_SUCCESS:{power}"
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

                    if motor_id < 1 or motor_id > 6:
                        return f"MOVE_MOTOR_FAILED: Motor ID must be 1-6"

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
                    if motor_id < 1 or motor_id > 6:
                        return f"ENABLE_MOTOR_FAILED: Motor ID must be 1-6"

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
                    if motor_id < 1 or motor_id > 6:
                        return f"DISABLE_MOTOR_FAILED: Motor ID must be 1-6"

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

                    if motor_id < 1 or motor_id > 6:
                        return f"SET_MOTOR_SPEED_FAILED: Motor ID must be 1-6"

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
                    if len(parts) != 3:
                        return "SET_MOTOR_POSITION_FAILED: Invalid format (expected: SET_MOTOR_POSITION:<motor_id>:<percentage>)"

                    motor_id = int(parts[1])
                    percentage = float(parts[2])

                    is_valid, motor_obj, error = self._validate_and_create_motor_object(motor_id, percentage)
                    if not is_valid:
                        return f"SET_MOTOR_POSITION_FAILED: {error}"

                    if self.bundled_interface.send_motor_object(motor_id, percentage):
                        logger.info(f"Motor object sent to Arduino: motor_id={motor_obj['motor_id']}, degree={motor_obj['motor_degree']}")
                        result = f"SET_MOTOR_POSITION{motor_id}_SUCCESS:{percentage}% ({motor_obj['motor_degree']}°)"
                        self._send_status_update(result)
                        return result
                    else:
                        return f"SET_MOTOR_POSITION{motor_id}_FAILED: Could not send to Arduino"

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

            elif command == "TEST_ARDUINO" or command.startswith("TEST_ARDUINO:"):
                if not self.arduino_interface:
                    error_msg = "TEST_ARDUINO_FAILED: Arduino interface not available"
                    self._send_status_update(error_msg)
                    return error_msg
                
                if not self.arduino_interface.is_connected():
                    error_msg = "TEST_ARDUINO_FAILED: Arduino not connected"
                    self._send_status_update(error_msg)
                    return error_msg
                
                try:
                    self._send_status_update("Testing Arduino communication...")
                    
                    arduino = self.arduino_interface
                    if hasattr(arduino, 'port'):
                        self._send_status_update(f"Arduino port: {arduino.port}")
                    
                    serial_conn = arduino.serial_connection
                    if serial_conn:
                        if serial_conn.is_open:
                            bytes_waiting = serial_conn.in_waiting
                            self._send_status_update(f"Serial port status: OPEN, {bytes_waiting} bytes waiting in buffer")
                            self._send_status_update(f"Serial port name: {serial_conn.name}")
                            self._send_status_update(f"Serial baudrate: {serial_conn.baudrate}")
                        else:
                            self._send_status_update("WARNING: Serial connection exists but is not open")
                    else:
                        self._send_status_update("WARNING: Serial connection object is None")
                    
                    test_command = "TEST_PING"
                    self._send_status_update(f"Sending test command to Arduino: {test_command}")
                    
                    if not self.arduino_interface.send_command(test_command):
                        error_msg = "TEST_ARDUINO_FAILED: Could not send test command"
                        self._send_status_update(error_msg)
                        return error_msg
                    
                    self._send_status_update("Command sent, waiting 0.5 seconds...")
                    time.sleep(0.5)
                    
                    if serial_conn and serial_conn.is_open:
                        bytes_waiting = serial_conn.in_waiting
                        self._send_status_update(f"After send: {bytes_waiting} bytes waiting in buffer")
                        if bytes_waiting > 0:
                            raw_data = serial_conn.read(bytes_waiting).decode("utf-8", errors="ignore")
                            self._send_status_update(f"Raw data in buffer: {repr(raw_data)}")
                    
                    self._send_status_update("Waiting for Arduino response (timeout: 3 seconds)...")
                    response = self.arduino_interface.read_data(timeout=3.0)
                    
                    if response:
                        result = f"TEST_ARDUINO_SUCCESS: Arduino responded with '{response}'"
                        self._send_status_update(result)
                        return result
                    else:
                        error_msg = "TEST_ARDUINO_FAILED: No response from Arduino (timeout)"
                        self._send_status_update(error_msg)
                        if serial_conn and serial_conn.is_open:
                            bytes_waiting = serial_conn.in_waiting
                            self._send_status_update(f"Final check: {bytes_waiting} bytes still in buffer")
                        return error_msg
                        
                except Exception as e:
                    error_msg = f"TEST_ARDUINO_FAILED: {e}"
                    logger.error(f"Error testing Arduino: {e}")
                    self._send_status_update(error_msg)
                    return error_msg

            elif command.startswith("ARDUINO:"):
                if not self.arduino_interface:
                    return "ARDUINO_COMMAND_FAILED: Arduino interface not available"
                if not self.arduino_interface.is_connected():
                    return "ARDUINO_COMMAND_FAILED: Arduino not connected"
                try:
                    arduino_cmd = command[8:].strip()
                    if not arduino_cmd:
                        return "ARDUINO_COMMAND_FAILED: Empty command after ARDUINO:"
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
                error_msg = f"ERROR: Unknown command '{command}'"
                logger.warning(error_msg)
                self._send_status_update(error_msg)
                return error_msg

        except Exception as e:
            error_msg = f"ERROR: {e}"
            logger.error(f"Error processing command '{command}': {e}")
            self._send_status_update(error_msg)
            return error_msg
