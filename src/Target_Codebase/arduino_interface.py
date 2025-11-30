import serial
import serial.tools.list_ports
import time
import threading
import json
from queue import Queue
from typing import Optional, Callable, Dict
from logging_setup import setup_logging, get_logger

setup_logging()
logger = get_logger("ArduinoInterface")


class ArduinoInterface:
    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 9600,
        timeout: float = 1.0,
        auto_detect: bool = True,
        data_callback: Optional[Callable[[str], None]] = None,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.auto_detect = auto_detect
        self.data_callback = data_callback

        self._serial_connection: Optional[serial.Serial] = None
        self.connected = False
        self.read_thread: Optional[threading.Thread] = None
        self.running = False
        self._connection_lock = threading.Lock()
        self._running_lock = threading.Lock()
        self._callback_lock = threading.Lock()
        self._response_queue = Queue()

        logger.info(
            f"Arduino interface initialized (port={port}, baudrate={baudrate}, "
            f"auto_detect={auto_detect})"
        )

    def _detect_arduino_port(self) -> Optional[str]:
        try:
            ports = serial.tools.list_ports.comports()

            if not ports:
                logger.warning("No serial ports found on system")
                return None

            logger.info(f"Found {len(ports)} serial port(s):")
            for port_info in ports:
                try:
                    vid = getattr(port_info, "vid", None)
                    if vid is not None:
                        vid_str = f"{vid:04X}"
                    else:
                        vid_str = "N/A"
                except (AttributeError, TypeError, ValueError):
                    vid_str = "N/A"

                try:
                    pid = getattr(port_info, "pid", None)
                    if pid is not None:
                        pid_str = f"{pid:04X}"
                    else:
                        pid_str = "N/A"
                except (AttributeError, TypeError, ValueError):
                    pid_str = "N/A"

                try:
                    description = getattr(port_info, "description", None) or "N/A"
                    device = getattr(port_info, "device", "N/A")
                except (AttributeError, TypeError):
                    description = "N/A"
                    device = "N/A"

                logger.info(
                    f"  - {device}: {description} " f"(VID={vid_str}, PID={pid_str})"
                )

            for port_info in ports:
                if not port_info.device:
                    continue
                description_upper = (
                    port_info.description.upper() if port_info.description else ""
                )
                if any(
                    identifier in description_upper
                    for identifier in [
                        "ARDUINO",
                        "USB",
                        "SERIAL",
                        "CH340",
                        "FTDI",
                        "CP210",
                        "PL2303",
                    ]
                ):
                    desc = port_info.description if port_info.description else "N/A"
                    logger.info(
                        f"Auto-detected Arduino on port: {port_info.device} "
                        f"({desc})"
                    )
                    return port_info.device

            for port_info in ports:
                device = port_info.device
                if not device:
                    continue
                if (
                    device.startswith("/dev/ttyUSB")
                    or device.startswith("/dev/ttyACM")
                    or device.startswith("/dev/ttyAMA")
                ):
                    desc = port_info.description if port_info.description else "N/A"
                    logger.info(f"Auto-detected USB serial port: {device} " f"({desc})")
                    return device

            if len(ports) == 1 and ports[0].device:
                desc = ports[0].description if ports[0].description else "N/A"
                logger.info(
                    f"Only one port found, using it: {ports[0].device} " f"({desc})"
                )
                return ports[0].device

            logger.warning(
                "No Arduino port auto-detected - multiple ports found or no USB serial ports"
            )
            logger.warning("Try specifying port manually with --arduino-port argument")
            return None
        except Exception as e:
            logger.error(f"Error during Arduino port detection: {e}")
            return None

    def connect(self) -> bool:
        with self._connection_lock:
            if (
                self.connected
                and self._serial_connection
                and self._serial_connection.is_open
            ):
                logger.debug("Already connected to Arduino")
                return True

            try:
                if self.port is None and self.auto_detect:
                    self.port = self._detect_arduino_port()
                    if self.port is None:
                        logger.error("Cannot connect: Arduino port not found")
                        return False

                if self.port is None:
                    logger.error("Cannot connect: No port specified")
                    return False

                self._serial_connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    write_timeout=self.timeout,
                )

                time.sleep(2.0)

                self.connected = True
                logger.info(
                    f"Connected to Arduino on port {self.port} at {self.baudrate} baud"
                )
                
                logger.info("Waiting for Arduino startup message...")
                time.sleep(2.0)
                
                startup_messages = []
                for i in range(20):
                    if self._serial_connection.in_waiting > 0:
                        line = (
                            self._serial_connection.readline()
                            .decode("utf-8", errors="ignore")
                            .strip()
                        )
                        if line:
                            startup_messages.append(line)
                            logger.info(f"Arduino startup message: {line}")
                            if self.data_callback:
                                try:
                                    self.data_callback(line)
                                except Exception as e:
                                    logger.error(f"Error in startup callback: {e}")
                    elif i == 0:
                        logger.info(f"Checking for startup messages (attempt {i+1}/20)...")
                    time.sleep(0.2)
                
                if not startup_messages:
                    logger.warning("No startup messages received from Arduino - may not be responding")
                    logger.warning("This could mean:")
                    logger.warning("  1. Arduino is not powered on")
                    logger.warning("  2. Arduino firmware is not running")
                    logger.warning("  3. Wrong baud rate (expected 9600)")
                    logger.warning("  4. USB cable issue")
                else:
                    logger.info(f"Received {len(startup_messages)} startup message(s) from Arduino")

                with self._running_lock:
                    self.running = True
                    self.read_thread = threading.Thread(
                        target=self._read_loop, daemon=True
                    )
                    self.read_thread.start()

                return True

            except serial.SerialException as e:
                logger.error(f"Serial connection error: {e}")
                self.connected = False
                return False
            except Exception as e:
                logger.error(f"Unexpected error connecting to Arduino: {e}")
                self.connected = False
                return False

    def disconnect(self):
        with self._running_lock:
            self.running = False

        with self._connection_lock:
            self.connected = False

        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)

        with self._connection_lock:
            if self._serial_connection and self._serial_connection.is_open:
                try:
                    self._serial_connection.close()
                    logger.info("Disconnected from Arduino")
                except Exception as e:
                    logger.error(f"Error closing serial connection: {e}")

            self._serial_connection = None

    def _read_loop(self):
        while True:
            with self._running_lock:
                if not self.running:
                    break

            with self._connection_lock:
                if not self.connected:
                    break

                serial_conn = self._serial_connection

            try:
                if serial_conn and serial_conn.is_open:
                    if serial_conn.in_waiting > 0:
                        line = (
                            serial_conn.readline()
                            .decode("utf-8", errors="ignore")
                            .strip()
                        )
                        if line:
                            logger.info(f"Received from Arduino: {line}")
                            
                            self._response_queue.put(line)

                            callback = None
                            with self._callback_lock:
                                callback = self.data_callback

                            if callback:
                                try:
                                    callback(line)
                                except Exception as e:
                                    logger.error(f"Error in data callback: {e}")
                else:
                    break
                time.sleep(0.01)
            except serial.SerialException as e:
                logger.error(f"Serial read error: {e}")
                with self._connection_lock:
                    self.connected = False
                break
            except Exception as e:
                logger.error(f"Unexpected error in read loop: {e}")
                time.sleep(0.1)

    def send_command(self, command: str) -> bool:
        if not command or not command.strip():
            logger.warning("Cannot send empty command to Arduino")
            return False
            
        with self._connection_lock:
            if (
                not self.connected
                or not self._serial_connection
                or not self._serial_connection.is_open
            ):
                logger.warning("Cannot send command: Not connected to Arduino")
                return False

            try:
                if not command.endswith("\n"):
                    command += "\n"

                encoded = command.encode("utf-8")
                bytes_written = self._serial_connection.write(encoded)
                self._serial_connection.flush()
                logger.info(f"Sent to Arduino ({bytes_written} bytes): {command.strip()}")
                if bytes_written != len(encoded):
                    logger.warning(f"Only wrote {bytes_written} of {len(encoded)} bytes to Arduino")
                    return False
                return True
            except serial.SerialException as e:
                logger.error(f"Serial write error: {e}")
                self.connected = False
                return False
            except Exception as e:
                logger.error(f"Unexpected error sending command: {e}")
                return False

    def send_data(self, data: str) -> bool:
        if not data or not data.strip():
            logger.warning("Cannot send empty data to Arduino")
            return False
        return self.send_command(data)

    def send_analog_command(self, component_label: str, value) -> bool:
        if not component_label:
            logger.warning("Analog command missing component label")
            return False
        if isinstance(value, float):
            value_str = f"{value:.2f}".rstrip("0").rstrip(".")
            if not value_str:
                value_str = "0"
        else:
            value_str = str(value)
        command = f"ANALOG:{component_label}:{value_str}"
        return self.send_command(command)

    def send_motor_object(self, component_name: str, motor_degree: float) -> bool:
        if not component_name:
            logger.warning("Motor command missing component name")
            return False

        try:
            motor_object = {
                "component_name": component_name,
                "motor_degree": float(motor_degree),
            }
            command_json = json.dumps(motor_object)
            command = f"MOTOR:{command_json}"
            logger.info(f"Sending motor object to Arduino: {command}")
            result = self.send_command(command)
            if result:
                logger.info(f"Motor command sent successfully: {component_name} -> {motor_degree}°")
            else:
                logger.error(f"Failed to send motor command: {component_name} -> {motor_degree}°")
            return result
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid motor degree value: {motor_degree} - {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating motor command object: {e}")
            return False

    def read_data(self, timeout: Optional[float] = None) -> Optional[str]:
        if (
            not self.connected
            or not self._serial_connection
            or not self._serial_connection.is_open
        ):
            logger.warning("Cannot read data: Not connected to Arduino")
            return None

        try:
            if timeout is None:
                timeout = 1.0
            
            logger.debug(f"Waiting for Arduino response (timeout: {timeout}s)...")
            try:
                response = self._response_queue.get(timeout=timeout)
                logger.info(f"Received response from Arduino: {response}")
                return response
            except:
                logger.warning(f"No response from Arduino within {timeout} seconds")
                return None

        except Exception as e:
            logger.error(f"Unexpected error reading data: {e}")
            return None

    def is_connected(self) -> bool:
        with self._connection_lock:
            if self._serial_connection and self._serial_connection.is_open:
                return self.connected
            return False
    
    @property
    def serial_connection(self):
        return self._serial_connection

    def set_data_callback(self, callback: Callable[[str], None]):
        with self._callback_lock:
            self.data_callback = callback
        logger.info("Data callback set for Arduino interface")

    def cleanup(self):
        self.disconnect()
        logger.info("Arduino interface cleaned up")
