import paramiko
import threading
import time
import sys
import logging

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

class SSHClient:
    def __init__(self, host, port, username, password, command_template):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.command_template = command_template
        self.client = None
        
    def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            logger.info(f"Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def send_ssh_command(self, bitstring):
        if not self.client:
            logger.error("Not connected to SSH server")
            return None
            
        try:
            command = self.command_template.format(bitstring)
            stdin, stdout, stderr = self.client.exec_command(command)
            response = stdout.read().decode().strip()
            logger.info(f"Command sent: {command}, Response: {response}")
            return response
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return None
    
    def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("Disconnected from SSH server")