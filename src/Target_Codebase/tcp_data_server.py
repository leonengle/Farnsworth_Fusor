import socket
import threading
import time
from logging_setup import setup_logging, get_logger
from typing import Optional, Callable

# Setup logging for this module
setup_logging()
logger = get_logger("TCPDataServer")


class TCPDataServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 12345):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.client_address = None
        self.server_thread: Optional[threading.Thread] = None
        self.send_thread: Optional[threading.Thread] = None
        self.running = False
        self.send_callback: Optional[Callable[[], str]] = None
        self.send_interval = 1.0

        logger.info(f"TCP Data Server initialized for {host}:{port}")

    def set_send_callback(self, callback: Callable[[], str]):
        self.send_callback = callback
        logger.info("TCP data send callback set")

    def start_server(self):
        if self.running:
            logger.warning("TCP data server is already running")
            return

        self.running = True

        try:
            # Create and configure socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.settimeout(1.0)  # Allow periodic checking
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)  # Listen for one connection at a time

            logger.info(f"TCP Data server listening on {self.host}:{self.port}")

            # Start server thread
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()

        except Exception as e:
            logger.error(f"TCP data server error: {e}")
            self.running = False

    def _server_loop(self):
        while self.running:
            try:
                # Accept connection from host
                client_socket, client_address = self.server_socket.accept()
                logger.info(f"Host connected from {client_address}")

                self.client_socket = client_socket
                self.client_address = client_address

                # Start sending data to this client
                if self.send_thread and self.send_thread.is_alive():
                    # Stop previous send thread
                    pass

                self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
                self.send_thread.start()

                # Wait for client to disconnect
                try:
                    while self.running:
                        data = client_socket.recv(1024)
                        if not data:
                            break
                except socket.error:
                    pass

                logger.info(f"Host disconnected from {client_address}")
                self.client_socket = None
                self.client_address = None

            except socket.timeout:
                # Timeout is expected, continue to check self.running
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"TCP data server error: {e}")
                break

    def _send_loop(self):
        logger.info("TCP data send loop started - sending periodic updates every {:.1f}s".format(self.send_interval))

        while self.running and self.client_socket:
            try:
                if self.send_callback:
                    data = self.send_callback()
                    if data:
                        # Send data with newline terminator
                        message = data + "\n"
                        self.client_socket.send(message.encode("utf-8"))
                        logger.info(f"Periodic data sent to host: {data}")
                    else:
                        logger.debug("No data to send (callback returned empty)")

                time.sleep(self.send_interval)

            except socket.error as e:
                logger.debug(f"TCP data send error: {e}")
                break
            except Exception as e:
                logger.error(f"Error in send loop: {e}")
                time.sleep(self.send_interval)

        logger.info("TCP data send loop ended")

    def stop_server(self):
        self.running = False

        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception as e:
                logger.error(f"Error closing client socket: {e}")
            self.client_socket = None

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")
            self.server_socket = None

        logger.info("TCP Data server stopped")
