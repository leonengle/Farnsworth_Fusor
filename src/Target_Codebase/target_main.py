import threading
import time
import argparse
import signal
import sys
from tcp_command_server import TCPCommandServer, PeriodicDataSender
from tcp_data_server import TCPDataServer
from udp_status_server import UDPStatusSender, UDPStatusReceiver
from arduino_interface import ArduinoInterface
from logging_setup import setup_logging, get_logger

# Setup logging first
setup_logging()
logger = get_logger("TargetMain")


class TargetSystem:
    def __init__(
        self,
        host_ip: str = "192.168.0.1",
        tcp_command_port: int = 2222,
        led_pin: int = 26,
        input_pin: int = 6,
        use_adc: bool = True,
        arduino_port: str = None,
        use_arduino: bool = True,
    ):
        self.host_ip = host_ip
        self.tcp_command_port = tcp_command_port
        self.led_pin = led_pin
        self.input_pin = input_pin
        self.use_adc = use_adc
        self.use_arduino = use_arduino

        # Initialize Arduino USB interface (early in startup sequence)
        self.arduino_interface = None
        if use_arduino:
            try:
                self.arduino_interface = ArduinoInterface(
                    port=arduino_port,
                    baudrate=9600,
                    auto_detect=(arduino_port is None),
                )
                # Set callback for Arduino data
                self.arduino_interface.set_data_callback(self._arduino_data_callback)
                logger.info("Arduino interface initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Arduino interface: {e}")
                logger.info("Continuing without Arduino interface")
                self.arduino_interface = None

        # Initialize components
        self.tcp_command_server = TCPCommandServer(
            host="0.0.0.0",
            port=tcp_command_port,
            led_pin=led_pin,
            input_pin=input_pin,
            use_adc=use_adc,
            arduino_interface=self.arduino_interface,
        )

        # TCP data server - listens on port 12345 for host to connect
        self.tcp_data_server = TCPDataServer(host="0.0.0.0", port=12345)
        self.data_sender = None

        # UDP status communication
        self.udp_status_sender = UDPStatusSender(host_ip, 8888)
        self.udp_status_receiver = UDPStatusReceiver(8889)

        self.running = False
        
        # ADC filtering - moving average buffer
        self.adc_filter_size = 5  # Number of samples to average
        self.adc_readings_buffer = []  # Buffer for moving average
        self.adc_last_reported_value = None  # Last reported value for change detection
        self.adc_noise_threshold = 2  # Minimum change to report (filter out noise)

        logger.info(
            f"Target system initialized (Host: {host_ip}, TCP Command Port: {tcp_command_port}, "
            f"Arduino: {'Enabled' if self.arduino_interface else 'Disabled'})"
        )

    def _host_callback(self, data: str):
        try:
            self.udp_status_sender.send_status(f"STATUS:{data}")
        except Exception as e:
            logger.debug(f"UDP status send failed: {e}")

    def _arduino_data_callback(self, data: str):
        """Callback for data received from Arduino."""
        try:
            logger.debug(f"Arduino data received: {data}")
            # Forward Arduino data to host via UDP status
            self.udp_status_sender.send_status(f"ARDUINO_DATA:{data}")
        except Exception as e:
            logger.debug(f"Error processing Arduino data: {e}")

    def _get_periodic_data(self) -> str:
        """Generate periodic data packet to send to host."""
        try:
            import time
            timestamp = time.strftime("%H:%M:%S")
            
            # Collect data based on available sensors
            data_parts = [f"TIME:{timestamp}"]
            
            # Always try to read ADC (default behavior)
            if self.tcp_command_server.adc:
                if self.tcp_command_server.adc.is_initialized():
                    try:
                        # Read multiple samples and average to reduce noise
                        raw_readings = []
                        for _ in range(3):  # Take 3 quick samples
                            raw_value = self.tcp_command_server.read_adc_channel(0)
                            raw_readings.append(raw_value)
                        
                        # Calculate average
                        adc_value = int(sum(raw_readings) / len(raw_readings))
                        
                        # Add to moving average buffer
                        self.adc_readings_buffer.append(adc_value)
                        if len(self.adc_readings_buffer) > self.adc_filter_size:
                            self.adc_readings_buffer.pop(0)  # Remove oldest
                        
                        # Calculate filtered value (moving average)
                        filtered_value = int(sum(self.adc_readings_buffer) / len(self.adc_readings_buffer))
                        
                        # Only report if change is significant (above noise threshold)
                        if (self.adc_last_reported_value is None or 
                            abs(filtered_value - self.adc_last_reported_value) >= self.adc_noise_threshold):
                            self.adc_last_reported_value = filtered_value
                            data_parts.append(f"ADC_CH0:{filtered_value}")
                        else:
                            # Use last reported value to avoid noise
                            data_parts.append(f"ADC_CH0:{self.adc_last_reported_value}")
                    except Exception as e:
                        logger.warning(f"Error reading ADC channel 0: {e}")
                        data_parts.append("ADC_CH0:ERROR")
                else:
                    data_parts.append("ADC:NOT_INITIALIZED")
            else:
                data_parts.append("ADC:NOT_AVAILABLE")
            
            # Add Arduino status if available
            if self.arduino_interface and self.arduino_interface.is_connected():
                data_parts.append("ARDUINO:CONNECTED")
            else:
                data_parts.append("ARDUINO:DISCONNECTED")
            
            return "|".join(data_parts)
        except Exception as e:
            logger.error(f"Error getting periodic data: {e}")
            return ""

    def start(self):
        if self.running:
            logger.warning("Target system is already running")
            return

        self.running = True

        try:
            # Connect to Arduino if interface is available
            if self.arduino_interface:
                if self.arduino_interface.connect():
                    logger.info("Arduino USB connection established")
                else:
                    logger.warning("Failed to connect to Arduino, continuing without it")

            # Set up host callback for TCP command server
            self.tcp_command_server.set_host_callback(self._host_callback)

            # Set up data callback for TCP data server
            self.tcp_data_server.set_send_callback(self._get_periodic_data)

            # Create and start periodic data sender (for legacy support)
            self.data_sender = PeriodicDataSender(
                self.tcp_command_server, self._host_callback, self.use_adc
            )
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
            if self.arduino_interface and self.arduino_interface.is_connected():
                logger.info("Arduino USB interface active")
            logger.info(
                f"Send 'LED_ON' or 'LED_OFF' commands via TCP to control the LED"
            )

            # Start TCP command server (this will block)
            self.tcp_command_server.start_server()

        except Exception as e:
            logger.error(f"Error starting target system: {e}")
            self.stop()

    def stop(self):
        self.running = False

        logger.info("Stopping target system...")

        # Disconnect Arduino first
        if self.arduino_interface:
            try:
                self.arduino_interface.cleanup()
                logger.info("Arduino interface disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting Arduino: {e}")

        # Turn off LED first, before stopping services
        try:
            if self.tcp_command_server and self.tcp_command_server.gpio_handler:
                success, msg = self.tcp_command_server.gpio_handler.led_off()
                if success:
                    logger.info("LED turned OFF during shutdown")
                else:
                    logger.warning(f"LED off during shutdown: {msg}")
        except Exception as e:
            logger.error(f"Error turning off LED during stop: {e}")

        # Stop data sender
        if self.data_sender:
            try:
                self.data_sender.stop()
            except Exception as e:
                logger.error(f"Error stopping data sender: {e}")

        # Stop TCP data server
        try:
            self.tcp_data_server.stop_server()
        except Exception as e:
            logger.error(f"Error stopping TCP data server: {e}")

        # Stop TCP command server
        try:
            self.tcp_command_server.stop_server()
        except Exception as e:
            logger.error(f"Error stopping TCP command server: {e}")

        # Stop UDP status communication
        try:
            self.udp_status_sender.stop()
            self.udp_status_receiver.stop()
        except Exception as e:
            logger.error(f"Error stopping UDP communication: {e}")

        # Cleanup - this will also turn off LED again as a safety measure
        try:
            self.tcp_command_server.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Final attempt to turn off LED
            try:
                if self.tcp_command_server and self.tcp_command_server.gpio_handler:
                    self.tcp_command_server.gpio_handler.led_off()
            except:
                pass

        logger.info("Target system stopped")


