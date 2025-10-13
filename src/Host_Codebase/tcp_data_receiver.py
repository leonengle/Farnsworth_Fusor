# tcp_data_receiver.py
"""
Host-side TCP server for receiving sensor data from the target system.
- Listens on port 8888 for incoming data from Raspberry Pi
- Receives GPIO and ADC data every 1 second
- Provides callback mechanism for GUI integration
"""

import socket
import threading
import logging
import os
import argparse
from typing import Optional, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("tcp_data_receiver.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TCPDataReceiver")

class TCPDataReceiver:
    def __init__(self, host: str = None, port: int = None):
        # Use environment variables or defaults
        self.host = host or os.getenv('FUSOR_HOST_IP', '0.0.0.0')
        self.port = port or int(os.getenv('FUSOR_TCP_PORT', '8888'))
        self.server_socket = None
        self.running = False
        self.server_thread = None
        self.data_callback: Optional[Callable[[str], None]] = None
        
        logger.info(f"TCP Data Receiver initialized (Host: {self.host}, Port: {self.port})")
    
    def set_data_callback(self, callback: Callable[[str], None]):
        """Set the function that will be called when data is received."""
        self.data_callback = callback
        logger.info("Data callback set")
    
    def _handle_client(self, client_socket, client_address):
        """Handle individual client connections."""
        logger.info(f"TCP client connected from {client_address}")
        
        try:
            while self.running:
                # Receive data from client
                data = client_socket.recv(1024).decode('utf-8').strip()
                if not data:
                    break
                
                logger.info(f"Received data from {client_address}: {data}")
                
                # Call the data callback if set
                if self.data_callback:
                    self.data_callback(data)
                
                # Send acknowledgment back to client
                client_socket.send(b"ACK")
                
        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()
            logger.info(f"TCP client {client_address} disconnected")
    
    def start_server(self):
        """Start the TCP server."""
        if self.running:
            logger.warning("TCP server is already running")
            return
        
        self.running = True
        
        try:
            # Create and configure socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            logger.info(f"TCP Data Receiver started on {self.host}:{self.port}")
            
            # Main server loop - accept connections
            while self.running:
                try:
                    # Set timeout to allow Ctrl+C to work
                    self.server_socket.settimeout(1.0)
                    client_socket, client_address = self.server_socket.accept()
                    
                    # Handle each connection in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.timeout:
                    # Timeout is normal - allows Ctrl+C to work
                    continue
                except socket.error as e:
                    if self.running:
                        logger.error(f"Socket error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"TCP server error: {e}")
        finally:
            self.stop_server()
    
    def stop_server(self):
        """Stop the TCP server."""
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")
        
        logger.info("TCP Data Receiver stopped")
    
    def start_in_background(self):
        """Start the TCP server in a background thread."""
        if self.server_thread and self.server_thread.is_alive():
            logger.warning("TCP server thread is already running")
            return
        
        self.server_thread = threading.Thread(target=self.start_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        logger.info("TCP Data Receiver started in background thread")


def parse_sensor_data(data: str) -> dict:
    """Parse sensor data received from target."""
    try:
        if data.startswith("GPIO_INPUT:"):
            value = int(data.split(":")[1])
            return {"type": "GPIO", "pin": 6, "value": value}
        elif data.startswith("ADC_DATA:"):
            value = int(data.split(":")[1])
            return {"type": "ADC", "channel": 0, "value": value}
        else:
            logger.warning(f"Unknown data format: {data}")
            return {"type": "UNKNOWN", "data": data}
    except Exception as e:
        logger.error(f"Error parsing sensor data '{data}': {e}")
        return {"type": "ERROR", "data": data}


def main():
    """Test the TCP data receiver with configurable parameters."""
    parser = argparse.ArgumentParser(description="TCP Data Receiver - Host Server for Fusor Target")
    parser.add_argument("--host", default=None,
                       help="Host IP to bind to (default: from FUSOR_HOST_IP env var or 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None,
                       help="TCP port (default: from FUSOR_TCP_PORT env var or 8888)")
    
    args = parser.parse_args()
    
    # Use command line args or environment variables or defaults
    host = args.host or os.getenv('FUSOR_HOST_IP', '0.0.0.0')
    port = args.port or int(os.getenv('FUSOR_TCP_PORT', '8888'))
    
    logger.info(f"Starting TCP Data Receiver on {host}:{port}")
    
    receiver = TCPDataReceiver(host, port)
    
    def data_handler(data):
        """Handle received data."""
        parsed = parse_sensor_data(data)
        print(f"Received: {parsed}")
    
    receiver.set_data_callback(data_handler)
    
    try:
        receiver.start_server()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        receiver.stop_server()


if __name__ == "__main__":
    main()
