import socket
import threading
import time
import logging
from typing import Optional, Callable
from base_classes import DataReceiverInterface

logger = logging.getLogger("TCPDataClient")


class TCPDataClient(DataReceiverInterface):
    def __init__(self, target_ip: str = "192.168.0.2", target_port: int = 12345,
                 data_callback: Optional[Callable[[str], None]] = None):
        super().__init__(target_ip, target_port, data_callback)
        self.socket: Optional[socket.socket] = None
        self.client_thread: Optional[threading.Thread] = None
        self.connection_timeout = 5
        self.receive_timeout = 1.0
        self.reconnect_delay = 5
        
        logger.info(f"TCP Data Client initialized for {target_ip}:{target_port}")
    
    def set_data_callback(self, callback: Callable[[str], None]):
        self.data_callback = callback
        logger.info("Data callback set")
    
    def start(self):
        if self.running:
            logger.warning("TCP data client is already running")
            return
        
        self.running = True
        self.client_thread = threading.Thread(target=self._client_loop, daemon=True)
        self.client_thread.start()
        logger.info("TCP data client started")
    
    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing socket: {e}")
            self.socket = None
        
        if self.client_thread:
            self.client_thread.join(timeout=2)
        
        logger.info("TCP data client stopped")
    
    def _client_loop(self):
        while self.running:
            try:
                # Connect to target's TCP data server
                logger.info(f"Connecting to target data server at {self.target_ip}:{self.target_port}")
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.connection_timeout)
                self.socket.connect((self.target_ip, self.target_port))
                
                logger.info(f"Connected to target at {self.target_ip}:{self.target_port}")
                
                # Set receive timeout
                self.socket.settimeout(self.receive_timeout)
                
                # Keep connection open and receive data
                while self.running:
                    try:
                        data = self.socket.recv(1024).decode().strip()
                        if data:
                            # Call callback if set
                            if self.data_callback:
                                self.data_callback(data)
                            logger.debug(f"Received data: {data}")
                        else:
                            # Connection closed by server
                            logger.info("Connection closed by target")
                            break
                    except socket.timeout:
                        # Timeout is expected, continue to check connection
                        continue
                    except socket.error as e:
                        logger.debug(f"Socket error: {e}")
                        break
                
                # Close connection
                if self.socket:
                    self.socket.close()
                    self.socket = None
                logger.info("Disconnected from target")
                
            except socket.timeout:
                if self.running:
                    logger.warning(f"Connection timeout - target may not be ready")
                    time.sleep(self.reconnect_delay)
                else:
                    break
            except ConnectionRefusedError:
                if self.running:
                    logger.warning(f"Connection refused - is target listening on port {self.target_port}?")
                    time.sleep(self.reconnect_delay)
                else:
                    break
            except OSError as e:
                if self.running:
                    if e.errno == 10051:  # Windows: Network unreachable
                        logger.error(f"Network unreachable - cannot reach {self.target_ip}:{self.target_port}")
                    elif e.errno == 10061:  # Windows: Connection refused
                        logger.warning(f"Connection refused - is target running on port {self.target_port}?")
                    else:
                        logger.error(f"Connection failed (OSError {e.errno}): {e}")
                    time.sleep(self.reconnect_delay)
                else:
                    break
            except socket.error as e:
                if self.running:
                    logger.error(f"Socket error: {e}")
                    time.sleep(self.reconnect_delay)
                else:
                    break
            except Exception as e:
                if self.running:
                    logger.error(f"Unexpected error ({type(e).__name__}): {e}")
                    time.sleep(self.reconnect_delay)
                else:
                    break
        
        logger.info("TCP data client loop ended")
    
    def is_connected(self) -> bool:
        return self.socket is not None and self.running