# Global target_system instance for signal handler access
_target_system_instance = None


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down gracefully...")

    # Turn off LED immediately - try multiple methods
    try:
        # Try to use existing GPIO handler from target_system if available
        if _target_system_instance:
            try:
                if (
                    _target_system_instance.tcp_command_server
                    and _target_system_instance.tcp_command_server.gpio_handler
                ):
                    success, msg = _target_system_instance.tcp_command_server.gpio_handler.led_off()
                    if success:
                        logger.info("LED turned OFF via existing GPIO handler")
                    else:
                        logger.warning(f"LED off via existing handler: {msg}")
            except Exception as e:
                logger.debug(f"Could not use existing GPIO handler: {e}")
    except Exception as e:
        logger.debug(f"Error accessing target_system: {e}")

    # Fallback: create new GPIO handler
    try:
        from gpio_handler import GPIOHandler

        gpio = GPIOHandler(led_pin=26, input_pin=6)
        success, msg = gpio.led_off()
        if success:
            logger.info("LED turned OFF via new GPIO handler")
        else:
            logger.warning(f"LED off via new handler: {msg}")
        gpio.cleanup()
    except Exception as e:
        logger.error(f"Could not turn off LED: {e}")

    # Try to stop target system gracefully
    if _target_system_instance:
        try:
            _target_system_instance.stop()
        except Exception as e:
            logger.error(f"Error stopping target system: {e}")

    sys.exit(0)


