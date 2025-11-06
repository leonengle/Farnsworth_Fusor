import logging
from tcp_command_client import TCPCommandClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("communication.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Communication")

class TCPClient:
    def __init__(self, host, port, command_template):
        self.host = host
        self.port = port
        self.command_template = command_template
        self.client = None
        
    def connect(self):
        try:
            self.client = TCPCommandClient(self.host, self.port)
            if self.client.connect():
                logger.info(f"Connected to {self.host}:{self.port}")
                return True
            else:
                logger.error(f"Failed to connect to {self.host}:{self.port}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def send_tcp_command(self, bitstring):
        if not self.client or not self.client.is_connected():
            logger.error("Not connected to TCP server")
            return None
            
        try:
            command = self.command_template.format(bitstring)
            response = self.client.send_command(command)
            if response:
                logger.info(f"Command sent: {command}, Response: {response}")
            else:
                logger.warning(f"Command sent: {command}, No response")
            return response
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return None
    
    def disconnect(self):
        if self.client:
            self.client.disconnect()
            logger.info("Disconnected from TCP server")