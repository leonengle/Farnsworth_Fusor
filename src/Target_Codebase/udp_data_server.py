import socket
import threading
import time
from logging_setup import setup_logging, get_logger
from typing import Optional, Callable

setup_logging()
logger = get_logger("UDPDataServer")


class UDPDataServer:
    def __init__(self, host_ip: str = "192.168.0.1", host_port: int = 12345):
        self.host_ip = host_ip
        self.host_port = host_port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.send_thread: Optional[threading.Thread] = None
        self.send_callback: Optional[Callable[[], str]] = None
        self.send_interval = 1.0

        logger.info(f"UDP Data Server initialized for {host_ip}:{host_port}")

    def set_send_callback(self, callback: Callable[[], str]):
        self.send_callback = callback
        logger.info("UDP data send callback set")

    def start(self):
        if self.running:
            logger.warning("UDP data server is already running")
            return

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.running = True
            self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
            self.send_thread.start()
            logger.info(f"UDP Data server started - sending to {self.host_ip}:{self.host_port}")
        except Exception as e:
            logger.error(f"UDP data server error: {e}")
            self.running = False

    def _send_loop(self):
        logger.info("UDP data send loop started - sending updates only when values change or errors occur")

        while self.running:
            try:
                if self.send_callback:
                    data = self.send_callback()
                    if data:
                        message = data.encode("utf-8")
                        self.socket.sendto(message, (self.host_ip, self.host_port))
                        logger.debug(f"Data sent to host via UDP: {data}")

                time.sleep(self.send_interval)

            except Exception as e:
                logger.error(f"Error in UDP data send loop: {e}")
                time.sleep(self.send_interval)

        logger.info("UDP data send loop ended")

    def stop(self):
        self.running = False

        if self.send_thread:
            self.send_thread.join(timeout=2)

        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing UDP socket: {e}")
            self.socket = None

        logger.info("UDP Data server stopped")

