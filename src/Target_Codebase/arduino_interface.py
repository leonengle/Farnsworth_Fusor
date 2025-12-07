import serial
import serial.tools.list_ports
import time
import threading
from queue import Queue
from typing import Optional, Callable
from logging_setup import setup_logging, get_logger

setup_logging()
logger = get_logger("ArduinoInterface")

ARDUINO_VID_PID_PAIRS = {
    # Genuine Arduino AVR Boards
    (0x2341, 0x0043): "Arduino Uno",
    (0x2341, 0x0001): "Arduino Uno (older)",
    (0x2341, 0x0010): "Arduino Nano",
    (0x2341, 0x0036): "Arduino Leonardo",
    (0x2341, 0x8036): "Arduino Leonardo (bootloader)",
    (0x2341, 0x0243): "Arduino Mega 2560",
    
    # Arduino Clones (same VID as genuine)
    (0x2A03, 0x0043): "Arduino Uno (clone)",
    (0x2A03, 0x0001): "Arduino Uno (clone, older)",
    (0x2A03, 0x0010): "Arduino Nano (clone)",
    
    # CH340/CH341 USB-to-Serial (very common in Arduino Nano clones)
    (0x1A86, 0x7523): "Arduino Nano (CH340)",
    (0x1A86, 0x5523): "Arduino Nano (CH341)",
    (0x1A86, 0x5512): "Arduino Nano (CH340G)",
    
    # FTDI USB-to-Serial (common in Arduino Nano)
    (0x0403, 0x6001): "Arduino Nano (FTDI FT232)",
    (0x0403, 0x6015): "Arduino Nano (FTDI FT232H)",
    
    # Silicon Labs CP210x USB-to-Serial (Arduino Nano clones)
    (0x10C4, 0xEA60): "Arduino Nano (CP2102)",
    (0x10C4, 0xEA61): "Arduino Nano (CP2103)",
    
    # Prolific PL2303 (less common Arduino Nano variant)
    (0x067B, 0x2303): "Arduino Nano (PL2303)",
}

