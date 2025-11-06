#!/usr/bin/env python3
"""
Host Main Program - TCP/UDP Implementation
This is the single entry point for the host application.

Features:
- CustomTkinter control panel with buttons for all commands
- TCP client to send commands to target (port 2222)
- TCP client to connect and receive read-only data from target (port 12345)
- UDP status/heartbeat communication
- Real-time data display showing all responses
- All buttons send commands to target which listens, takes action, and sends data back
"""

import customtkinter as ctk
import threading
import socket
import time
import argparse
from tcp_command_client import TCPCommandClient
from udp_status_client import UDPStatusClient, UDPStatusReceiver

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Options: "light", "dark", "system"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"


class FusorHostApp:
    """
    Main host application - single entry point with control panel.
    All buttons send commands to target, target listens, takes action, and sends data back.
    """
    
    def __init__(self, target_ip: str = "192.168.0.2", target_tcp_command_port: int = 2222,
                 tcp_data_port: int = 12345, udp_status_port: int = 8888):
        """
        Initialize the Fusor Host Application.
        
        Args:
            target_ip: IP address of the target system (RPi)
            target_tcp_command_port: TCP command port on target system
            tcp_data_port: TCP port for receiving data from target
            udp_status_port: UDP port for status communication
        """
        self.target_ip = target_ip
        self.target_tcp_command_port = target_tcp_command_port
        self.tcp_data_port = tcp_data_port
        self.udp_status_port = udp_status_port
        
        # TCP command client - sends commands to target
        self.tcp_command_client = TCPCommandClient(target_ip, target_tcp_command_port)
        
        # TCP data client - connects to target to receive read-only data
        self.tcp_data_client = None
        self.tcp_data_running = False
        self.tcp_data_thread = None
        
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
        
        # Start TCP data client to connect and receive read-only data from target
        self._start_tcp_data_client()
        
        # Start UDP status communication
        self.udp_status_client.start()
        self.udp_status_receiver.start()
    
    def _setup_ui(self):
        """Setup the CustomTkinter control panel with all buttons wired to send commands."""
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
            command=lambda: self._send_command("READ_INPUT"),
            font=ctk.CTkFont(size=12),
            width=150
        )
        read_input_button.pack(side="left", padx=5)
        
        read_adc_button = ctk.CTkButton(
            read_button_frame,
            text="Read ADC",
            command=lambda: self._send_command("READ_ADC"),
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
        """
        Send command to target via TCP.
        Target listens, takes action, and sends response back.
        Automatically retries connection if not connected.
        """
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
            self._update_status(f"Error sending command: {e}", "red")
            self._update_data_display(f"[ERROR] Command {command} failed: {e}")
    
    def _update_voltage_label(self, value):
        """Update voltage label when slider moves."""
        self.voltage_value_label.configure(text=str(int(value)))
    
    def _update_pump_label(self, value):
        """Update pump power label when slider moves."""
        self.pump_value_label.configure(text=f"{int(value)}%")
    
    def _set_voltage(self):
        """Set voltage - sends command to target."""
        voltage = int(self.voltage_scale.get())
        command = f"SET_VOLTAGE:{voltage}"
        self._send_command(command)
    
    def _set_pump_power(self):
        """Set pump power - sends command to target."""
        power = int(self.pump_power_scale.get())
        command = f"SET_PUMP_POWER:{power}"
        self._send_command(command)
    
    def _move_motor(self):
        """Move motor - sends command to target."""
        try:
            steps = int(self.steps_entry.get())
            command = f"MOVE_VAR:{steps}"
            self._send_command(command)
        except ValueError:
            self._update_status("Invalid steps value", "red")
            self._update_data_display("[ERROR] Steps must be a number")
    
    def _handle_udp_status(self, message: str, address: tuple):
        """Handle UDP status messages from target."""
        self._update_data_display(f"[UDP Status] From {address[0]}: {message}")
    
    def _update_data_display(self, data: str):
        """Update the data display with new read-only data from target."""
        timestamp = time.strftime('%H:%M:%S')
        self.data_display.insert("end", f"{timestamp} - {data}\n")
        # Auto-scroll to bottom
        self.data_display.see("end")
    
    def _update_status(self, message: str, color: str = "white"):
        """Update the status label."""
        self.status_label.configure(text=message, text_color=color)
    
    def _start_tcp_data_client(self):
        """Start TCP data client thread to connect and receive read-only data from target."""
        self.tcp_data_running = True
        self.tcp_data_thread = threading.Thread(target=self._tcp_data_client, daemon=True)
        self.tcp_data_thread.start()
    
    def _tcp_data_client(self):
        """
        TCP data client - connects to target and receives read-only data.
        Target sends sensor data, ADC readings, GPIO states, etc.
        """
        while self.tcp_data_running:
            try:
                # Connect to target's TCP data server
                self._update_data_display(f"[System] Connecting to target data server at {self.target_ip}:{self.tcp_data_port}")
                self.tcp_data_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.tcp_data_client.settimeout(5)
                self.tcp_data_client.connect((self.target_ip, self.tcp_data_port))
                
                self._update_status(f"Connected to target data server", "green")
                self._update_data_display(f"[TCP Data] Connected to target at {self.target_ip}:{self.tcp_data_port}")
                
                # Keep connection open and receive read-only data
                while self.tcp_data_running:
                    try:
                        data = self.tcp_data_client.recv(1024).decode().strip()
                        if data:
                            # Display received read-only data from target
                            self._update_data_display(f"[TCP Data] {data}")
                            self._update_status(f"Received data from target", "green")
                        else:
                            break
                    except socket.timeout:
                        # Timeout is expected, continue to check connection
                        continue
                    except socket.error as e:
                        self._update_data_display(f"[TCP Data] Connection error: {e}")
                        break
                
                self.tcp_data_client.close()
                self.tcp_data_client = None
                self._update_data_display(f"[TCP Data] Disconnected from target")
                
            except socket.timeout:
                if self.tcp_data_running:
                    self._update_data_display(f"[ERROR] TCP data connection timeout - target may not be ready")
                    self._update_data_display(f"[System] Retrying connection in 5 seconds...")
                    time.sleep(5)
                else:
                    break
            except ConnectionRefusedError:
                if self.tcp_data_running:
                    self._update_data_display(f"[ERROR] TCP data connection refused - is target listening on port {self.tcp_data_port}?")
                    self._update_data_display(f"[System] Retrying connection in 5 seconds...")
                    time.sleep(5)
                else:
                    break
            except OSError as e:
                if self.tcp_data_running:
                    if e.errno == 10051:  # Windows: Network unreachable
                        self._update_data_display(f"[ERROR] Network unreachable - cannot reach {self.target_ip}:{self.tcp_data_port}")
                    elif e.errno == 10061:  # Windows: Connection refused
                        self._update_data_display(f"[ERROR] Connection refused - is target running on port {self.tcp_data_port}?")
                    else:
                        self._update_data_display(f"[ERROR] TCP data connection failed (OSError {e.errno}): {e}")
                    self._update_data_display(f"[System] Retrying connection in 5 seconds...")
                    time.sleep(5)
                else:
                    break
            except socket.error as e:
                if self.tcp_data_running:
                    self._update_data_display(f"[ERROR] TCP data connection failed: {e}")
                    self._update_data_display(f"[System] Retrying connection in 5 seconds...")
                    time.sleep(5)
                else:
                    break
            except Exception as e:
                if self.tcp_data_running:
                    self._update_data_display(f"[ERROR] TCP data client error ({type(e).__name__}): {e}")
                    self._update_data_display(f"[System] Retrying connection in 5 seconds...")
                    time.sleep(5)
                else:
                    break
    
    def _on_closing(self):
        """Handle window closing - cleanup and send LED_OFF command."""
        # Send LED_OFF command before shutting down
        try:
            if self.tcp_command_client.is_connected():
                self.tcp_command_client.send_command("LED_OFF")
                self._update_data_display("[System] LED turned OFF during shutdown")
        except Exception as e:
            self._update_data_display(f"[ERROR] Could not turn off LED: {e}")
        
        self.stop()
        self.root.destroy()
    
    def run(self):
        """Run the host application - pop up control panel."""
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
        finally:
            self.stop()
    
    def stop(self):
        """Stop the host application and cleanup."""
        self.tcp_data_running = False
        
        # Disconnect TCP command client
        self.tcp_command_client.disconnect()
        
        # Stop UDP status communication
        self.udp_status_client.stop()
        self.udp_status_receiver.stop()
        
        # Close TCP data client
        if self.tcp_data_client:
            try:
                self.tcp_data_client.close()
            except Exception:
                pass
            self.tcp_data_client = None


def main():
    """Main function - single entry point."""
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
    
    app.run()


if __name__ == "__main__":
    main()
