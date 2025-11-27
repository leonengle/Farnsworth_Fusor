import socket
import threading
import logging
from typing import Optional, Callable

logger = logging.getLogger("UDPDataClient")


class UDPDataClient:
    def __init__(
        self,
        target_ip: str = "192.168.0.2",
        target_port: int = 12345,
        data_callback: Optional[Callable[[str], None]] = None,
    ):
        self.target_ip = target_ip
        self.target_port = target_port
        self.data_callback = data_callback
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.receiver_thread: Optional[threading.Thread] = None
        self._running_lock = threading.Lock()
        self._callback_lock = threading.Lock()

        logger.info(f"UDP Data Client initialized for {target_ip}:{target_port}")

    def set_data_callback(self, callback: Callable[[str], None]):
        with self._callback_lock:
            self.data_callback = callback
        logger.info("Data callback set")

    def start(self):
        with self._running_lock:
            if self.running:
                logger.warning("UDP data client is already running")
                return

            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.socket.bind(("0.0.0.0", self.target_port))
                self.socket.settimeout(1.0)

                self.running = True
                self.receiver_thread = threading.Thread(
                    target=self._receive_loop, daemon=True
                )
                self.receiver_thread.start()
                logger.info(
                    f"UDP data client started - listening on port {self.target_port}"
                )
            except Exception as e:
                logger.error(f"Failed to start UDP data client: {e}")
                self.running = False

    def _receive_loop(self):
        logger.info("UDP data receive loop started")

        while True:
            with self._running_lock:
                if not self.running:
                    break

            try:
                data, address = self.socket.recvfrom(1024)
                message = data.decode("utf-8").strip()

                if message:
                    logger.debug(f"Received data from {address}: {message}")

                    callback = None
                    with self._callback_lock:
                        callback = self.data_callback

                    if callback:
                        callback(message)

            except socket.timeout:
                continue
            except Exception as e:
                with self._running_lock:
                    if self.running:
                        logger.error(f"UDP data receive error: {e}")
                break

        logger.info("UDP data receive loop ended")

    def stop(self):
        with self._running_lock:
            self.running = False

        if self.receiver_thread:
            self.receiver_thread.join(timeout=2)

        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing UDP socket: {e}")
            self.socket = None

        logger.info("UDP data client stopped")

    def is_connected(self) -> bool:
        with self._running_lock:
            return self.socket is not None and self.running