def main():
    global _target_system_instance

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description="Target System - TCP/UDP")
    parser.add_argument(
        "--host", default="192.168.0.1", help="Host IP address (default: 192.168.0.1)"
    )
    parser.add_argument(
        "--tcp-command-port",
        type=int,
        default=2222,
        help="TCP command server port (default: 2222)",
    )
    parser.add_argument(
        "--led-pin", type=int, default=26, help="GPIO pin for LED (default: 26)"
    )
    parser.add_argument(
        "--input-pin",
        type=int,
        default=6,
        help="GPIO pin for input reading (default: 6)",
    )
    parser.add_argument(
        "--no-adc", action="store_true", help="Disable ADC functionality (ADC enabled by default)"
    )
    parser.add_argument(
        "--arduino-port",
        type=str,
        default=None,
        help="Arduino USB serial port (e.g., /dev/ttyUSB0). Auto-detect if not specified",
    )
    parser.add_argument(
        "--no-arduino",
        action="store_true",
        help="Disable Arduino USB interface",
    )

    args = parser.parse_args()

    logger.info("Starting Target System - TCP/UDP")
    logger.info(
        f"Configuration: Host={args.host}, TCP Command Port={args.tcp_command_port}"
    )
    logger.info(f"GPIO: LED={args.led_pin}, Input={args.input_pin}")
    logger.info(f"ADC: {'Disabled' if args.no_adc else 'Enabled (default)'}")
    logger.info(
        f"Arduino: {'Disabled' if args.no_arduino else ('Enabled' + (f' (port: {args.arduino_port})' if args.arduino_port else ' (auto-detect)'))}"
    )

    # Create and start target system
    target_system = TargetSystem(
        host_ip=args.host,
        tcp_command_port=args.tcp_command_port,
        led_pin=args.led_pin,
        input_pin=args.input_pin,
        use_adc=not args.no_adc,  # ADC enabled by default unless --no-adc is specified
        arduino_port=args.arduino_port,
        use_arduino=not args.no_arduino,
    )

    # Store target_system globally for signal handler access
    _target_system_instance = target_system

    try:
        target_system.start()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt signal")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Ensure LED is turned off in all cases
        try:
            target_system.stop()
        except Exception as e:
            logger.error(f"Error during stop: {e}")
            # Final attempt to turn off LED
            try:
                if (
                    target_system.tcp_command_server
                    and target_system.tcp_command_server.gpio_handler
                ):
                    success, msg = target_system.tcp_command_server.gpio_handler.led_off()
                    if not success:
                        logger.debug(f"Final LED off attempt: {msg}")
            except:
                pass
        logger.info("Target system shutdown complete")


if __name__ == "__main__":
    main()
