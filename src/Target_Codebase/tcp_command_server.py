import threading
import time
import socket

from logging_setup import setup_logging, get_logger
from typing import Optional, Callable

# Import real ADC - no mock fallback
from adc import MCP3008ADC
from gpio_handler import GPIOHandler
from command_processor import CommandProcessor

# setup logging for this module
setup_logging()
logger = get_logger("TCPCommandServer")


class TCPCommandServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 2222,
        led_pin: int = 26,
        input_pin: int = 6,
        use_adc: bool = False,
        arduino_interface=None,
    ):
        self.host = host
        self.port = port
        self.server_socket = None
        self.server_thread = None
        self.running = False

        # Initialize GPIO handler
        self.gpio_handler = GPIOHandler(led_pin=led_pin, input_pin=input_pin)

        # Initialize ADC if enabled
        self.adc = None
        if use_adc:
            try:
                logger.info("Attempting to initialize ADC (MCP3008)...")
                self.adc = MCP3008ADC()
                if not self.adc.initialize():
                    logger.error("Failed to initialize ADC - hardware may not be connected or libraries missing")
                    logger.error("ADC will not be available. Check SPI connection and Adafruit_MCP3008 library.")
                    self.adc = None
                else:
                    logger.info("ADC initialized successfully")
            except Exception as e:
                logger.error(f"ADC setup error: {e}")
                logger.error("ADC will not be available. Continuing without ADC.")
                self.adc = None
        else:
            logger.info("ADC initialization skipped (use --use-adc flag to enable)")

        # Initialize command processor with Arduino interface
        self.command_processor = CommandProcessor(
            gpio_handler=self.gpio_handler,
            adc=self.adc,
            arduino_interface=arduino_interface,
            host_callback=None,  # Will be set via set_host_callback
        )

        # Log GPIO initialization status
        gpio_status = "Initialized" if self.gpio_handler.initialized else "NOT INITIALIZED"
        logger.info(
            f"TCP Command Server initialized (LED: {led_pin}, Input: {input_pin}, "
            f"ADC: {use_adc}, Arduino: {'Enabled' if arduino_interface else 'Disabled'}, "
            f"GPIO: {gpio_status})"
        )
        if not self.gpio_handler.initialized:
            logger.error("WARNING: GPIO not initialized - LED and GPIO commands will fail!")
            logger.error("Ensure target is running with 'sudo' to access GPIO pins")

    def set_host_callback(self, callback: Callable[[str], None]):
        self.command_processor.set_host_callback(callback)
        logger.info("Host callback set")

    def _handle_command(self, command: str) -> str:
        logger.info(f"Received TCP command: {command}")

        # Strip whitespace and convert to string if needed
        if isinstance(command, bytes):
            command = command.decode("utf-8")
        command = command.strip()

        # Delegate to command processor
        return self.command_processor.process_command(command)

    def _tcp_session_handler(self, client_socket, client_address):
        logger.info(f"TCP session started with {client_address}")

        try:
            client_socket.settimeout(30)  # 30 second timeout for commands

            # Keep connection alive and process commands
            while self.running:
                try:
                    # Receive command from client
                    data = client_socket.recv(1024)
                    if not data:
                        break

                    # Process command
                    command = data.decode("utf-8").strip()
                    response = self._handle_command(command)

                    # Send response back
                    client_socket.send((response + "\n").encode("utf-8"))
                    logger.debug(f"Sent response: {response}")

                except socket.timeout:
                    # Send heartbeat to keep connection alive
                    try:
                        client_socket.send("HEARTBEAT\n".encode("utf-8"))
                    except:
                        break
                    continue
                except socket.error as e:
                    logger.debug(f"Socket error in session: {e}")
                    break

        except Exception as e:
            logger.error(f"TCP session error: {e}")
        finally:
            client_socket.close()
            logger.info(f"TCP session ended with {client_address}")

    def start_server(self):
        if self.running:
            logger.warning("Server is already running")
            return

        self.running = True

        try:
            # create and configure socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.settimeout(
                1.0
            )  # Allow periodic checking of self.running
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)

            logger.info(f"TCP Command server started on {self.host}:{self.port}")

            # main server loop - accept connections
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()

                    # handle each connection in a separate thread
                    session_thread = threading.Thread(
                        target=self._tcp_session_handler,
                        args=(client_socket, client_address),
                    )
                    session_thread.daemon = True
                    session_thread.start()

                except socket.timeout:
                    # Timeout is expected, continue loop to check self.running
                    continue
                except socket.error as e:
                    if self.running:
                        logger.error(f"Socket error: {e}")
                    break

        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.stop_server()

    def stop_server(self):
        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")

        logger.info("TCP Command server stopped")

    def read_input_pin(self) -> Optional[int]:
        return self.gpio_handler.read_input()

    def read_adc_channel(self, channel: int) -> int:
        if self.adc and self.adc.is_initialized():
            return self.adc.read_channel(channel)
        return 0

    def read_adc_all_channels(self) -> list:
        if self.adc and self.adc.is_initialized():
            return self.adc.read_all_channels()
        return [0] * 8

    def cleanup(self):
        self.stop_server()

        # Cleanup GPIO
        self.gpio_handler.cleanup()

        # Cleanup ADC
        if self.adc:
            self.adc.cleanup()

        logger.info("TCP Command Server cleanup complete")


class PeriodicDataSender:
    def __init__(
        self,
        command_server: TCPCommandServer,
        send_callback: Callable[[str], None],
        use_adc: bool = False,
    ):
        self.command_server = command_server
        self.send_callback = send_callback
        self.use_adc = use_adc
        self.running = False
        self.sender_thread = None

        logger.info(f"Periodic data sender initialized (ADC: {self.use_adc})")

    def start(self):
        if self.running:
            logger.warning("Periodic sender is already running")
            return
        self.running = True
        self.sender_thread = threading.Thread(target=self._send_loop)
        self.sender_thread.daemon = True
        self.sender_thread.start()
        logger.info("Periodic data sender started")

    def stop(self):
        self.running = False
        if self.sender_thread:
            self.sender_thread.join(timeout=2)
        logger.info("Periodic data sender stopped")

    def _send_loop(self):
        while self.running:
            try:
                if (
                    self.use_adc
                    and self.command_server.adc
                    and self.command_server.adc.is_initialized()
                ):
                    # send adc data - simple format as per diagram
                    adc_values = self.command_server.read_adc_all_channels()
                    data_message = f"ADC_DATA:{adc_values[0]}"
                    logger.debug(f"Sent ADC data: {adc_values[0]}")
                else:
                    # send gpio data - simple format as per diagram
                    pin_value = self.command_server.read_input_pin()
                    data_message = f"GPIO_INPUT:{pin_value}"
                    logger.debug(f"Sent GPIO data: {pin_value}")

                # send data to host via callback
                if self.send_callback:
                    self.send_callback(data_message)

                # wait 1 second before next send
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"Error in periodic send loop: {e}")
                time.sleep(1.0)
