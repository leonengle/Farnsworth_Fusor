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
                super().__init__(name="TCPCommandClient")
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
                self.logger.info(f"TCP connection established to {self.target_ip}:{self.target_port}")
                return True
            except socket.timeout:
                self.logger.error(f"TCP connection timeout: Could not connect to {self.target_ip}:{self.target_port} within {self.connection_timeout}s")
                self.connected = False
                if self.socket:
                    self.socket.close()
                    self.socket = None
                return False
            except Exception as e:
                self.logger.error(f"TCP connection failed ({type(e).__name__}): {e}")
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
    
        def disconnect(self):
            if self.connected:
                self.connected = False
                if self.socket:
                    self.socket.close()
                    self.socket = None
                self.logger.info("TCP connection closed")
    
        def send_command(self, command: str, wait_response: bool = True) -> Optional[str]:
            if not self.connected or not self.socket:
                self.logger.warning("TCP client not connected")
                return None
                
            message = command.strip() + "\n"
            self.socket.send(message.encode('utf-8'))
            self.logger.debug(f"TCP command sent: {command}")
            
            if wait_response:
                self.socket.settimeout(self.receive_timeout)
                response = self.socket.recv(1024).decode('utf-8').strip()
                self.logger.debug(f"TCP response received: {response}")
                return response
            return None
    
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.disconnect()

