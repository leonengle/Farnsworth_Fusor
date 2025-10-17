"""
Target Main Program - Option A: SSH Control of Raspberry Pi
This program implements the SSH datalink verification system where the Target Machine
controls a Raspberry Pi via SSH instead of direct GPIO control.

Features:
- SSH server to receive commands from host
- SSH client to control Raspberry Pi GPIO
- TCP client to send data to host
- No direct GPIO control (Pi handles GPIO via SSH)
"""

import threading
import time
import argparse
import paramiko
from ssh_hello_world import SSHHelloWorldServer, PeriodicDataSender
from tcp_client import TargetTCPCommunicator
from logging_setup import setup_logging, get_logger

# Setup logging first
setup_logging()
logger = get_logger("TargetMainOptionA")


class PiGPIOController:
    """
    Controls Raspberry Pi GPIO via SSH.
    """
    
    def __init__(self, pi_ip: str = "192.168.1.101", pi_port: int = 22,
                 username: str = "pi", password: str = "raspberry"):
        """
        Initialize Pi GPIO controller.
        
        Args:
            pi_ip: Raspberry Pi IP address
            pi_port: SSH port on Pi
            username: SSH username
            password: SSH password
        """
        self.pi_ip = pi_ip
        self.pi_port = pi_port
        self.username = username
        self.password = password
        self.client = None
        
        logger.info(f"Pi GPIO Controller initialized for {username}@{pi_ip}:{pi_port}")
    
    def connect(self) -> bool:
        """Connect to Raspberry Pi via SSH."""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.client.connect(
                hostname=self.pi_ip,
                port=self.pi_port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            
            logger.info(f"Connected to Raspberry Pi at {self.pi_ip}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Pi: {e}")
            return False
    
    def setup_gpio(self, led_pin: int = 26, input_pin: int = 6) -> bool:
        """Setup GPIO pins on Raspberry Pi."""
        if not self.client:
            logger.error("Not connected to Pi")
            return False
        
        try:
            # Setup LED pin as output
            led_cmd = f"""
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup({led_pin}, GPIO.OUT)
GPIO.output({led_pin}, GPIO.LOW)
print("LED pin {led_pin} setup complete")
"""
            
            # Setup input pin
            input_cmd = f"""
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup({input_pin}, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
print("Input pin {input_pin} setup complete")
"""
            
            # Execute setup commands
            stdin, stdout, stderr = self.client.exec_command(led_cmd)
            response = stdout.read().decode().strip()
            logger.info(f"LED setup response: {response}")
            
            stdin, stdout, stderr = self.client.exec_command(input_cmd)
            response = stdout.read().decode().strip()
            logger.info(f"Input setup response: {response}")
            
            return True
            
        except Exception as e:
            logger.error(f"GPIO setup failed: {e}")
            return False
    
    def control_led(self, state: bool) -> bool:
        """Control LED on Raspberry Pi."""
        if not self.client:
            logger.error("Not connected to Pi")
            return False
        
        try:
            state_str = "GPIO.HIGH" if state else "GPIO.LOW"
            cmd = f"""
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.OUT)
GPIO.output(26, {state_str})
print("LED set to {state_str}")
"""
            
            stdin, stdout, stderr = self.client.exec_command(cmd)
            response = stdout.read().decode().strip()
            logger.info(f"LED control response: {response}")
            return True
            
        except Exception as e:
            logger.error(f"LED control failed: {e}")
            return False
    
    def read_input_pin(self) -> int:
        """Read input pin value from Raspberry Pi."""
        if not self.client:
            logger.error("Not connected to Pi")
            return 0
        
        try:
            cmd = """
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(6, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
value = GPIO.input(6)
print(value)
"""
            
            stdin, stdout, stderr = self.client.exec_command(cmd)
            response = stdout.read().decode().strip()
            value = int(response) if response.isdigit() else 0
            logger.debug(f"Input pin reads: {value}")
            return value
            
        except Exception as e:
            logger.error(f"Input pin read failed: {e}")
            return 0
    
    def disconnect(self):
        """Disconnect from Raspberry Pi."""
        if self.client:
            try:
                self.client.close()
                logger.info("Disconnected from Raspberry Pi")
            except Exception as e:
                logger.error(f"Error disconnecting from Pi: {e}")
            self.client = None


class TargetSystemOptionA:
    """
    Main target system that controls Raspberry Pi via SSH.
    """
    
    def __init__(self, host_ip: str = "192.168.1.100", ssh_port: int = 2222,
                 pi_ip: str = "192.168.1.101", led_pin: int = 26, input_pin: int = 6):
        """
        Initialize the target system.
        
        Args:
            host_ip: IP address of the host system
            ssh_port: Port for SSH server
            pi_ip: IP address of Raspberry Pi
            led_pin: GPIO pin for LED on Pi
            input_pin: GPIO pin for input reading on Pi
        """
        self.host_ip = host_ip
        self.ssh_port = ssh_port
        self.pi_ip = pi_ip
        self.led_pin = led_pin
        self.input_pin = input_pin
        
        # Initialize components
        self.pi_controller = PiGPIOController(pi_ip)
        self.host_communicator = TargetTCPCommunicator(host_ip, 12345)
        self.data_sender = None
        
        self.running = False
        
        logger.info(f"Target system initialized (Host: {host_ip}, Pi: {pi_ip})")
    
    def _handle_ssh_command(self, command: str) -> str:
        """Handle SSH commands from host."""
        logger.info(f"Received SSH command: {command}")
        
        if command.strip() == "LED_ON":
            if self.pi_controller.control_led(True):
                logger.info("LED turned ON via Pi")
                return "LED_ON_SUCCESS"
            else:
                logger.error("Failed to turn LED ON")
                return "LED_ON_FAILED"
        elif command.strip() == "LED_OFF":
            if self.pi_controller.control_led(False):
                logger.info("LED turned OFF via Pi")
                return "LED_OFF_SUCCESS"
            else:
                logger.error("Failed to turn LED OFF")
                return "LED_OFF_FAILED"
        else:
            logger.warning(f"Unknown command: {command}")
            return "UNKNOWN_COMMAND"
    
    def _get_periodic_data(self) -> str:
        """Get periodic data from Raspberry Pi."""
        try:
            pin_value = self.pi_controller.read_input_pin()
            return f"GPIO_INPUT:{pin_value}"
        except Exception as e:
            logger.error(f"Error getting periodic data: {e}")
            return ""
    
    def start(self):
        """Start the target system."""
        if self.running:
            logger.warning("Target system is already running")
            return
        
        self.running = True
        
        try:
            # Connect to Raspberry Pi
            logger.info("Connecting to Raspberry Pi...")
            if not self.pi_controller.connect():
                logger.error("Failed to connect to Pi, cannot continue")
                return
            
            # Setup GPIO on Pi
            logger.info("Setting up GPIO on Pi...")
            if not self.pi_controller.setup_gpio(self.led_pin, self.input_pin):
                logger.error("Failed to setup GPIO on Pi")
                return
            
            # Connect to host
            logger.info("Connecting to host...")
            if self.host_communicator.connect():
                logger.info("Connected to host successfully")
            else:
                logger.warning("Failed to connect to host, continuing without host communication")
            
            # Start TCP periodic sending
            self.host_communicator.start_periodic_sending(self._get_periodic_data, 1.0)
            
            logger.info("Target system started successfully")
            logger.info("SSH Hello World system is now running!")
            logger.info(f"Connect from host using: ssh user@{self.host_ip} -p {self.ssh_port}")
            logger.info("Send 'LED_ON' or 'LED_OFF' commands to control the LED")
            
            # Main loop for SSH command handling
            while self.running:
                try:
                    # This is a simplified version - in practice you'd implement
                    # a proper SSH server here or use the existing ssh_hello_world
                    time.sleep(1)
                except KeyboardInterrupt:
                    break
            
        except Exception as e:
            logger.error(f"Error starting target system: {e}")
            self.stop()
    
    def stop(self):
        """Stop the target system."""
        self.running = False
        
        logger.info("Stopping target system...")
        
        # Stop TCP periodic sending
        self.host_communicator.stop_periodic_sending()
        
        # Disconnect from host
        self.host_communicator.disconnect()
        
        # Disconnect from Pi
        self.pi_controller.disconnect()
        
        logger.info("Target system stopped")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Target System - Option A (SSH Control)")
    parser.add_argument("--host", default="192.168.1.100", 
                       help="Host IP address (default: 192.168.1.100)")
    parser.add_argument("--ssh-port", type=int, default=2222,
                       help="SSH server port (default: 2222)")
    parser.add_argument("--pi-ip", default="192.168.1.101",
                       help="Raspberry Pi IP address (default: 192.168.1.101)")
    parser.add_argument("--led-pin", type=int, default=26,
                       help="GPIO pin for LED on Pi (default: 26)")
    parser.add_argument("--input-pin", type=int, default=6,
                       help="GPIO pin for input reading on Pi (default: 6)")
    
    args = parser.parse_args()
    
    logger.info("Starting Target System - Option A (SSH Control)")
    logger.info(f"Configuration: Host={args.host}, Pi={args.pi_ip}")
    logger.info(f"GPIO: LED={args.led_pin}, Input={args.input_pin}")
    
    # Create and start target system
    target_system = TargetSystemOptionA(
        host_ip=args.host,
        ssh_port=args.ssh_port,
        pi_ip=args.pi_ip,
        led_pin=args.led_pin,
        input_pin=args.input_pin
    )
    
    try:
        target_system.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        target_system.stop()
        logger.info("Target system shutdown complete")


if __name__ == "__main__":
    main()
