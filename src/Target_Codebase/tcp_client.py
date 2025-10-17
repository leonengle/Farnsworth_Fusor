"""
TCP Client for Target System
This implements TCP communication from Target to Host as described in the system architecture diagram.

Features:
- TCP client that connects to host system
- Sends GPIO pin data every 1 second
- Handles connection failures gracefully
- Supports both GPIO and ADC data transmission
"""

import socket
import time
import threading
from logging_setup import setup_logging, get_logger
from typing import Optional, Callable

# Setup logging for this module
setup_logging()
logger = get_logger("TCPClient")


class TCPClient:
    """
    TCP client for sending data from target to host system.
    """
    
    def __init__(self, host: str = "192.168.1.100", port: int = 12345):
        """
        Initialize the TCP client.
        
        Args:
            host: Host IP address to connect to
            port: TCP port on host system
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        self.send_thread: Optional[threading.Thread] = None
        self.send_callback: Optional[Callable[[str], None]] = None
        
        logger.info(f"TCP Client initialized for {host}:{port}")
    
    def set_send_callback(self, callback: Callable[[str], None]):
        """
        Set the callback function that provides data to send.
        
        Args:
            callback: Function that returns data string to send
        """
        self.send_callback = callback
        logger.info("TCP send callback set")
    
    def connect(self) -> bool:
        """
        Connect to the host system.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # 10 second timeout
            
            # Connect to host
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            logger.info(f"TCP connection established to {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"TCP connection failed: {e}")
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
    
    def disconnect(self):
        """Disconnect from the host system."""
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
                logger.info("TCP connection closed")
            except Exception as e:
                logger.error(f"Error closing TCP connection: {e}")
            self.socket = None
    
    def send_data(self, data: str) -> bool:
        """
        Send data to the host system.
        
        Args:
            data: Data string to send
            
        Returns:
            True if data sent successfully, False otherwise
        """
        if not self.connected or not self.socket:
            logger.warning("TCP client not connected")
            return False
        
        try:
            # Send data with newline terminator
            message = data + "\n"
            self.socket.send(message.encode('utf-8'))
            logger.debug(f"TCP data sent: {data}")
            return True
            
        except Exception as e:
            logger.error(f"TCP send failed: {e}")
            self.connected = False
            return False
    
    def start_periodic_sending(self, interval: float = 1.0):
        """
        Start periodic data sending thread.
        
        Args:
            interval: Send interval in seconds (default: 1.0)
        """
        if self.running:
            logger.warning("Periodic sending already running")
            return
        
        self.running = True
        self.send_thread = threading.Thread(
            target=self._periodic_send_loop, 
            args=(interval,),
            daemon=True
        )
        self.send_thread.start()
        
        logger.info(f"Periodic TCP sending started (interval: {interval}s)")
    
    def stop_periodic_sending(self):
        """Stop periodic data sending."""
        self.running = False
        if self.send_thread:
            self.send_thread.join(timeout=2)
        
        logger.info("Periodic TCP sending stopped")
    
    def _periodic_send_loop(self, interval: float):
        """
        Main loop for periodic data sending.
        
        Args:
            interval: Send interval in seconds
        """
        logger.info("TCP periodic send loop started")
        
        while self.running:
            try:
                # Get data from callback
                if self.send_callback:
                    data = self.send_callback()
                    if data:
                        # Try to send data
                        if not self.send_data(data):
                            # If send failed, try to reconnect
                            logger.warning("Send failed, attempting to reconnect...")
                            if self.connect():
                                # Retry sending
                                self.send_data(data)
                            else:
                                logger.error("Reconnection failed")
                                # Wait longer before retry
                                time.sleep(5)
                
                # Wait for next interval
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in periodic send loop: {e}")
                # Try to reconnect on error
                if not self.is_connected():
                    logger.info("Attempting to reconnect...")
                    self.connect()
                time.sleep(interval)
        
        logger.info("TCP periodic send loop ended")
    
    def is_connected(self) -> bool:
        """Check if TCP client is connected."""
        return self.connected and self.socket is not None


class TargetTCPCommunicator:
    """
    High-level interface for TCP communication from target to host.
    """
    
    def __init__(self, host: str = "192.168.1.100", port: int = 12345):
        """
        Initialize the target TCP communicator.
        
        Args:
            host: Host IP address
            port: TCP port on host
        """
        self.tcp_client = TCPClient(host, port)
        self.max_retries = 3
        self.retry_delay = 1.0
        
        logger.info("Target TCP communicator initialized")
    
    def connect(self) -> bool:
        """Connect to the host system."""
        return self.tcp_client.connect()
    
    def send_gpio_data(self, pin_value: int) -> bool:
        """
        Send GPIO pin data to host.
        
        Args:
            pin_value: GPIO pin value (0 or 1)
            
        Returns:
            True if data sent successfully
        """
        data = f"GPIO_INPUT:{pin_value}"
        return self.tcp_client.send_data(data)
    
    def send_adc_data(self, channel: int, value: int) -> bool:
        """
        Send ADC channel data to host.
        
        Args:
            channel: ADC channel number
            value: ADC reading value
            
        Returns:
            True if data sent successfully
        """
        data = f"ADC_CH{channel}:{value}"
        return self.tcp_client.send_data(data)
    
    def send_adc_all_data(self, adc_values: list) -> bool:
        """
        Send all ADC channel data to host.
        
        Args:
            adc_values: List of ADC values for all channels
            
        Returns:
            True if data sent successfully
        """
        data = f"ADC_DATA:{','.join(map(str, adc_values))}"
        return self.tcp_client.send_data(data)
    
    def start_periodic_sending(self, callback: Callable[[], str], interval: float = 1.0):
        """
        Start periodic data sending.
        
        Args:
            callback: Function that returns data to send
            interval: Send interval in seconds
        """
        self.tcp_client.set_send_callback(callback)
        self.tcp_client.start_periodic_sending(interval)
    
    def stop_periodic_sending(self):
        """Stop periodic data sending."""
        self.tcp_client.stop_periodic_sending()
    
    def disconnect(self):
        """Disconnect from host."""
        self.tcp_client.stop_periodic_sending()
        self.tcp_client.disconnect()
        logger.info("Target TCP communicator disconnected")
    
    def is_connected(self) -> bool:
        """Check if connected to host."""
        return self.tcp_client.is_connected()
