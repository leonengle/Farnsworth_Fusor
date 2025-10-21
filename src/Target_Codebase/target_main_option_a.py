"""
Target Codebase for Option A: Target Machine controls Pi via SSH
This version replaces direct GPIO calls with SSH commands sent to the Raspberry Pi.
"""

import threading
import time
import argparse
from ssh_client import SSHClient
from tcp_client import TargetTCPCommunicator
from logging_setup import setup_logging, get_logger

class TargetSystemOptionA:
    def __init__(self, host_ip: str = "172.20.10.5", ssh_port: int = 2222,
                 pi_ip: str = "192.168.1.102", pi_ssh_port: int = 22,
                 pi_username: str = "pi", pi_password: str = "raspberry",
                 led_pin: int = 26, input_pin: int = 6, use_adc: bool = False):
        """
        Initialize Target System Option A.
        
        Args:
            host_ip: IP address of the host machine
            ssh_port: SSH port for receiving commands from host
            pi_ip: IP address of the Raspberry Pi
            pi_ssh_port: SSH port on the Raspberry Pi
            pi_username: Username for Pi SSH connection
            pi_password: Password for Pi SSH connection
            led_pin: GPIO pin for LED control on Pi
            input_pin: GPIO pin for input reading on Pi
            use_adc: Whether to use ADC for analog readings
        """
        self.host_ip = host_ip
        self.ssh_port = ssh_port
        self.pi_ip = pi_ip
        self.pi_ssh_port = pi_ssh_port
        self.pi_username = pi_username
        self.pi_password = pi_password
        self.led_pin = led_pin
        self.input_pin = input_pin
        self.use_adc = use_adc
        
        # Initialize components
        self.pi_ssh_client = SSHClient(pi_ip, pi_ssh_port, pi_username, pi_password)
        self.host_communicator = TargetTCPCommunicator(host_ip, 12345)
        
        # System state
        self.running = False
        self.ssh_server_thread = None
        
        # Setup logging
        setup_logging()
        self.logger = get_logger("TargetSystemOptionA")
        
    def start(self):
        """Start the target system."""
        self.logger.info("Starting Target System Option A...")
        
        # Connect to Raspberry Pi
        if not self.pi_ssh_client.connect():
            self.logger.error("Failed to connect to Raspberry Pi")
            return False
            
        self.logger.info(f"Connected to Raspberry Pi at {self.pi_ip}")
        
        # Setup GPIO on Pi
        self._setup_pi_gpio()
        
        # Start SSH server for host commands
        self.running = True
        self.ssh_server_thread = threading.Thread(target=self._ssh_server_loop, daemon=True)
        self.ssh_server_thread.start()
        
        # Start TCP communication with host
        self.host_communicator.start_periodic_sending(self._get_periodic_data, 1.0)
        
        self.logger.info("Target System Option A started successfully")
        self.logger.info(f"Connect from host using: ssh mdali@{self.host_ip} -p {self.ssh_port}")
        
        return True
        
    def stop(self):
        """Stop the target system."""
        self.logger.info("Stopping Target System Option A...")
        
        self.running = False
        
        # Stop TCP communication
        self.host_communicator.stop_periodic_sending()
        
        # Disconnect from Pi
        self.pi_ssh_client.disconnect()
        
        self.logger.info("Target System Option A stopped")
        
    def _setup_pi_gpio(self):
        """Setup GPIO pins on Raspberry Pi via SSH."""
        try:
            # Setup LED pin as output
            self.pi_ssh_client.send_command(f"gpio -g mode {self.led_pin} out")
            self.pi_ssh_client.send_command(f"gpio -g write {self.led_pin} 0")
            
            # Setup input pin
            self.pi_ssh_client.send_command(f"gpio -g mode {self.input_pin} in")
            
            self.logger.info(f"GPIO setup completed on Pi: LED={self.led_pin}, INPUT={self.input_pin}")
            
        except Exception as e:
            self.logger.error(f"Error setting up Pi GPIO: {e}")
            
    def _ssh_server_loop(self):
        """SSH server loop for receiving commands from host."""
        # This is a simplified implementation
        # In a real implementation, you'd use paramiko's SSH server
        self.logger.info("SSH server loop started (simplified)")
        
        while self.running:
            time.sleep(1)
            
    def _get_periodic_data(self) -> str:
        """Get periodic data from Raspberry Pi."""
        try:
            if self.use_adc:
                # Read ADC value from Pi
                adc_value = self.pi_ssh_client.send_command("python3 -c 'from adc import MCP3008ADC; adc = MCP3008ADC(); print(adc.read_channel(0))'")
                return f"ADC_DATA:{adc_value}"
            else:
                # Read GPIO input from Pi
                pin_value = self.pi_ssh_client.send_command(f"gpio -g read {self.input_pin}")
                return f"GPIO_INPUT:{pin_value}"
                
        except Exception as e:
            self.logger.error(f"Error getting periodic data: {e}")
            return ""
            
    def handle_ssh_command(self, command: str) -> str:
        """Handle SSH command from host."""
        try:
            if command == "LED_ON":
                self.pi_ssh_client.send_command(f"gpio -g write {self.led_pin} 1")
                return "LED turned ON"
                
            elif command == "LED_OFF":
                self.pi_ssh_client.send_command(f"gpio -g write {self.led_pin} 0")
                return "LED turned OFF"
                
            elif command.startswith("MOVE_VAR:"):
                steps = command.split(":")[1]
                self.pi_ssh_client.send_command(f"python3 moveVARIAC.py move {steps}")
                return f"VARIAC moved {steps} steps"
                
            else:
                return f"Unknown command: {command}"
                
        except Exception as e:
            self.logger.error(f"Error handling SSH command: {e}")
            return f"Error: {e}"

def main():
    parser = argparse.ArgumentParser(description="Target System Option A")
    parser.add_argument("--host", default="172.20.10.5", help="Host IP address")
    parser.add_argument("--ssh-port", type=int, default=2222, help="SSH port for host commands")
    parser.add_argument("--pi-ip", default="192.168.1.102", help="Raspberry Pi IP address")
    parser.add_argument("--pi-ssh-port", type=int, default=22, help="Pi SSH port")
    parser.add_argument("--pi-username", default="pi", help="Pi username")
    parser.add_argument("--pi-password", default="raspberry", help="Pi password")
    parser.add_argument("--led-pin", type=int, default=26, help="LED GPIO pin")
    parser.add_argument("--input-pin", type=int, default=6, help="Input GPIO pin")
    parser.add_argument("--use-adc", action="store_true", help="Use ADC for analog readings")
    
    args = parser.parse_args()
    
    # Create and start target system
    target_system = TargetSystemOptionA(
        host_ip=args.host,
        ssh_port=args.ssh_port,
        pi_ip=args.pi_ip,
        pi_ssh_port=args.pi_ssh_port,
        pi_username=args.pi_username,
        pi_password=args.pi_password,
        led_pin=args.led_pin,
        input_pin=args.input_pin,
        use_adc=args.use_adc
    )
    
    try:
        if target_system.start():
            print("Target System Option A running. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        else:
            print("Failed to start Target System Option A")
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        target_system.stop()

if __name__ == "__main__":
    main()