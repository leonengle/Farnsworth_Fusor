#!/usr/bin/env python3
import customtkinter as ctk
import threading
import time
import argparse
import logging
import signal
import sys
import atexit
from tcp_command_client import TCPCommandClient
from tcp_data_client import TCPDataClient
from udp_status_client import UDPStatusClient, UDPStatusReceiver
from command_handler import CommandHandler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HostMain")

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Options: "light", "dark", "system"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"


class FusorHostApp:
    def __init__(self, target_ip: str = "192.168.0.2", target_tcp_command_port: int = 2222,
                 tcp_data_port: int = 12345, udp_status_port: int = 8888):
        self.target_ip = target_ip
        self.target_tcp_command_port = target_tcp_command_port
        self.tcp_data_port = tcp_data_port
        self.udp_status_port = udp_status_port
        
        # Command handler - validates and builds commands
        self.command_handler = CommandHandler()
        
        # TCP command client - sends commands to target
        self.tcp_command_client = TCPCommandClient(target_ip, target_tcp_command_port)
        
        # TCP data client - receives periodic data from target
        self.tcp_data_client = TCPDataClient(
            target_ip=target_ip,
            target_port=tcp_data_port,
            data_callback=self._handle_tcp_data
        )
        
        # UDP status communication
        self.udp_status_client = UDPStatusClient(target_ip, 8889)
        self.udp_status_receiver = UDPStatusReceiver(udp_status_port, self._handle_udp_status)
        
        # UI components
        self.root = None
        self.data_display = None
        self.status_label = None
        self.voltage_scale = None
        self.pump_power_scale = None
        
        # Setup UI first
        self._setup_ui()
        
        # Connect to target
        if not self.tcp_command_client.connect():
            self._update_status("Failed to connect to target on startup", "red")
            self._update_data_display("[ERROR] Failed to connect to target - check network connection")
        else:
            self._update_status("Connected to target", "green")
            self._update_data_display("[System] Connected to target successfully")
        
        # Start TCP data client
        self.tcp_data_client.start()
        
        # Start UDP status communication
        self.udp_status_client.start()
        self.udp_status_receiver.start()
    
    def _setup_ui(self):
        self.root = ctk.CTk()
        self.root.title("Fusor Control Panel - TCP/UDP")
        self.root.geometry("900x700")
        
        # Main container
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Farnsworth Fusor Control Panel",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=10)
        
        # LED Control Section
        led_frame = ctk.CTkFrame(main_frame)
        led_frame.pack(fill="x", padx=10, pady=5)
        
        led_label = ctk.CTkLabel(led_frame, text="LED Control", font=ctk.CTkFont(size=14, weight="bold"))
        led_label.pack(pady=5)
        
        led_button_frame = ctk.CTkFrame(led_frame)
        led_button_frame.pack(pady=5)
        
        led_on_button = ctk.CTkButton(
            led_button_frame,
            text="LED ON",
            command=lambda: self._send_command("LED_ON"),
            font=ctk.CTkFont(size=14),
            width=150,
            height=40,
            fg_color="green",
            hover_color="darkgreen"
        )
        led_on_button.pack(side="left", padx=10, pady=10)
        
        led_off_button = ctk.CTkButton(
            led_button_frame,
            text="LED OFF",
            command=lambda: self._send_command("LED_OFF"),
            font=ctk.CTkFont(size=14),
            width=150,
            height=40,
            fg_color="red",
            hover_color="darkred"
        )
        led_off_button.pack(side="left", padx=10, pady=10)
        
        # Power Control Section
        power_frame = ctk.CTkFrame(main_frame)
        power_frame.pack(fill="x", padx=10, pady=5)
        
        power_label = ctk.CTkLabel(power_frame, text="Power Control", font=ctk.CTkFont(size=14, weight="bold"))
        power_label.pack(pady=5)
        
        power_control_frame = ctk.CTkFrame(power_frame)
        power_control_frame.pack(pady=5)
        
        voltage_label = ctk.CTkLabel(
            power_control_frame,
            text="Desired Voltage (V):",
            font=ctk.CTkFont(size=12)
        )
        voltage_label.pack(side="left", padx=5)
        
        self.voltage_value_label = ctk.CTkLabel(
            power_control_frame,
            text="0",
            font=ctk.CTkFont(size=12),
            width=60
        )
        self.voltage_value_label.pack(side="left", padx=5)
        
        self.voltage_scale = ctk.CTkSlider(
            power_control_frame,
            from_=0,
            to=28000,
            width=300,
            command=self._update_voltage_label
        )
        self.voltage_scale.pack(side="left", padx=5)
        
        voltage_button = ctk.CTkButton(
            power_control_frame,
            text="Set Voltage",
            command=self._set_voltage,
            font=ctk.CTkFont(size=12),
            width=120
        )
        voltage_button.pack(side="left", padx=5)
        
        # Vacuum Control Section
        vacuum_frame = ctk.CTkFrame(main_frame)
        vacuum_frame.pack(fill="x", padx=10, pady=5)
        
        vacuum_label = ctk.CTkLabel(vacuum_frame, text="Vacuum Control", font=ctk.CTkFont(size=14, weight="bold"))
        vacuum_label.pack(pady=5)
        
        vacuum_control_frame = ctk.CTkFrame(vacuum_frame)
        vacuum_control_frame.pack(pady=5)
        
        pump_label = ctk.CTkLabel(
            vacuum_control_frame,
            text="Pump Power (%):",
            font=ctk.CTkFont(size=12)
        )
        pump_label.pack(side="left", padx=5)
        
        self.pump_value_label = ctk.CTkLabel(
            vacuum_control_frame,
            text="0",
            font=ctk.CTkFont(size=12),
            width=60
        )
        self.pump_value_label.pack(side="left", padx=5)
        
        self.pump_power_scale = ctk.CTkSlider(
            vacuum_control_frame,
            from_=0,
            to=100,
            width=300,
            command=self._update_pump_label
        )
        self.pump_power_scale.pack(side="left", padx=5)
        
        pump_button = ctk.CTkButton(
            vacuum_control_frame,
            text="Set Pump Power",
            command=self._set_pump_power,
            font=ctk.CTkFont(size=12),
            width=120
        )
        pump_button.pack(side="left", padx=5)
        
        # Motor Control Section
        motor_frame = ctk.CTkFrame(main_frame)
        motor_frame.pack(fill="x", padx=10, pady=5)
        
        motor_label = ctk.CTkLabel(motor_frame, text="Motor Control", font=ctk.CTkFont(size=14, weight="bold"))
        motor_label.pack(pady=5)
        
        motor_control_frame = ctk.CTkFrame(motor_frame)
        motor_control_frame.pack(pady=5)
        
        steps_label = ctk.CTkLabel(
            motor_control_frame,
            text="Steps:",
            font=ctk.CTkFont(size=12)
        )
        steps_label.pack(side="left", padx=5)
        
        self.steps_entry = ctk.CTkEntry(motor_control_frame, width=100, font=ctk.CTkFont(size=12))
        self.steps_entry.pack(side="left", padx=5)
        self.steps_entry.insert(0, "100")
        
        motor_button = ctk.CTkButton(
            motor_control_frame,
            text="Move Motor",
            command=self._move_motor,
            font=ctk.CTkFont(size=12),
            width=120
        )
        motor_button.pack(side="left", padx=5)
        
        # Read Data Section
        read_frame = ctk.CTkFrame(main_frame)
        read_frame.pack(fill="x", padx=10, pady=5)
        
        read_label = ctk.CTkLabel(read_frame, text="Read Data", font=ctk.CTkFont(size=14, weight="bold"))
        read_label.pack(pady=5)
        
        read_button_frame = ctk.CTkFrame(read_frame)
        read_button_frame.pack(pady=5)
        
        read_input_button = ctk.CTkButton(
            read_button_frame,
            text="Read GPIO Input",
            command=lambda: self._send_command(self.command_handler.build_read_input_command()),
            font=ctk.CTkFont(size=12),
            width=150
        )
        read_input_button.pack(side="left", padx=5)
        
        read_adc_button = ctk.CTkButton(
            read_button_frame,
            text="Read ADC",
            command=lambda: self._send_command(self.command_handler.build_read_adc_command()),
            font=ctk.CTkFont(size=12),
            width=150
        )
        read_adc_button.pack(side="left", padx=5)
        
        # Data Display Section
        data_frame = ctk.CTkFrame(main_frame)
        data_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        data_label = ctk.CTkLabel(data_frame, text="Data Display (Read-Only from Target)", font=ctk.CTkFont(size=14, weight="bold"))
        data_label.pack(pady=5)
        
        # Text display with built-in scrolling
        self.data_display = ctk.CTkTextbox(
            data_frame,
            font=ctk.CTkFont(size=11, family="Courier"),
            wrap="word",
            height=200
        )
        self.data_display.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Ready - Waiting for commands",
            font=ctk.CTkFont(size=12),
            text_color="blue"
        )
        self.status_label.pack(pady=5)
        
        # Configure closing behavior
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _send_command(self, command: str):
        if not command:
            logger.warning("Attempted to send empty command")
            return
        
        try:
            # Ensure connected - try to connect if not connected
            if not self.tcp_command_client.is_connected():
                self._update_status(f"Connecting to {self.target_ip}:{self.target_tcp_command_port}...", "blue")
                self._update_data_display(f"[System] Attempting to connect to target at {self.target_ip}:{self.target_tcp_command_port}")
                
                if not self.tcp_command_client.connect():
                    self._update_status(f"Failed to connect to {self.target_ip}:{self.target_tcp_command_port}", "red")
                    self._update_data_display(f"[ERROR] Cannot send command {command} - connection failed")
                    self._update_data_display(f"[TROUBLESHOOTING] Check:")
                    self._update_data_display(f"  - Is target running? (python src/Target_Codebase/target_main.py)")
                    self._update_data_display(f"  - Is target IP correct? (Expected: {self.target_ip})")
                    self._update_data_display(f"  - Can you ping target? (ping {self.target_ip})")
                    self._update_data_display(f"  - Is firewall blocking port {self.target_tcp_command_port}?")
                    return
            
            # Send command
            self._update_status(f"Sending command: {command}...", "blue")
            response = self.tcp_command_client.send_command(command)
            
            # Display response
            if response:
                self._update_status(f"Command sent: {command} - Response: {response}", "green")
                self._update_data_display(f"[COMMAND] {command} -> [RESPONSE] {response}")
            else:
                self._update_status(f"Command sent: {command} - No response", "yellow")
                self._update_data_display(f"[COMMAND] {command} -> [RESPONSE] (no response)")
            
        except Exception as e:
            logger.error(f"Error sending command {command}: {e}")
            self._update_status(f"Error sending command: {e}", "red")
            self._update_data_display(f"[ERROR] Command {command} failed: {e}")
    
    def _update_voltage_label(self, value):
        self.voltage_value_label.configure(text=str(int(value)))
    
    def _update_pump_label(self, value):
        self.pump_value_label.configure(text=f"{int(value)}%")
    
    def _set_voltage(self):
        voltage = int(self.voltage_scale.get())
        command = self.command_handler.build_set_voltage_command(voltage)
        if command:
            self._send_command(command)
        else:
            self._update_status("Invalid voltage value", "red")
            self._update_data_display(f"[ERROR] Invalid voltage: {voltage}")
    
    def _set_pump_power(self):
        power = int(self.pump_power_scale.get())
        command = self.command_handler.build_set_pump_power_command(power)
        if command:
            self._send_command(command)
        else:
            self._update_status("Invalid power value", "red")
            self._update_data_display(f"[ERROR] Invalid power: {power}")
    
    def _move_motor(self):
        try:
            steps = int(self.steps_entry.get())
            command = self.command_handler.build_move_motor_command(steps)
            if command:
                self._send_command(command)
            else:
                self._update_status("Invalid steps value", "red")
                self._update_data_display("[ERROR] Steps must be a number")
        except ValueError:
            self._update_status("Invalid steps value", "red")
            self._update_data_display("[ERROR] Steps must be a number")
    
    def _handle_tcp_data(self, data: str):
        self._update_data_display(f"[TCP Data] {data}")
    
    def _handle_udp_status(self, message: str, address: tuple):
        self._update_data_display(f"[UDP Status] From {address[0]}: {message}")
    
    def _update_data_display(self, data: str):
        if not self.data_display or not self.root:
            return
        try:
            timestamp = time.strftime('%H:%M:%S')
            self.data_display.insert("end", f"{timestamp} - {data}\n")
            # Auto-scroll to bottom
            self.data_display.see("end")
        except Exception:
            pass
    
    def _update_status(self, message: str, color: str = "white"):
        if not self.status_label or not self.root:
            return
        try:
            self.status_label.configure(text=message, text_color=color)
        except Exception:
            pass
    
    def _on_closing(self):
        # Send LED_OFF command before shutting down
        self._turn_off_led()
        # Destroy root first to prevent UI update errors
        if self.root:
            try:
                self.root.destroy()
            except:
                pass
        self.stop()
    
    def _turn_off_led(self):
        # Try to send LED_OFF command - attempt multiple times if needed
        try:
            # Try to connect if not connected
            if not self.tcp_command_client.is_connected():
                self.tcp_command_client.connect()
            
            # Send LED_OFF command
            if self.tcp_command_client.is_connected():
                self.tcp_command_client.send_command("LED_OFF")
                if self.data_display and self.root:
                    self._update_data_display("[System] LED turned OFF during shutdown")
            else:
                if self.data_display and self.root:
                    self._update_data_display("[WARNING] Could not connect to turn off LED")
        except Exception as e:
            if self.data_display and self.root:
                try:
                    self._update_data_display(f"[ERROR] Could not turn off LED: {e}")
                except:
                    pass
            # Try one more time
            try:
                if self.tcp_command_client.connect():
                    self.tcp_command_client.send_command("LED_OFF")
            except:
                pass
    
    def run(self):
        print("Fusor Host Application starting...")
        print(f"Target IP: {self.target_ip}:{self.target_tcp_command_port}")
        print(f"TCP Data Port: {self.tcp_data_port}")
        print(f"UDP Status Port: {self.udp_status_port}")
        print("\nControl panel opening...")
        print("All buttons send commands to target.")
        print("Target listens, takes action, and sends read-only data back.")
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"\nUnexpected error: {e}")
        finally:
            # Always try to turn off LED before stopping
            self._turn_off_led()
            self.stop()
    
    def stop(self):
        # Try to turn off LED before disconnecting
        try:
            self._turn_off_led()
        except Exception as e:
            logger.error(f"Error turning off LED in stop: {e}")
        
        # Disconnect TCP command client
        try:
            self.tcp_command_client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting TCP client: {e}")
        
        # Stop TCP data client
        try:
            self.tcp_data_client.stop()
        except Exception as e:
            logger.error(f"Error stopping TCP data client: {e}")
        
        # Stop UDP status communication
        try:
            self.udp_status_client.stop()
            self.udp_status_receiver.stop()
        except Exception as e:
            logger.error(f"Error stopping UDP communication: {e}")


