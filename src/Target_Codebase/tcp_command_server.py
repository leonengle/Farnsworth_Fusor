import threading
import time
import socket

from logging_setup import setup_logging, get_logger
from typing import Optional, Callable
from bundled_interface import BundledInterface
from command_processor import CommandProcessor

# setup logging for this module
setup_logging()
logger = get_logger("TCPCommandServer")


class TCPCommandServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 2222,
        bundled_interface: Optional[BundledInterface] = None,
    ):
        self.host = host
        self.port = port
        self.server_socket = None
        self.server_thread = None
        self.running = False
        self.bundled_interface = bundled_interface

        self.command_processor = CommandProcessor(
            bundled_interface=self.bundled_interface,
            host_callback=None,
        )

        logger.info(f"TCP Command Server initialized (Bundled Interface: {'Available' if bundled_interface else 'Not available'})")

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
        gpio = self.bundled_interface.get_gpio() if self.bundled_interface else None
        return gpio.read_input() if gpio else None

    def read_adc_channel(self, channel: int) -> int:
        adc = self.bundled_interface.get_adc() if self.bundled_interface else None
        if adc and adc.is_initialized():
            return adc.read_channel(channel)
        return 0

    def read_adc_all_channels(self) -> list:
        adc = self.bundled_interface.get_adc() if self.bundled_interface else None
        if adc and adc.is_initialized():
            return adc.read_all_channels()
        return [0] * 8

    @property
    def gpio_handler(self):
        return self.bundled_interface.get_gpio() if self.bundled_interface else None

    @property
    def adc(self):
        return self.bundled_interface.get_adc() if self.bundled_interface else None

    def cleanup(self):
        self.stop_server()
        if self.bundled_interface:
            self.bundled_interface.cleanup()
        logger.info("TCP Command Server cleanup complete")