def identify_board_type(vid: Optional[int], pid: Optional[int], description: Optional[str]):
    """Identify Arduino board type from VID/PID and description.
    
    Returns:
        tuple: (is_arduino: bool, board_type: str)
    """
    if vid is not None and pid is not None:
        board_name = ARDUINO_VID_PID_PAIRS.get((vid, pid))
        if board_name:
            return True, board_name
    
    if description:
        desc_upper = description.upper()
        if "NANO" in desc_upper:
            return True, "Arduino Nano (detected by description)"
        elif "UNO" in desc_upper:
            return True, "Arduino Uno (detected by description)"
        elif "LEONARDO" in desc_upper:
            return True, "Arduino Leonardo (detected by description)"
        elif "MEGA" in desc_upper:
            return True, "Arduino Mega (detected by description)"
        elif any(chip in desc_upper for chip in ["CH340", "CH341", "FTDI", "CP210", "PL2303"]):
            return True, f"Arduino-compatible USB Serial ({description})"
    
    return False, "Unknown"


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

    @staticmethod
    def list_available_ports() -> list:
        ports_info = []
        try:
            ports = serial.tools.list_ports.comports()
            for port_info in ports:
                try:
                    vid = getattr(port_info, "vid", None)
                    pid = getattr(port_info, "pid", None)
                    is_arduino = False
                    if vid is not None and pid is not None:
                        is_arduino = (vid, pid) in ARDUINO_VID_PID_PAIRS
                    
                    is_arduino, board_type = identify_board_type(vid, pid, port_info.description)
                    
                    port_data = {
                        "device": port_info.device or "N/A",
                        "description": port_info.description or "N/A",
                        "vid": f"{vid:04X}" if vid is not None else "N/A",
                        "pid": f"{pid:04X}" if pid is not None else "N/A",
                        "hwid": port_info.hwid or "N/A",
                        "manufacturer": port_info.manufacturer or "N/A",
                        "product": port_info.product or "N/A",
                        "serial_number": port_info.serial_number or "N/A",
                        "board_type": board_type,
                        "is_arduino": is_arduino,
                    }
                    ports_info.append(port_data)
                except Exception as e:
                    logger.warning(f"Error reading port info: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error listing serial ports: {e}")
        return ports_info

    def _detect_arduino_port(self) -> Optional[str]:
        try:
            ports = serial.tools.list_ports.comports()

            if not ports:
                logger.warning("No serial ports found on system")
                return None

            logger.info(f"Scanning {len(ports)} serial port(s) for Arduino...")
            
            arduino_ports = []
            other_ports = []
            
            for port_info in ports:
                if not port_info.device:
                    continue
                    
                try:
                    vid = getattr(port_info, "vid", None)
                    pid = getattr(port_info, "pid", None)
                    description = getattr(port_info, "description", None) or "N/A"
                    device = port_info.device
                    
                    vid_str = f"{vid:04X}" if vid is not None else "N/A"
                    pid_str = f"{pid:04X}" if pid is not None else "N/A"
                    
                    is_arduino, board_type = identify_board_type(vid, pid, description)
                    
                    is_usb_serial = (
                        device.startswith("/dev/ttyUSB")
                        or device.startswith("/dev/ttyACM")
                        or device.startswith("/dev/ttyAMA")
                    )
                    
                    port_data = {
                        "device": device,
                        "description": description,
                        "vid": vid_str,
                        "pid": pid_str,
                        "board_type": board_type,
                        "is_arduino": is_arduino,
                        "is_usb_serial": is_usb_serial,
                    }
                    
                    if is_arduino:
                        arduino_ports.insert(0, port_data)
                        logger.info(
                            f"  ✓ {board_type} detected on {device} "
                            f"(VID={vid_str}, PID={pid_str}, Description: {description})"
                        )
                    elif is_usb_serial:
                        other_ports.append(port_data)
                        logger.info(
                            f"  → USB Serial port: {device} - {description} "
                            f"(VID={vid_str}, PID={pid_str})"
                        )
                    else:
                        logger.debug(
                            f"  - Other port: {device} - {description} "
                            f"(VID={vid_str}, PID={pid_str})"
                        )
                except Exception as e:
                    logger.warning(f"Error processing port {port_info.device}: {e}")
                    continue

            if arduino_ports:
                selected = arduino_ports[0]
                logger.info(
                    f"Auto-selected Arduino port: {selected['device']} "
                    f"({selected['board_type']}) - {selected['description']}"
                )
                logger.info(
                    f"Board details: VID={selected['vid']}, PID={selected['pid']}, "
                    f"Device={selected['device']}"
                )
                return selected["device"]

            if other_ports:
                selected = other_ports[0]
                logger.info(
                    f"Auto-selected USB serial port: {selected['device']} "
                    f"({selected['description']})"
                )
                return selected["device"]

            if len(ports) == 1 and ports[0].device:
                desc = ports[0].description if ports[0].description else "N/A"
                logger.info(
                    f"Only one port found, using it: {ports[0].device} ({desc})"
                )
                return ports[0].device

            logger.warning(
                "No Arduino port auto-detected - multiple ports found or no USB serial ports"
            )
            logger.warning("Available ports:")
            for port_info in ports:
                if port_info.device:
                    desc = port_info.description or "N/A"
                    vid = f"{port_info.vid:04X}" if port_info.vid else "N/A"
                    pid = f"{port_info.pid:04X}" if port_info.pid else "N/A"
                    logger.warning(f"  - {port_info.device}: {desc} (VID={vid}, PID={pid})")
            logger.warning("Try specifying port manually with --arduino-port argument")
            return None
        except Exception as e:
            logger.error(f"Error during Arduino port detection: {e}")
            return None

    def test_port(self, port: Optional[str] = None, timeout: float = 2.0) -> bool:
        test_port = port or self.port
        if not test_port:
            return False
        
        test_connection = None
        try:
            logger.info(f"Testing port {test_port} for Arduino...")
            test_connection = serial.Serial(
                port=test_port,
                baudrate=self.baudrate,
                timeout=timeout,
                write_timeout=timeout,
            )
            
            time.sleep(0.5)
            
            startup_detected = False
            for _ in range(10):
                if test_connection.in_waiting > 0:
                    line = test_connection.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        logger.info(f"Port {test_port} responded: {line}")
                        if "READY" in line.upper() or "ARDUINO" in line.upper():
                            startup_detected = True
                            break
                time.sleep(0.2)
            
            test_connection.close()
            return startup_detected
        except serial.SerialException as e:
            logger.warning(f"Port {test_port} test failed: {e}")
            if test_connection and test_connection.is_open:
                try:
                    test_connection.close()
                except:
                    pass
            return False
        except Exception as e:
            logger.warning(f"Error testing port {test_port}: {e}")
            if test_connection and test_connection.is_open:
                try:
                    test_connection.close()
                except:
                    pass
            return False

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
                    logger.info("Auto-detecting Arduino port (like Arduino IDE)...")
                    self.port = self._detect_arduino_port()
                    if self.port is None:
                        logger.error("Cannot connect: Arduino port not found")
                        logger.info("Use list_available_ports() to see all available ports")
                        return False

                if self.port is None:
                    logger.error("Cannot connect: No port specified")
                    return False

                logger.info(f"Connecting to Arduino on {self.port} at {self.baudrate} baud...")
                self._serial_connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    write_timeout=self.timeout,
                )

                try:
                    self._serial_connection.dtr = False
                    self._serial_connection.rts = False
                    time.sleep(0.1)
                    self._serial_connection.dtr = True
                    self._serial_connection.rts = True
                    time.sleep(2.0)
                except Exception as e:
                    logger.warning(f"Could not toggle DTR/RTS for reset: {e}")

                self.connected = True
                logger.info(
                    f"Connected to Arduino on port {self.port} at {self.baudrate} baud"
                )
                
                logger.info("Waiting for Arduino startup message...")
                
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
                    
                    logger.info("Attempting to test Arduino responsiveness...")
                    try:
                        test_cmd = "TEST_PING\n"
                        self._serial_connection.write(test_cmd.encode("utf-8"))
                        self._serial_connection.flush()
                        time.sleep(0.5)
                        if self._serial_connection.in_waiting > 0:
                            response = self._serial_connection.readline().decode("utf-8", errors="ignore").strip()
                            logger.info(f"Arduino responded to test: {response}")
                        else:
                            logger.warning("Arduino did not respond to test command - firmware may not be running")
                    except Exception as e:
                        logger.error(f"Error testing Arduino: {e}")
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
                            
                            try:
                                self._response_queue.put_nowait(line)
                                logger.debug(f"Added to response queue (size: {self._response_queue.qsize()})")
                            except:
                                logger.warning("Response queue full, dropping message")

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

    def send_motor_object(self, component_name: str, motor_degree: float, percentage: Optional[float] = None, direction: Optional[str] = None) -> bool:
        if not component_name:
            logger.warning("Motor command missing component name")
            return False

        try:
            angle = int(round(float(motor_degree)))
            motor_id = None
            if component_name.upper().startswith("MOTOR_"):
                try:
                    motor_id = int(component_name.upper().replace("MOTOR_", ""))
                except ValueError:
                    pass
            
            if motor_id == 5:
                if angle < 0 or angle > 300:
                    logger.error(f"VARIAC motor degree out of range: {angle} (must be 0-300)")
                    return False
            else:
                if angle < 0 or angle > 360:
                    logger.error(f"Motor degree out of range: {angle} (must be 0-360)")
                    return False
                if angle == 360:
                    angle = 0
            
            command = f"{component_name}:{angle}"
            direction_info = f" ({direction})" if direction else ""
            percentage_info = f" [{percentage}%]" if percentage is not None else ""
            logger.info(f"Sending motor command to Arduino: {command}{direction_info}{percentage_info}")
            result = self.send_command(command)
            if result:
                logger.info(f"Motor command sent successfully: {component_name} -> {angle}°{direction_info}{percentage_info}")
            else:
                logger.error(f"Failed to send motor command: {component_name} -> {angle}°{direction_info}{percentage_info}")
            return result
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid motor degree value: {motor_degree} - {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating motor command: {e}")
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
            
            logger.info(f"Waiting for Arduino response (timeout: {timeout}s)...")
            logger.info(f"Response queue size before wait: {self._response_queue.qsize()}")
            
            try:
                response = self._response_queue.get(timeout=timeout)
                logger.info(f"Received response from Arduino: {response}")
                return response
            except:
                queue_size = self._response_queue.qsize()
                logger.warning(f"No response from Arduino within {timeout} seconds (queue size: {queue_size})")
                if queue_size > 0:
                    logger.warning(f"Note: {queue_size} message(s) in queue but timeout occurred")
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