import threading
import time
import socket
import paramiko
try:
    import RPi.GPIO as GPIO
    print("Using real RPi.GPIO")
except ImportError:
    import mock_gpio as GPIO
    print("Using mock GPIO for Windows testing")

from logging_setup import setup_logging, get_logger
from typing import Optional, Callable
<<<<<<< HEAD
from adc import MCP3008ADC
from tcp_data_sender import TCPDataSender
=======

try:
    from adc import MCP3008ADC
    print("Using real MCP3008ADC")
except ImportError:
    from mock_adc import MockMCP3008ADC as MCP3008ADC
    print("Using mock ADC for Windows testing")
>>>>>>> 1ee0e228647f8d2941aa2698e1bdc0a93f54eae6

# setup logging for this module
setup_logging()
logger = get_logger("SSHHelloWorld")


class SSHHelloWorldServer:
    # main ssh server class that handles communication with the host
    def __init__(self, host: str = "0.0.0.0", port: int = 2222, 
                 led_pin: int = 26, input_pin: int = 6, use_adc: bool = False):
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
        
        logger.info(f"SSH Hello World Server initialized (LED: {led_pin}, Input: {input_pin}, ADC: {use_adc})")
    
    def _setup_gpio(self):
        # configure gpio pins - led as output, input pin with pull-down resistor
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.led_pin, GPIO.OUT)
        GPIO.setup(self.input_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # start with led off
        GPIO.output(self.led_pin, GPIO.LOW)
        logger.info(f"GPIO setup complete - LED pin {self.led_pin}, Input pin {self.input_pin}")
    
    def _setup_adc(self):
        # setup the adc for analog readings
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
        # set the function that will be called to send data back to host
        self.host_callback = callback
        logger.info("Host callback set")
    
    def _handle_ssh_command(self, command: str) -> str:
        # process commands received from the host system
        logger.info(f"Received SSH command: {command}")
        
        # check for led control commands
        if command.strip() == "LED_ON":
            # turn on the led for visual feedback
            GPIO.output(self.led_pin, GPIO.HIGH)
            logger.info("LED turned ON")
            return "LED_ON_SUCCESS"
        elif command.strip() == "LED_OFF":
            # turn off the led
            GPIO.output(self.led_pin, GPIO.LOW)
            logger.info("LED turned OFF")
            return "LED_OFF_SUCCESS"
        else:
            logger.warning(f"Unknown command: {command}")
            return "UNKNOWN_COMMAND"
    
    def _ssh_session_handler(self, client_socket, client_address):
        # handle each ssh connection in its own thread
        logger.info(f"SSH session started with {client_address}")
        
        try:
            # create ssh transport layer
            transport = paramiko.Transport(client_socket)
            transport.add_server_key(paramiko.RSAKey.generate(2048))
            
            # start the ssh server
            transport.start_server(server=SSHServerInterface(self))
            
            # accept the ssh connection
            channel = transport.accept(20)
            if channel is None:
                logger.error("SSH channel not established")
                return
            
            logger.info("SSH channel established")
            
            # main command processing loop
            while self.running:
                try:
                    # receive command from host
                    command = channel.recv(1024).decode('utf-8').strip()
                    if not command:
                        break
                    
                    # process the command and get response
                    response = self._handle_ssh_command(command)
                    
                    # send response back to host
                    channel.send(response.encode('utf-8'))
                    
                except Exception as e:
                    logger.error(f"Error in SSH session: {e}")
                    break
            
            # cleanup ssh resources
            channel.close()
            transport.close()
            
        except Exception as e:
            logger.error(f"SSH session error: {e}")
        finally:
            client_socket.close()
            logger.info(f"SSH session ended with {client_address}")
    
    def start_server(self):
        # start the ssh server and listen for connections
        if self.running:
            logger.warning("Server is already running")
            return
        
        self.running = True
        
        try:
            # create and configure socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            logger.info(f"SSH Hello World server started on {self.host}:{self.port}")
            
            # main server loop - accept connections
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    
                    # handle each connection in a separate thread
                    session_thread = threading.Thread(
                        target=self._ssh_session_handler,
                        args=(client_socket, client_address)
                    )
                    session_thread.daemon = True
                    session_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        logger.error(f"Socket error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.stop_server()
    
    def stop_server(self):
        # stop the ssh server
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")
        
        logger.info("SSH Hello World server stopped")
    
    def read_input_pin(self) -> int:
        # read the input pin value (0 for ground, 1 for 5v)
        return GPIO.input(self.input_pin)
    
    def read_adc_channel(self, channel: int) -> int:
        # read adc channel value (0-1023 for 10-bit adc)
        if self.adc and self.adc.is_initialized():
            return self.adc.read_channel(channel)
        return 0
    
    def read_adc_all_channels(self) -> list:
        # read all adc channels
        if self.adc and self.adc.is_initialized():
            return self.adc.read_all_channels()
        return [0] * 8
    
    def cleanup(self):
        # clean up all resources
        self.stop_server()
        if self.adc:
            self.adc.cleanup()
        GPIO.cleanup()
        logger.info("SSH Hello World cleanup complete")


class SSHServerInterface(paramiko.ServerInterface):
    # ssh server interface for handling authentication and channels
    def __init__(self, hello_world_server: SSHHelloWorldServer):
        self.hello_world_server = hello_world_server
    
    def check_auth_password(self, username: str, password: str) -> int:
        # simple authentication - accept any username/password for hello world
        logger.info(f"SSH authentication attempt: {username}")
        return paramiko.AUTH_SUCCESSFUL
    
    def check_channel_request(self, kind: str, chanid: int) -> int:
        # allow all channel requests
        return paramiko.OPEN_SUCCEEDED


class PeriodicDataSender:
    # handles sending data to host every 1 second via TCP
    def __init__(self, hello_world_server: SSHHelloWorldServer, 
                 host: str = None, port: int = None, use_adc: bool = False):
        self.hello_world_server = hello_world_server
        self.tcp_sender = TCPDataSender(host, port)
        self.use_adc = use_adc
        self.running = False
        self.sender_thread = None
        
        logger.info(f"Periodic data sender initialized (Host: {host or 'default'}, Port: {port or 'default'}, ADC: {use_adc})")
    
    def start(self):
        # start the periodic data sending thread
        if self.running:
            logger.warning("Periodic sender is already running")
            return
        
        self.running = True
        self.sender_thread = threading.Thread(target=self._send_loop)
        self.sender_thread.daemon = True
        self.sender_thread.start()
        
        logger.info("Periodic data sender started")
    
    def stop(self):
        # stop the periodic data sending
        self.running = False
        if self.sender_thread:
            self.sender_thread.join(timeout=2)
        
        # disconnect TCP sender
        self.tcp_sender.disconnect()
        
        logger.info("Periodic data sender stopped")
    
    def _send_loop(self):
        # main loop that sends data every second via TCP
        while self.running:
            try:
                if self.use_adc and self.hello_world_server.adc:
                    # send adc data - simple format as per diagram
                    adc_values = self.hello_world_server.read_adc_all_channels()
                    success = self.tcp_sender.send_adc_data(adc_values[0])
                    if success:
                        logger.debug(f"Sent ADC data: {adc_values[0]}")
                    else:
                        logger.warning(f"Failed to send ADC data: {adc_values[0]}")
                else:
                    # send gpio data - simple format as per diagram
                    pin_value = self.hello_world_server.read_input_pin()
                    success = self.tcp_sender.send_gpio_data(pin_value)
                    if success:
                        logger.debug(f"Sent GPIO data: {pin_value}")
                    else:
                        logger.warning(f"Failed to send GPIO data: {pin_value}")
                
                # wait 1 second before next send
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in periodic send loop: {e}")
                time.sleep(1.0)


