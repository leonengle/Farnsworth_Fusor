"""
Target Main Program - SSH Hello World Implementation
This program implements the SSH datalink verification system as described in Figure 7.

Features:
- SSH server to receive commands from host
- GPIO LED control for visual feedback when receiving commands
- GPIO input reading (jumper wire to ground/5V)
- Periodic SSH command sending every 1 second
- Integration with existing motor control and ADC systems
"""

import threading
import time
import argparse
from ssh_hello_world import SSHHelloWorldServer, PeriodicDataSender
from tcp_client import TargetTCPCommunicator
from logging_setup import setup_logging, get_logger

# Setup logging first
setup_logging()
logger = get_logger("TargetMain")


class TargetSystem:
    """
    Main target system that integrates all components.
    """
    
    def __init__(self, host_ip: str = "192.168.1.69", ssh_port: int = 2222,
                 led_pin: int = 26, input_pin: int = 6, use_adc: bool = False):
        """
        Initialize the target system.
        
        Args:
            host_ip: IP address of the host system
            ssh_port: Port for SSH server
            led_pin: GPIO pin for LED output
            input_pin: GPIO pin for input reading
            use_adc: Enable ADC functionality
        """
        self.host_ip = host_ip
        self.ssh_port = ssh_port
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
        
        self.host_communicator = TargetTCPCommunicator(host_ip, 12345)
        self.data_sender = None
        
        self.running = False
        
        logger.info(f"Target system initialized (Host: {host_ip}, SSH Port: {ssh_port})")
    
    def _host_callback(self, data: str):
        """
        Callback function to send data to host.
        
        Args:
            data: Data string to send to host
        """
        if self.host_communicator.is_connected():
            # Parse data and send appropriately
            if data.startswith("GPIO_INPUT:"):
                pin_value = int(data.split(":")[1])
                self.host_communicator.send_gpio_data(pin_value)
            elif data.startswith("ADC_DATA:"):
                # Format: ADC_DATA:512,256,128,64,32,16,8,4
                adc_values_str = data.split(":")[1]
                adc_values = [int(x) for x in adc_values_str.split(",")]
                self.host_communicator.send_adc_all_data(adc_values)
            elif data.startswith("ADC_CH"):
                # Format: ADC_CH0:512
                parts = data.split(":")
                channel = int(parts[0].split("CH")[1])
                value = int(parts[1])
                self.host_communicator.send_adc_data(channel, value)
            else:
                logger.warning(f"Unknown data format: {data}")
        else:
            logger.warning("Host communicator not connected, cannot send data")
    
    def _get_periodic_data(self) -> str:
        """
        Get periodic data to send to host.
        
        Returns:
            Data string to send
        """
        try:
            if self.use_adc and self.ssh_server.adc:
                # Send ADC data
                adc_value = self.ssh_server.read_adc_channel(0)  # Use channel 0
                return f"ADC_DATA:{adc_value}"
            else:
                # Send GPIO data
                pin_value = self.ssh_server.read_input_pin()
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
            # Connect to host
            logger.info("Connecting to host...")
            if self.host_communicator.connect():
                logger.info("Connected to host successfully")
            else:
                logger.warning("Failed to connect to host, continuing without host communication")
            
            # Set up host callback for SSH server
            self.ssh_server.set_host_callback(self._host_callback)
            
            # Create and start periodic data sender
            self.data_sender = PeriodicDataSender(self.ssh_server, self._host_callback, self.use_adc)
            self.data_sender.start()
            
            # Start TCP periodic sending
            self.host_communicator.start_periodic_sending(self._get_periodic_data, 1.0)
            
            logger.info("Target system started successfully")
            logger.info("SSH Hello World system is now running!")
            logger.info(f"Connect from host using: ssh mdali@{self.host_ip} -p {self.ssh_port}")
            logger.info("Send 'LED_ON' or 'LED_OFF' commands to control the LED")
            
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
        
        # Stop TCP periodic sending
        self.host_communicator.stop_periodic_sending()
        
        # Stop SSH server
        self.ssh_server.stop_server()
        
        # Disconnect from host
        self.host_communicator.disconnect()
        
        # Cleanup
        self.ssh_server.cleanup()
        
        logger.info("Target system stopped")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Target System - SSH Hello World")
    parser.add_argument("--host", default="192.168.1.69", 
                       help="Host IP address (default: 192.168.1.69)")
    parser.add_argument("--ssh-port", type=int, default=2222,
                       help="SSH server port (default: 2222)")
    parser.add_argument("--led-pin", type=int, default=26,
                       help="GPIO pin for LED (default: 26)")
    parser.add_argument("--input-pin", type=int, default=6,
                       help="GPIO pin for input reading (default: 6)")
    parser.add_argument("--use-adc", action="store_true",
                       help="Enable ADC functionality")
    
    args = parser.parse_args()
    
    logger.info("Starting Target System - SSH Hello World")
    logger.info(f"Configuration: Host={args.host}, SSH Port={args.ssh_port}")
    logger.info(f"GPIO: LED={args.led_pin}, Input={args.input_pin}")
    logger.info(f"ADC: {'Enabled' if args.use_adc else 'Disabled'}")
    
    # Create and start target system
    target_system = TargetSystem(
        host_ip=args.host,
        ssh_port=args.ssh_port,
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