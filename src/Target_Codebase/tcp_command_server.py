"""
TCP Command Server for Target System
This replaces the SSH server functionality with a TCP-based command server.

Features:
- TCP server to receive commands from host
- GPIO LED control for visual feedback when receiving commands
- GPIO input reading (jumper wire to ground/5V)
- Integration with existing motor control and ADC systems
"""

import threading
import time
import socket
import RPi.GPIO as GPIO

from logging_setup import setup_logging, get_logger
from typing import Optional, Callable

# Import real ADC - no mock fallback
from adc import MCP3008ADC

# setup logging for this module
setup_logging()
logger = get_logger("TCPCommandServer")


class TCPCommandServer:
    """
    TCP server class that handles command communication from the host.
    """
    def __init__(self, host: str = "0.0.0.0", port: int = 2222, 
                 led_pin: int = 26, input_pin: int = 6, use_adc: bool = False):
        """
        Initialize the TCP command server.
        
        Args:
            host: Host address to bind to (0.0.0.0 for all interfaces)
            port: TCP port to listen on
            led_pin: GPIO pin for LED output
            input_pin: GPIO pin for input reading
            use_adc: Enable ADC functionality
        """
        self.host = host
        self.port = port
        self.led_pin = led_pin
        self.input_pin = input_pin
        self.use_adc = use_adc
        self.server_socket = None
        self.server_thread = None
        self.running = False
        self.host_callback: Optional[Callable[[str], None]] = None
        
        # setup gpio pins for led and input
        self._setup_gpio()
        
        # setup adc if enabled
        self.adc = None
        if self.use_adc:
            self._setup_adc()
        
        logger.info(f"TCP Command Server initialized (LED: {led_pin}, Input: {input_pin}, ADC: {use_adc})")
    
    def _setup_gpio(self):
        """Configure GPIO pins - LED as output, input pin with pull-down resistor."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.led_pin, GPIO.OUT)
        GPIO.setup(self.input_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # start with led off
        GPIO.output(self.led_pin, GPIO.LOW)
        logger.info(f"GPIO setup complete - LED pin {self.led_pin}, Input pin {self.input_pin}")
    
    def _setup_adc(self):
        """Setup the ADC for analog readings."""
        try:
            self.adc = MCP3008ADC()
            if self.adc.initialize():
                logger.info("ADC initialized successfully")
            else:
                logger.error("Failed to initialize ADC")
                self.adc = None
        except Exception as e:
            logger.error(f"ADC setup error: {e}")
            self.adc = None
    
    def set_host_callback(self, callback: Callable[[str], None]):
        """
        Set the function that will be called to send data back to host.
        
        Args:
            callback: Function that accepts a data string
        """
        self.host_callback = callback
        logger.info("Host callback set")
    
    def _handle_command(self, command: str) -> str:
        """
        Process commands received from the host system.
        
        Args:
            command: Command string from host
            
        Returns:
            Response string to send back
        """
        logger.info(f"Received TCP command: {command}")
        
        # Strip whitespace and convert to string if needed
        if isinstance(command, bytes):
            command = command.decode('utf-8')
        command = command.strip()
        
        # check for led control commands
        if command == "LED_ON":
            # turn on the led for visual feedback
            GPIO.output(self.led_pin, GPIO.HIGH)
            logger.info("LED turned ON")
            return "LED_ON_SUCCESS"
        elif command == "LED_OFF":
            # turn off the led
            GPIO.output(self.led_pin, GPIO.LOW)
            logger.info("LED turned OFF")
            return "LED_OFF_SUCCESS"
        elif command.startswith("MOVE_VAR:"):
            # Handle motor control commands
            try:
                steps = int(command.split(":")[1])
                # TODO: Integrate with motor control if needed
                logger.info(f"Motor move command: {steps} steps")
                return f"MOVE_VAR_SUCCESS:{steps}"
            except (ValueError, IndexError):
                logger.warning(f"Invalid MOVE_VAR command: {command}")
                return "MOVE_VAR_ERROR:Invalid format"
        else:
            logger.warning(f"Unknown command: {command}")
            return "UNKNOWN_COMMAND"
    
    def _tcp_session_handler(self, client_socket, client_address):
        """
        Handle each TCP connection in its own thread.
        
        Args:
            client_socket: Client socket connection
            client_address: Client address tuple
        """
        logger.info(f"TCP session started with {client_address}")
        
        try:
            client_socket.settimeout(30)  # 30 second timeout for commands
            
            # Keep connection alive and process commands
            while self.running:
                try:
                    # Receive command from client
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    # Process command
                    command = data.decode('utf-8').strip()
                    response = self._handle_command(command)
                    
                    # Send response back
                    client_socket.send((response + "\n").encode('utf-8'))
                    logger.debug(f"Sent response: {response}")
                    
                except socket.timeout:
                    # Send heartbeat to keep connection alive
                    try:
                        client_socket.send("HEARTBEAT\n".encode('utf-8'))
                    except:
                        break
                    continue
                except socket.error as e:
                    logger.debug(f"Socket error in session: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"TCP session error: {e}")
        finally:
            client_socket.close()
            logger.info(f"TCP session ended with {client_address}")
    
    def start_server(self):
        """Start the TCP server and listen for connections."""
        if self.running:
            logger.warning("Server is already running")
            return
        
        self.running = True
        
        try:
            # create and configure socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.settimeout(1.0)  # Allow periodic checking of self.running
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            logger.info(f"TCP Command server started on {self.host}:{self.port}")
            
            # main server loop - accept connections
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    
                    # handle each connection in a separate thread
                    session_thread = threading.Thread(
                        target=self._tcp_session_handler,
                        args=(client_socket, client_address)
                    )
                    session_thread.daemon = True
                    session_thread.start()
                    
                except socket.timeout:
                    # Timeout is expected, continue loop to check self.running
                    continue
                except socket.error as e:
                    if self.running:
                        logger.error(f"Socket error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.stop_server()
    
    def stop_server(self):
        """Stop the TCP server."""
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")
        
        logger.info("TCP Command server stopped")
    
    def read_input_pin(self) -> int:
        """
        Read the input pin value (0 for ground, 1 for 5v).
        
        Returns:
            Pin value (0 or 1)
        """
        return GPIO.input(self.input_pin)
    
    def read_adc_channel(self, channel: int) -> int:
        """
        Read ADC channel value (0-1023 for 10-bit ADC).
        
        Args:
            channel: ADC channel number (0-7)
            
        Returns:
            ADC reading value
        """
        if self.adc and self.adc.is_initialized():
            return self.adc.read_channel(channel)
        return 0
    
    def read_adc_all_channels(self) -> list:
        """
        Read all ADC channels.
        
        Returns:
            List of ADC values for all channels
        """
        if self.adc and self.adc.is_initialized():
            return self.adc.read_all_channels()
        return [0] * 8
    
    def cleanup(self):
        """Clean up all resources."""
        self.stop_server()
        
        # Turn off LED before cleanup
        try:
            GPIO.output(self.led_pin, GPIO.LOW)
            logger.info("LED turned OFF during cleanup")
        except Exception as e:
            logger.error(f"Could not turn off LED during cleanup: {e}")
        
        if self.adc:
            self.adc.cleanup()
        GPIO.cleanup()
        logger.info("TCP Command Server cleanup complete")


class PeriodicDataSender:
    """
    Handles sending data to host every 1 second.
    """
    def __init__(self, command_server: TCPCommandServer, 
                 send_callback: Callable[[str], None], use_adc: bool = False):
        """
        Initialize the periodic data sender.
        
        Args:
            command_server: TCP command server instance
            send_callback: Function that accepts data string to send
            use_adc: Enable ADC functionality
        """
        self.command_server = command_server
        self.send_callback = send_callback
        self.use_adc = use_adc
        self.running = False
        self.sender_thread = None
        
        logger.info(f"Periodic data sender initialized (ADC: {use_adc})")
    
    def start(self):
        """Start the periodic data sending thread."""
        if self.running:
            logger.warning("Periodic sender is already running")
            return
        
        self.running = True
        self.sender_thread = threading.Thread(target=self._send_loop)
        self.sender_thread.daemon = True
        self.sender_thread.start()
        
        logger.info("Periodic data sender started")
    
    def stop(self):
        """Stop the periodic data sending."""
        self.running = False
        if self.sender_thread:
            self.sender_thread.join(timeout=2)
        
        logger.info("Periodic data sender stopped")
    
    def _send_loop(self):
        """Main loop that sends data every second."""
        while self.running:
            try:
                if self.use_adc and self.command_server.adc:
                    # send adc data - simple format as per diagram
                    adc_values = self.command_server.read_adc_all_channels()
                    data_message = f"ADC_DATA:{adc_values[0]}"
                    logger.debug(f"Sent ADC data: {adc_values[0]}")
                else:
                    # send gpio data - simple format as per diagram
                    pin_value = self.command_server.read_input_pin()
                    data_message = f"GPIO_INPUT:{pin_value}"
                    logger.debug(f"Sent GPIO data: {pin_value}")
                
                # send data to host via callback
                if self.send_callback:
                    self.send_callback(data_message)
                
                # wait 1 second before next send
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in periodic send loop: {e}")
                time.sleep(1.0)
