import serial
import serial.tools.list_ports
import time
import threading
from typing import Optional, Callable
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
        
        self.serial_connection: Optional[serial.Serial] = None
        self.connected = False
        self.read_thread: Optional[threading.Thread] = None
        self.running = False
        
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
                logger.info(
                    f"  - {port_info.device}: {port_info.description} "
                    f"(VID={port_info.vid:04X}, PID={port_info.pid:04X})"
                )
            
            for port_info in ports:
                description_upper = port_info.description.upper() if port_info.description else ""
                if any(
                    identifier in description_upper
                    for identifier in ["ARDUINO", "USB", "SERIAL", "CH340", "FTDI", "CP210", "PL2303"]
                ):
                    logger.info(
                        f"Auto-detected Arduino on port: {port_info.device} "
                        f"({port_info.description})"
                    )
                    return port_info.device
            
            for port_info in ports:
                device = port_info.device
                if device.startswith("/dev/ttyUSB") or device.startswith("/dev/ttyACM") or device.startswith("/dev/ttyAMA"):
                    logger.info(
                        f"Auto-detected USB serial port: {device} "
                        f"({port_info.description})"
                    )
                    return device
            
            if len(ports) == 1:
                logger.info(
                    f"Only one port found, using it: {ports[0].device} "
                    f"({ports[0].description})"
                )
                return ports[0].device
                    
            logger.warning("No Arduino port auto-detected - multiple ports found or no USB serial ports")
            logger.warning("Try specifying port manually with --arduino-port argument")
            return None
        except Exception as e:
            logger.error(f"Error during Arduino port detection: {e}")
            return None

    def connect(self) -> bool:
        if self.connected and self.serial_connection and self.serial_connection.is_open:
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

            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )

            time.sleep(2.0)

            self.connected = True
            logger.info(f"Connected to Arduino on port {self.port} at {self.baudrate} baud")

            self.running = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
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
        self.running = False
        self.connected = False

        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)

        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.close()
                logger.info("Disconnected from Arduino")
            except Exception as e:
                logger.error(f"Error closing serial connection: {e}")

        self.serial_connection = None

    def _read_loop(self):
        while self.running and self.connected:
            try:
                if self.serial_connection and self.serial_connection.is_open:
                    if self.serial_connection.in_waiting > 0:
                        line = self.serial_connection.readline().decode("utf-8", errors="ignore").strip()
                        if line:
                            logger.debug(f"Received from Arduino: {line}")
                            if self.data_callback:
                                try:
                                    self.data_callback(line)
                                except Exception as e:
                                    logger.error(f"Error in data callback: {e}")
                else:
                    break
                time.sleep(0.01)
            except serial.SerialException as e:
                logger.error(f"Serial read error: {e}")
                self.connected = False
                break
            except Exception as e:
                logger.error(f"Unexpected error in read loop: {e}")
                time.sleep(0.1)

    def send_command(self, command: str) -> bool:
        if not self.connected or not self.serial_connection or not self.serial_connection.is_open:
            logger.warning("Cannot send command: Not connected to Arduino")
            return False

        try:
            if not command.endswith("\n"):
                command += "\n"
            
            self.serial_connection.write(command.encode("utf-8"))
            logger.debug(f"Sent to Arduino: {command.strip()}")
            return True
        except serial.SerialException as e:
            logger.error(f"Serial write error: {e}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending command: {e}")
            return False

    def send_data(self, data: str) -> bool:
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

    def read_data(self, timeout: Optional[float] = None) -> Optional[str]:
        if not self.connected or not self.serial_connection or not self.serial_connection.is_open:
            logger.warning("Cannot read data: Not connected to Arduino")
            return None

        try:
            original_timeout = self.serial_connection.timeout
            if timeout is not None:
                self.serial_connection.timeout = timeout

            line = self.serial_connection.readline().decode("utf-8", errors="ignore").strip()
            
            if timeout is not None:
                self.serial_connection.timeout = original_timeout

            if line:
                logger.debug(f"Read from Arduino: {line}")
                return line
            return None

        except serial.SerialException as e:
            logger.error(f"Serial read error: {e}")
            self.connected = False
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading data: {e}")
            return None

    def is_connected(self) -> bool:
        if self.serial_connection and self.serial_connection.is_open:
            return self.connected
        return False

    def set_data_callback(self, callback: Callable[[str], None]):
        self.data_callback = callback
        logger.info("Data callback set for Arduino interface")

    def cleanup(self):
        self.disconnect()
        logger.info("Arduino interface cleaned up")

