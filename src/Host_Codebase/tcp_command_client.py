import socket
import logging
from typing import Optional
from base_classes import CommunicationClientInterface

# Setup logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TCPCommandClient")


class TCPCommandClient(CommunicationClientInterface):
    def __init__(self, target_ip: str = "192.168.0.2", target_port: int = 2222):
        super().__init__(target_ip, target_port)
        self.socket: Optional[socket.socket] = None
        self.connection_timeout = 10
        self.receive_timeout = 5

        logger.info(f"TCP Command Client initialized for {target_ip}:{target_port}")

    def connect(self) -> bool:
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.connection_timeout)
            self.socket.connect((self.target_ip, self.target_port))
            self.connected = True
            logger.info(
                f"TCP connection established to {self.target_ip}:{self.target_port}"
            )
            return True
        except socket.timeout:
            logger.error(
                f"TCP connection timeout: Could not connect to {self.target_ip}:{self.target_port} within {self.connection_timeout}s"
            )
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
        except Exception as e:
            logger.error(f"TCP connection failed ({type(e).__name__}): {e}")
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
            return False

    def disconnect(self):
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
                logger.info("TCP connection closed")
            except Exception as e:
                logger.error(f"Error closing TCP connection: {e}")
            self.socket = None

    def send_command(self, command: str, wait_response: bool = True) -> Optional[str]:
        if not self.connected or not self.socket:
            logger.warning("TCP client not connected")
            if not self.connect():
                return None

        try:
            message = command.strip() + "\n"
            self.socket.send(message.encode("utf-8"))
            logger.debug(f"TCP command sent: {command}")

            if wait_response:
                self.socket.settimeout(self.receive_timeout)
                response = self.socket.recv(1024).decode("utf-8").strip()
                logger.debug(f"TCP response received: {response}")
                return response
            return None
        except Exception as e:
            logger.error(f"TCP send failed: {e}")
            self.connected = False
            return None

    def is_connected(self) -> bool:
        return self.connected and self.socket is not None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
