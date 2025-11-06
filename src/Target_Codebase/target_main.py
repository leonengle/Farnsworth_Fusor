import threading
import time
import argparse
import signal
import sys
from tcp_command_server import TCPCommandServer, PeriodicDataSender
from tcp_data_server import TCPDataServer
from udp_status_server import UDPStatusSender, UDPStatusReceiver
from logging_setup import setup_logging, get_logger

# Setup logging first
setup_logging()
logger = get_logger("TargetMain")


class TargetSystem:
    def __init__(self, host_ip: str = "192.168.0.1", tcp_command_port: int = 2222,
                 led_pin: int = 26, input_pin: int = 6, use_adc: bool = False):
        self.host_ip = host_ip
        self.tcp_command_port = tcp_command_port
        self.led_pin = led_pin
        self.input_pin = input_pin
        self.use_adc = use_adc
        
        # Initialize components
        self.tcp_command_server = TCPCommandServer(
            host="0.0.0.0", 
            port=tcp_command_port,
            led_pin=led_pin,
            input_pin=input_pin,
            use_adc=use_adc
        )
        
        # TCP data server - listens on port 12345 for host to connect
        self.tcp_data_server = TCPDataServer(host="0.0.0.0", port=12345)
        self.data_sender = None
        
        # UDP status communication
        self.udp_status_sender = UDPStatusSender(host_ip, 8888)
        self.udp_status_receiver = UDPStatusReceiver(8889)
        
        self.running = False
        
        logger.info(f"Target system initialized (Host: {host_ip}, TCP Command Port: {tcp_command_port})")
    
    def _host_callback(self, data: str):
        try:
            self.udp_status_sender.send_status(f"STATUS:{data}")
        except Exception as e:
            logger.debug(f"UDP status send failed: {e}")
    
    def _get_periodic_data(self) -> str:
        try:
            if self.use_adc and self.tcp_command_server.adc:
                # Send ADC data
                adc_value = self.tcp_command_server.read_adc_channel(0)  # Use channel 0
                return f"ADC_DATA:{adc_value}"
            else:
                # Send GPIO data
                pin_value = self.tcp_command_server.read_input_pin()
                return f"GPIO_INPUT:{pin_value}"
        except Exception as e:
            logger.error(f"Error getting periodic data: {e}")
            return ""
    
    def start(self):
                if self.running:
            logger.warning("Target system is already running")
            return
        
        self.running = True
        
        try:
            # Set up host callback for TCP command server
            self.tcp_command_server.set_host_callback(self._host_callback)
            
            # Set up data callback for TCP data server
            self.tcp_data_server.set_send_callback(self._get_periodic_data)
            
            # Create and start periodic data sender (for legacy support)
            self.data_sender = PeriodicDataSender(self.tcp_command_server, self._host_callback, self.use_adc)
            self.data_sender.start()
            
            # Start TCP data server (listens on port 12345, host connects)
            self.tcp_data_server.start_server()
            
            # Start UDP status communication
            self.udp_status_sender.start()
            self.udp_status_receiver.start()
            
            logger.info("Target system started successfully")
            logger.info("TCP/UDP system is now running!")
            logger.info(f"TCP Command server listening on port {self.tcp_command_port}")
            logger.info(f"TCP Data server listening on port 12345")
            logger.info(f"Send 'LED_ON' or 'LED_OFF' commands via TCP to control the LED")
            
            # Start TCP command server (this will block)
            self.tcp_command_server.start_server()
            
        except Exception as e:
            logger.error(f"Error starting target system: {e}")
            self.stop()
    
    def stop(self):
                self.running = False
        
        logger.info("Stopping target system...")
        
        # Stop data sender
        if self.data_sender:
            self.data_sender.stop()
        
        # Stop TCP data server
        self.tcp_data_server.stop_server()
        
        # Stop TCP command server
        self.tcp_command_server.stop_server()
        
        # Stop UDP status communication
        self.udp_status_sender.stop()
        self.udp_status_receiver.stop()
        
        # Cleanup
        self.tcp_command_server.cleanup()
        
        logger.info("Target system stopped")


def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
    
    # Turn off LED immediately using GPIO handler
    try:
        from gpio_handler import GPIOHandler
        gpio = GPIOHandler(led_pin=26, input_pin=6)
        gpio.led_off()
        gpio.cleanup()
        logger.info("LED turned OFF due to interrupt")
    except Exception as e:
        logger.error(f"Could not turn off LED: {e}")
    
    sys.exit(0)


def main():
        # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(description="Target System - TCP/UDP")
    parser.add_argument("--host", default="192.168.0.1", 
                       help="Host IP address (default: 192.168.0.1)")
    parser.add_argument("--tcp-command-port", type=int, default=2222,
                       help="TCP command server port (default: 2222)")
    parser.add_argument("--led-pin", type=int, default=26,
                       help="GPIO pin for LED (default: 26)")
    parser.add_argument("--input-pin", type=int, default=6,
                       help="GPIO pin for input reading (default: 6)")
    parser.add_argument("--use-adc", action="store_true",
                       help="Enable ADC functionality")
    
    args = parser.parse_args()
    
    logger.info("Starting Target System - TCP/UDP")
    logger.info(f"Configuration: Host={args.host}, TCP Command Port={args.tcp_command_port}")
    logger.info(f"GPIO: LED={args.led_pin}, Input={args.input_pin}")
    logger.info(f"ADC: {'Enabled' if args.use_adc else 'Disabled'}")
    
    # Create and start target system
    target_system = TargetSystem(
        host_ip=args.host,
        tcp_command_port=args.tcp_command_port,
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