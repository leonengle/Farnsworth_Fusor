import socket
import threading
import logging
from typing import Optional, Callable

# Setup logging for this module
logger = logging.getLogger("UDPStatusClient")


class UDPStatusClient:
    def __init__(self, target_ip: str = "192.168.0.2", target_port: int = 8889):
        self.target_ip = target_ip
        self.target_port = target_port
        self.socket: Optional[socket.socket] = None

        logger.info(f"UDP Status Client initialized for {target_ip}:{target_port}")

    def start(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info("UDP client socket created")
        except Exception as e:
            logger.error(f"Failed to create UDP socket: {e}")

    def send_status(self, status: str) -> bool:
        if not self.socket:
            logger.warning("UDP socket not initialized")
            return False

        try:
            message = status.encode("utf-8")
            self.socket.sendto(message, (self.target_ip, self.target_port))
            logger.debug(f"UDP status sent: {status}")
            return True
        except Exception as e:
            logger.error(f"UDP send failed: {e}")
            return False

    def stop(self):
        if self.socket:
            try:
                self.socket.close()
                logger.info("UDP client socket closed")
            except Exception as e:
                logger.error(f"Error closing UDP socket: {e}")
            self.socket = None


class UDPStatusReceiver:
    def __init__(
        self,
        listen_port: int = 8888,
        callback: Optional[Callable[[str, tuple], None]] = None,
    ):
        self.listen_port = listen_port
        self.callback = callback
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.receiver_thread: Optional[threading.Thread] = None

        logger.info(f"UDP Status Receiver initialized for port {listen_port}")

    def start(self):
        if self.running:
            logger.warning("UDP receiver already running")
            return

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(("0.0.0.0", self.listen_port))
            self.socket.settimeout(1.0)  # Allow periodic checking of self.running

            self.running = True
            self.receiver_thread = threading.Thread(
                target=self._receive_loop, daemon=True
            )
            self.receiver_thread.start()

            logger.info(f"UDP receiver started on port {self.listen_port}")
        except Exception as e:
            logger.error(f"Failed to start UDP receiver: {e}")

    def _receive_loop(self):
        logger.info("UDP receive loop started")

        while self.running:
            try:
                data, address = self.socket.recvfrom(1024)
                message = data.decode("utf-8").strip()
                logger.debug(f"UDP message received from {address}: {message}")

                if self.callback:
                    self.callback(message, address)

            except socket.timeout:
                # Timeout is expected, continue loop to check self.running
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"UDP receive error: {e}")
                break

        logger.info("UDP receive loop ended")

    def stop(self):
        self.running = False

        if self.receiver_thread:
            self.receiver_thread.join(timeout=2)

        if self.socket:
            try:
                self.socket.close()
                logger.info("UDP receiver socket closed")
            except Exception as e:
                logger.error(f"Error closing UDP socket: {e}")
            self.socket = None

        logger.info("UDP receiver stopped")