# Global app instance for signal handler access
_app_instance = None

def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    if _app_instance:
        try:
            _app_instance._turn_off_led()
            _app_instance.stop()
        except Exception as e:
            logger.error(f"Error during signal handler shutdown: {e}")
    sys.exit(0)

def atexit_handler():
    if _app_instance:
        try:
            _app_instance._turn_off_led()
        except Exception as e:
            logger.error(f"Error during atexit handler: {e}")

def main():
    global _app_instance
    
    # Set up signal handlers for graceful shutdown
    try:
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
    except Exception as e:
        logger.warning(f"Could not set up signal handlers: {e}")
    
    # Register atexit handler as fallback
    atexit.register(atexit_handler)
    
    parser = argparse.ArgumentParser(description="Fusor Host Application - TCP/UDP Control Panel")
    parser.add_argument("--target-ip", default="192.168.0.2", help="Target IP address (default: 192.168.0.2)")
    parser.add_argument("--target-tcp-command-port", type=int, default=2222, help="Target TCP command port (default: 2222)")
    parser.add_argument("--tcp-data-port", type=int, default=12345, help="TCP port for receiving data (default: 12345)")
    parser.add_argument("--udp-status-port", type=int, default=8888, help="UDP port for status communication (default: 8888)")
    
    args = parser.parse_args()
    
    # Create and run host application - control panel pops up
    app = FusorHostApp(
        target_ip=args.target_ip,
        target_tcp_command_port=args.target_tcp_command_port,
        tcp_data_port=args.tcp_data_port,
        udp_status_port=args.udp_status_port
    )
    
    _app_instance = app
    app.run()


if __name__ == "__main__":
    main()
