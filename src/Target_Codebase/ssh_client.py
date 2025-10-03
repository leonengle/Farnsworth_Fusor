import paramiko
import socket
import time
from logging_setup import setup_logging, get_logger
from typing import Optional

# setup logging for this module
setup_logging()
logger = get_logger("SSHClient")


class SSHClient:
    # ssh client for sending commands to the host system
    def __init__(self, host: str = "192.168.1.100", port: int = 22, 
                 username: str = "pi", password: str = "raspberry"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = None
        self.connected = False
        
        logger.info(f"SSH Client initialized for {username}@{host}:{port}")
    
    def connect(self) -> bool:
        # establish ssh connection to the host
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # connect to the host system
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            
            self.connected = True
            logger.info(f"SSH connection established to {self.host}")
            return True
            
        except Exception as e:
            logger.error(f"SSH connection failed: {e}")
            self.connected = False
            return False
    
    def send_command(self, command: str) -> Optional[str]:
        # send a command to the host and get the response
        if not self.connected or not self.client:
            logger.error("SSH client not connected")
            return None
        
        try:
            # execute the command on the host
            stdin, stdout, stderr = self.client.exec_command(command)
            
            # read the response from the host
            response = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            
            if error:
                logger.warning(f"SSH command error: {error}")
            
            logger.debug(f"SSH command '{command}' -> '{response}'")
            return response
            
        except Exception as e:
            logger.error(f"SSH command failed: {e}")
            return None
    
    def disconnect(self):
        # close the ssh connection
        if self.client:
            try:
                self.client.close()
                logger.info("SSH connection closed")
            except Exception as e:
                logger.error(f"Error closing SSH connection: {e}")
        
        self.connected = False
        self.client = None
    
    def is_connected(self) -> bool:
        # check if we're connected to the host
        return self.connected and self.client is not None


class HostCommunicator:
    # high-level interface for sending data to the host system
    def __init__(self, host: str = "192.168.1.100", port: int = 22,
                 username: str = "pi", password: str = "raspberry"):
        self.ssh_client = SSHClient(host, port, username, password)
        self.max_retries = 3
        self.retry_delay = 1.0
        
        logger.info("Host communicator initialized")
    
    def connect(self) -> bool:
        # connect to the host system
        return self.ssh_client.connect()
    
    def send_gpio_data(self, pin_value: int) -> bool:
        # send gpio pin data to the host
        command = f"echo 'GPIO_INPUT:{pin_value}'"
        
        for attempt in range(self.max_retries):
            try:
                response = self.ssh_client.send_command(command)
                if response is not None:
                    logger.debug(f"GPIO data sent successfully: {pin_value}")
                    return True
                else:
                    logger.warning(f"Failed to send GPIO data (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.error(f"Error sending GPIO data: {e}")
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        logger.error("Failed to send GPIO data after all retries")
        return False
    
    def send_adc_data(self, channel: int, value: int) -> bool:
        # send adc data to the host
        command = f"echo 'ADC_CH{channel}:{value}'"
        
        for attempt in range(self.max_retries):
            try:
                response = self.ssh_client.send_command(command)
                if response is not None:
                    logger.debug(f"ADC data sent successfully: CH{channel}={value}")
                    return True
                else:
                    logger.warning(f"Failed to send ADC data (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.error(f"Error sending ADC data: {e}")
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        logger.error("Failed to send ADC data after all retries")
        return False
    
    def send_adc_all_data(self, adc_values: list) -> bool:
        # send all adc channel data to the host
        command = f"echo 'ADC_DATA:{','.join(map(str, adc_values))}'"
        
        for attempt in range(self.max_retries):
            try:
                response = self.ssh_client.send_command(command)
                if response is not None:
                    logger.debug(f"ADC all data sent successfully: {adc_values}")
                    return True
                else:
                    logger.warning(f"Failed to send ADC all data (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.error(f"Error sending ADC all data: {e}")
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        logger.error("Failed to send ADC all data after all retries")
        return False
    
    def disconnect(self):
        # disconnect from the host
        self.ssh_client.disconnect()
        logger.info("Host communicator disconnected")
    
    def is_connected(self) -> bool:
        # check if we're connected to the host
        return self.ssh_client.is_connected()


