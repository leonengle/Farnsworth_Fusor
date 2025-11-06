#!/usr/bin/env python3
"""
Host Main Program - TCP/UDP Implementation
This is the single entry point for the host application.

Features:
- Tkinter control panel with buttons for all commands
- TCP client to send commands to target
- TCP server to receive read-only data from target
- UDP status/heartbeat communication
- Real-time data display showing all responses
- All buttons send commands to target which listens, takes action, and sends data back
"""

import tkinter as tk
from tkinter import ttk
import threading
import socket
import time
import argparse
from tcp_command_client import TCPCommandClient
from udp_status_client import UDPStatusClient, UDPStatusReceiver


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
        
        # TCP data server - receives read-only data from target
        self.tcp_data_server = None
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
        
        # Start TCP data listener to receive read-only data from target
        self._start_tcp_data_listener()
        
        # Start UDP status communication
        self.udp_status_client.start()
        self.udp_status_receiver.start()
    
    def _setup_ui(self):
        """Setup the Tkinter control panel with all buttons wired to send commands."""
        self.root = tk.Tk()
        self.root.title("Fusor Control Panel - TCP/UDP")
        self.root.geometry("900x700")
        
        # Main container
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="Farnsworth Fusor Control Panel",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=10)
        
        # LED Control Section
        led_frame = tk.LabelFrame(main_frame, text="LED Control", font=("Arial", 10, "bold"))
        led_frame.pack(fill=tk.X, padx=10, pady=5)
        
        led_on_button = tk.Button(
            led_frame,
            text="LED ON",
            command=lambda: self._send_command("LED_ON"),
            bg="lightgreen",
            font=("Arial", 12),
            width=15,
            height=2
        )
        led_on_button.pack(side=tk.LEFT, padx=10, pady=10)
        
        led_off_button = tk.Button(
            led_frame,
            text="LED OFF",
            command=lambda: self._send_command("LED_OFF"),
            bg="lightcoral",
            font=("Arial", 12),
            width=15,
            height=2
        )
        led_off_button.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Power Control Section
        power_frame = tk.LabelFrame(main_frame, text="Power Control", font=("Arial", 10, "bold"))
        power_frame.pack(fill=tk.X, padx=10, pady=5)
        
        voltage_label = tk.Label(
            power_frame,
            text="Desired Voltage (V):",
            font=("Arial", 10)
        )
        voltage_label.pack(side=tk.LEFT, padx=5)
        
        self.voltage_scale = tk.Scale(
            power_frame,
            from_=0,
            to=28000,
            orient=tk.HORIZONTAL,
            length=300,
            font=("Arial", 9)
        )
        self.voltage_scale.pack(side=tk.LEFT, padx=5)
        
        voltage_button = tk.Button(
            power_frame,
            text="Set Voltage",
            command=self._set_voltage,
            font=("Arial", 10),
            width=12
        )
        voltage_button.pack(side=tk.LEFT, padx=5)
        
        # Vacuum Control Section
        vacuum_frame = tk.LabelFrame(main_frame, text="Vacuum Control", font=("Arial", 10, "bold"))
        vacuum_frame.pack(fill=tk.X, padx=10, pady=5)
        
        pump_label = tk.Label(
            vacuum_frame,
            text="Pump Power (%):",
            font=("Arial", 10)
        )
        pump_label.pack(side=tk.LEFT, padx=5)
        
        self.pump_power_scale = tk.Scale(
            vacuum_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=300,
            font=("Arial", 9)
        )
        self.pump_power_scale.pack(side=tk.LEFT, padx=5)
        
        pump_button = tk.Button(
            vacuum_frame,
            text="Set Pump Power",
            command=self._set_pump_power,
            font=("Arial", 10),
            width=12
        )
        pump_button.pack(side=tk.LEFT, padx=5)
        
        # Motor Control Section
        motor_frame = tk.LabelFrame(main_frame, text="Motor Control", font=("Arial", 10, "bold"))
        motor_frame.pack(fill=tk.X, padx=10, pady=5)
        
        steps_label = tk.Label(
            motor_frame,
            text="Steps:",
            font=("Arial", 10)
        )
        steps_label.pack(side=tk.LEFT, padx=5)
        
        self.steps_entry = tk.Entry(motor_frame, width=10, font=("Arial", 10))
        self.steps_entry.pack(side=tk.LEFT, padx=5)
        self.steps_entry.insert(0, "100")
        
        motor_button = tk.Button(
            motor_frame,
            text="Move Motor",
            command=self._move_motor,
            font=("Arial", 10),
            width=12
        )
        motor_button.pack(side=tk.LEFT, padx=5)
        
        # Read Data Section
        read_frame = tk.LabelFrame(main_frame, text="Read Data", font=("Arial", 10, "bold"))
        read_frame.pack(fill=tk.X, padx=10, pady=5)
        
        read_input_button = tk.Button(
            read_frame,
            text="Read GPIO Input",
            command=lambda: self._send_command("READ_INPUT"),
            font=("Arial", 10),
            width=15
        )
        read_input_button.pack(side=tk.LEFT, padx=5)
        
        read_adc_button = tk.Button(
            read_frame,
            text="Read ADC",
            command=lambda: self._send_command("READ_ADC"),
            font=("Arial", 10),
            width=15
        )
        read_adc_button.pack(side=tk.LEFT, padx=5)
        
        # Data Display Section
        data_frame = tk.LabelFrame(main_frame, text="Data Display (Read-Only from Target)", font=("Arial", 10, "bold"))
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Text display with scrollbar
        text_frame = tk.Frame(data_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.data_display = tk.Text(
            text_frame,
            state=tk.DISABLED,
            font=("Courier", 9),
            bg="white",
            wrap=tk.WORD
        )
        self.data_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.data_display.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.data_display.config(yscrollcommand=scrollbar.set)
        
        # Status label
        self.status_label = tk.Label(
            main_frame,
            text="Ready - Waiting for commands",
            font=("Arial", 10),
            fg="blue",
            bg="lightgray"
        )
        self.status_label.pack(pady=5)
        
        # Configure closing behavior
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _send_command(self, command: str):
        """
        Send command to target via TCP.
        Target listens, takes action, and sends response back.
        """
        try:
            # Ensure connected
            if not self.tcp_command_client.is_connected():
                if not self.tcp_command_client.connect():
                    self._update_status("Failed to connect to target", "red")
                    self._update_data_display(f"[ERROR] Cannot send command {command} - not connected")
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
        self.data_display.config(state=tk.NORMAL)
        timestamp = time.strftime('%H:%M:%S')
        self.data_display.insert(tk.END, f"{timestamp} - {data}\n")
        self.data_display.see(tk.END)
        self.data_display.config(state=tk.DISABLED)
    
    def _update_status(self, message: str, color: str = "black"):
        """Update the status label."""
        self.status_label.config(text=message, fg=color)
    
    def _start_tcp_data_listener(self):
        """Start TCP data listener thread to receive read-only data from target."""
        self.tcp_data_running = True
        self.tcp_data_thread = threading.Thread(target=self._tcp_data_listener, daemon=True)
        self.tcp_data_thread.start()
    
    def _tcp_data_listener(self):
        """
        TCP data listener - receives read-only data from target.
        Target sends sensor data, ADC readings, GPIO states, etc.
        """
        try:
            self.tcp_data_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_data_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_data_server.bind(("0.0.0.0", self.tcp_data_port))
            self.tcp_data_server.listen(1)
            
            self._update_status(f"TCP data server listening on port {self.tcp_data_port}", "blue")
            self._update_data_display(f"[System] TCP data server listening on port {self.tcp_data_port} for read-only data from target")
            
            while self.tcp_data_running:
                try:
                    # Accept connection from target
                    client_socket, client_address = self.tcp_data_server.accept()
                    self._update_data_display(f"[TCP Data] Connection from target {client_address[0]}:{client_address[1]}")
                    
                    # Keep connection open and receive read-only data
                    while self.tcp_data_running:
                        try:
                            data = client_socket.recv(1024).decode().strip()
                            if data:
                                # Display received read-only data from target
                                self._update_data_display(f"[TCP Data] {data}")
                                self._update_status(f"Received data from target", "green")
                            else:
                                break
                        except socket.error as e:
                            break
                    
                    client_socket.close()
                    self._update_data_display(f"[TCP Data] Connection closed from {client_address[0]}")
                    
                except socket.error as e:
                    if self.tcp_data_running:
                        self._update_data_display(f"[ERROR] TCP data server error: {e}")
                        break
                        
        except Exception as e:
            self._update_data_display(f"[ERROR] TCP data listener error: {e}")
        finally:
            if self.tcp_data_server:
                self.tcp_data_server.close()
    
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
        
        # Close TCP data server
        if self.tcp_data_server:
            self.tcp_data_server.close()


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
