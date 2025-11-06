"""
UDP Status Server for Target System
This provides UDP-based status and heartbeat communication.

Features:
- UDP server for sending status/heartbeat messages to host
- UDP client for receiving status updates from host
"""

import socket
import threading
from typing import Optional, Callable
from logging_setup import setup_logging, get_logger

# Setup logging for this module
setup_logging()
logger = get_logger("UDPStatusServer")


class UDPStatusSender:
    """
    UDP sender for sending status/heartbeat messages to host.
    """
    
    def __init__(self, host_ip: str = "192.168.0.1", host_port: int = 8888):
        """
        Initialize the UDP status sender.
        
        Args:
            host_ip: IP address of the host system
            host_port: UDP port on host system
        """
        self.host_ip = host_ip
        self.host_port = host_port
        self.socket: Optional[socket.socket] = None
        
        logger.info(f"UDP Status Sender initialized for {host_ip}:{host_port}")
    
    def start(self):
        """Start the UDP sender."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info("UDP sender socket created")
        except Exception as e:
            logger.error(f"Failed to create UDP socket: {e}")
    
    def send_status(self, status: str) -> bool:
        """
        Send a status message to the host.
        
        Args:
            status: Status message string
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.socket:
            logger.warning("UDP socket not initialized")
            return False
        
        try:
            message = status.encode('utf-8')
            self.socket.sendto(message, (self.host_ip, self.host_port))
            logger.debug(f"UDP status sent: {status}")
            return True
        except Exception as e:
            logger.error(f"UDP send failed: {e}")
            return False
    
    def stop(self):
        """Stop the UDP sender."""
        if self.socket:
            try:
                self.socket.close()
                logger.info("UDP sender socket closed")
            except Exception as e:
                logger.error(f"Error closing UDP socket: {e}")
            self.socket = None


class UDPStatusReceiver:
    """
    UDP receiver for receiving status updates from host.
    """
    
    def __init__(self, listen_port: int = 8889, callback: Optional[Callable[[str, tuple], None]] = None):
        """
        Initialize the UDP status receiver.
        
        Args:
            listen_port: UDP port to listen on
            callback: Optional callback function for received messages
        """
        self.listen_port = listen_port
        self.callback = callback
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.receiver_thread: Optional[threading.Thread] = None
        
        logger.info(f"UDP Status Receiver initialized for port {listen_port}")
    
    def start(self):
        """Start the UDP receiver thread."""
        if self.running:
            logger.warning("UDP receiver already running")
            return
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(("0.0.0.0", self.listen_port))
            self.socket.settimeout(1.0)  # Allow periodic checking of self.running
            
            self.running = True
            self.receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receiver_thread.start()
            
            logger.info(f"UDP receiver started on port {self.listen_port}")
        except Exception as e:
            logger.error(f"Failed to start UDP receiver: {e}")
    
    def _receive_loop(self):
        """Main loop for receiving UDP messages."""
        logger.info("UDP receive loop started")
        
        while self.running:
            try:
                data, address = self.socket.recvfrom(1024)
                message = data.decode('utf-8').strip()
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
        """Stop the UDP receiver."""
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
