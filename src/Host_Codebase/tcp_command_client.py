"""
TCP Command Client for Host System
This replaces the SSH client functionality with a TCP-based command client.

Features:
- TCP client to send commands to target
- Connection management with automatic reconnection
- Response handling
"""

import socket
import logging
from typing import Optional

# Setup logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TCPCommandClient")


class TCPCommandClient:
    """
    TCP client for sending commands from host to target system.
    """
    
    def __init__(self, target_ip: str = "192.168.0.2", target_port: int = 2222):
        """
        Initialize the TCP command client.
        
        Args:
            target_ip: IP address of the target system
            target_port: TCP port on target system
        """
        self.target_ip = target_ip
        self.target_port = target_port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.connection_timeout = 10
        self.receive_timeout = 5
        
        logger.info(f"TCP Command Client initialized for {target_ip}:{target_port}")
    
    def connect(self) -> bool:
        """
        Connect to the target system.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.connection_timeout)
            
            # Connect to target
            self.socket.connect((self.target_ip, self.target_port))
            self.connected = True
            
            logger.info(f"TCP connection established to {self.target_ip}:{self.target_port}")
            return True
            
        except socket.timeout:
            logger.error(f"TCP connection timeout: Could not connect to {self.target_ip}:{self.target_port} within {self.connection_timeout}s")
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
        except ConnectionRefusedError:
            logger.error(f"TCP connection refused: {self.target_ip}:{self.target_port} - Is target running and listening?")
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
        except OSError as e:
            if e.errno == 10051:  # Windows: Network unreachable
                logger.error(f"Network unreachable: Cannot reach {self.target_ip}:{self.target_port}")
            elif e.errno == 10061:  # Windows: Connection refused
                logger.error(f"TCP connection refused: {self.target_ip}:{self.target_port} - Is target running?")
            else:
                logger.error(f"TCP connection failed (OSError {e.errno}): {e}")
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
        """Disconnect from the target system."""
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
                logger.info("TCP connection closed")
            except Exception as e:
                logger.error(f"Error closing TCP connection: {e}")
            self.socket = None
    
    def send_command(self, command: str, wait_response: bool = True) -> Optional[str]:
        """
        Send a command to the target system.
        
        Args:
            command: Command string to send
            wait_response: Whether to wait for and return response
            
        Returns:
            Response string if wait_response is True, None otherwise
        """
        if not self.connected or not self.socket:
            logger.warning("TCP client not connected")
            if not self.connect():
                return None
        
        try:
            # Send command with newline terminator
            message = command.strip() + "\n"
            self.socket.send(message.encode('utf-8'))
            logger.debug(f"TCP command sent: {command}")
            
            if wait_response:
                # Wait for response
                self.socket.settimeout(self.receive_timeout)
                response = self.socket.recv(1024).decode('utf-8').strip()
                logger.debug(f"TCP response received: {response}")
                return response
            else:
                return None
                
        except socket.timeout:
            logger.warning(f"Timeout waiting for response to command: {command}")
            return None
        except Exception as e:
            logger.error(f"TCP send failed: {e}")
            self.connected = False
            # Try to reconnect
            if self.connect():
                # Retry sending
                try:
                    message = command.strip() + "\n"
                    self.socket.send(message.encode('utf-8'))
                    if wait_response:
                        self.socket.settimeout(self.receive_timeout)
                        response = self.socket.recv(1024).decode('utf-8').strip()
                        return response
                except Exception as retry_e:
                    logger.error(f"Retry send failed: {retry_e}")
            return None
    
    def is_connected(self) -> bool:
        """Check if TCP client is connected."""
        return self.connected and self.socket is not None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
