"""
Target Main Program - SSH/TCP Hybrid Implementation
This program implements the SSH/TCP hybrid communication system as described in the project diagram.

Features:
- SSH server to receive commands from host (port 2222)
- TCP client to send sensor data to host (port 8888)
- GPIO LED control for visual feedback when receiving commands
- GPIO input reading (jumper wire to ground/5V)
- Periodic TCP data sending every 1 second
- Integration with existing motor control and ADC systems
"""

import threading
import time
import argparse
import os
from ssh_hello_world import SSHHelloWorldServer, PeriodicDataSender
from logging_setup import setup_logging, get_logger

# Setup logging first
setup_logging()
logger = get_logger("TargetMain")


class TargetSystem:
    """
    Main target system that integrates all components.
    """
    
    def __init__(self, host_ip: str = None, ssh_port: int = 2222, tcp_port: int = 8888,
                 led_pin: int = 26, input_pin: int = 6, use_adc: bool = False):
        """
        Initialize the target system.
        
        Args:
            host_ip: IP address of the host system (defaults to environment variable or 192.168.1.100)
            ssh_port: Port for SSH server
            tcp_port: Port for TCP data transmission
            led_pin: GPIO pin for LED output
            input_pin: GPIO pin for input reading
            use_adc: Enable ADC functionality
        """
        # Get host IP from environment variable or use default
        if host_ip is None:
            host_ip = os.getenv('FUSOR_HOST_IP', '192.168.1.100')
        
        self.host_ip = host_ip
        self.ssh_port = ssh_port
        self.tcp_port = tcp_port
        self.led_pin = led_pin
        self.input_pin = input_pin
        self.use_adc = use_adc
        
        # Initialize components
        self.ssh_server = SSHHelloWorldServer(
            host="0.0.0.0", 
            port=ssh_port,
            led_pin=led_pin,
            input_pin=input_pin,
            use_adc=use_adc
        )
        
        self.data_sender = None
        
        self.running = False
        
        logger.info(f"Target system initialized (Host: {host_ip}, SSH Port: {ssh_port})")
    
    def start(self):
        """Start the target system."""
        if self.running:
            logger.warning("Target system is already running")
            return
        
        self.running = True
        
        try:
            # Create and start periodic data sender with TCP
            self.data_sender = PeriodicDataSender(
                self.ssh_server, 
                host=self.host_ip, 
                port=self.tcp_port,  # Use configurable TCP port
                use_adc=self.use_adc
            )
            self.data_sender.start()
            
            logger.info("Target system started successfully")
            logger.info("SSH Hello World system is now running!")
            logger.info(f"Connect from host using: ssh pi@{self.host_ip} -p {self.ssh_port}")
            logger.info("Send 'LED_ON' or 'LED_OFF' commands to control the LED")
            logger.info(f"Sending sensor data to host via TCP on port 8888")
            
            # Start SSH server (this will block)
            self.ssh_server.start_server()
            
        except Exception as e:
            logger.error(f"Error starting target system: {e}")
            self.stop()
    
    def stop(self):
        """Stop the target system."""
        self.running = False
        
        logger.info("Stopping target system...")
        
        # Stop data sender
        if self.data_sender:
            self.data_sender.stop()
        
        # Stop SSH server
        self.ssh_server.stop_server()
        
        # Cleanup
        self.ssh_server.cleanup()
        
        logger.info("Target system stopped")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Target System - SSH/TCP Hybrid")
    parser.add_argument("--host", default=None, 
                       help="Host IP address (default: from FUSOR_HOST_IP env var or 192.168.1.100)")
    parser.add_argument("--ssh-port", type=int, default=2222,
                       help="SSH server port (default: 2222)")
    parser.add_argument("--tcp-port", type=int, default=8888,
                       help="TCP data port (default: 8888)")
    parser.add_argument("--led-pin", type=int, default=26,
                       help="GPIO pin for LED (default: 26)")
    parser.add_argument("--input-pin", type=int, default=6,
                       help="GPIO pin for input reading (default: 6)")
    parser.add_argument("--use-adc", action="store_true",
                       help="Enable ADC functionality")
    
    args = parser.parse_args()
    
    # Get host IP from environment variable or command line
    host_ip = args.host or os.getenv('FUSOR_HOST_IP', '192.168.1.100')
    
    logger.info("Starting Target System - SSH/TCP Hybrid")
    logger.info(f"Configuration: Host={host_ip}, SSH Port={args.ssh_port}, TCP Port={args.tcp_port}")
    logger.info(f"GPIO: LED={args.led_pin}, Input={args.input_pin}")
    logger.info(f"ADC: {'Enabled' if args.use_adc else 'Disabled'}")
    
    # Create and start target system
    target_system = TargetSystem(
        host_ip=host_ip,
        ssh_port=args.ssh_port,
        tcp_port=args.tcp_port,
        led_pin=args.led_pin,
        input_pin=args.input_pin,
        use_adc=args.use_adc
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
