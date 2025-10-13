# tcp_data_sender.py
"""
Target-side TCP client for sending sensor data to the host system.
- Connects to host TCP server (port 8888)
- Sends GPIO and ADC data every 1 second
- Handles connection failures gracefully
"""

import socket
import time
import logging
import os
import argparse
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("tcp_data_sender.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TCPDataSender")

class TCPDataSender:
    def __init__(self, host: str = None, port: int = None):
        # Use environment variables or defaults
        self.host = host or os.getenv('FUSOR_HOST_IP', '192.168.1.100')
        self.port = port or int(os.getenv('FUSOR_TCP_PORT', '8888'))
        self.socket = None
        self.connected = False
        
        logger.info(f"TCP Data Sender initialized (Host: {self.host}, Port: {self.port})")
    
    def connect(self) -> bool:
        """Connect to the host TCP server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)  # 5 second timeout
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"Connected to host TCP server at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to host: {e}")
            self.connected = False
            return False
    
    def send_data(self, data: str) -> bool:
        """Send data to the host."""
        if not self.connected:
            if not self.connect():
                return False
        
        try:
            # Send data
            self.socket.send(data.encode('utf-8'))
            
            # Wait for acknowledgment
            response = self.socket.recv(1024)
            if response == b"ACK":
                logger.debug(f"Data sent successfully: {data}")
                return True
            else:
                logger.warning(f"Unexpected response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending data: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the host."""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing socket: {e}")
            finally:
                self.socket = None
                self.connected = False
        
        logger.info("Disconnected from host TCP server")
    
    def send_gpio_data(self, pin_value: int) -> bool:
        """Send GPIO data to host."""
        data = f"GPIO_INPUT:{pin_value}"
        return self.send_data(data)
    
    def send_adc_data(self, adc_value: int) -> bool:
        """Send ADC data to host."""
        data = f"ADC_DATA:{adc_value}"
        return self.send_data(data)


def main():
    """Test the TCP data sender with configurable parameters."""
    parser = argparse.ArgumentParser(description="TCP Data Sender - Target Client for Fusor Host")
    parser.add_argument("--host", default=None,
                       help="Host IP address (default: from FUSOR_HOST_IP env var or 192.168.1.100)")
    parser.add_argument("--port", type=int, default=None,
                       help="TCP port (default: from FUSOR_TCP_PORT env var or 8888)")
    
    args = parser.parse_args()
    
    # Use command line args or environment variables or defaults
    host = args.host or os.getenv('FUSOR_HOST_IP', '192.168.1.100')
    port = args.port or int(os.getenv('FUSOR_TCP_PORT', '8888'))
    
    logger.info(f"Starting TCP Data Sender to {host}:{port}")
    
    sender = TCPDataSender(host, port)
    
    try:
        # Test sending some data
        test_data = [
            ("GPIO_INPUT:0", "GPIO"),
            ("GPIO_INPUT:1", "GPIO"),
            ("ADC_DATA:512", "ADC"),
            ("ADC_DATA:768", "ADC")
        ]
        
        for data, data_type in test_data:
            if sender.send_data(data):
                print(f"Successfully sent {data_type} data: {data}")
            else:
                print(f"Failed to send {data_type} data: {data}")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Test interrupted")
    finally:
        sender.disconnect()


if __name__ == "__main__":
    main()
