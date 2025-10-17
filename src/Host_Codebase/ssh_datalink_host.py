#!/usr/bin/env python3
"""
SSH Datalink Host - Main Host Application
This implements the Host Codebase as specified in the architecture diagram.

Features:
- Tkinter UI with button and read-only field
- SSH client to send commands to target
- TCP server to receive data from target
- Real-time data display
"""

import tkinter as tk
import threading
import socket
import paramiko
import time
from typing import Optional

class SSHDatalinkHost:
    """
    Main host application that implements the SSH datalink system.
    """
    
    def __init__(self, target_ip: str = "172.20.10.6", target_ssh_port: int = 2222,
                 tcp_port: int = 12345, target_username: str = "mdali", 
                 target_password: str = "password"):
        """
        Initialize the SSH Datalink Host.
        
        Args:
            target_ip: IP address of the target system
            target_ssh_port: SSH port on target system
            tcp_port: TCP port for receiving data from target
            target_username: Username for SSH connection
            target_password: Password for SSH connection
        """
        self.target_ip = target_ip
        self.target_ssh_port = target_ssh_port
        self.tcp_port = tcp_port
        self.target_username = target_username
        self.target_password = target_password
        
        # UI components
        self.root = None
        self.button = None
        self.readonly_field = None
        
        # TCP server
        self.tcp_server = None
        self.tcp_running = False
        self.tcp_thread = None
        
        # SSH client
        self.ssh_client = None
        
        # Setup UI
        self._setup_ui()
        
        # Start TCP listener
        self._start_tcp_listener()
        
    def _setup_ui(self):
        """Setup the Tkinter UI with button and read-only field."""
        self.root = tk.Tk()
        self.root.title("SSH Datalink Host")
        self.root.geometry("400x200")
        
        # Button for sending SSH commands
        self.button = tk.Button(
            self.root, 
            text="Send SSH Command", 
            command=self._send_ssh_command,
            font=("Arial", 12),
            bg="lightblue",
            height=2
        )
        self.button.pack(pady=20)
        
        # Read-only field for displaying TCP data
        self.readonly_field = tk.Text(
            self.root,
            height=6,
            width=50,
            state=tk.DISABLED,
            font=("Courier", 10),
            bg="lightgray"
        )
        self.readonly_field.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # Status label
        self.status_label = tk.Label(
            self.root,
            text="Ready - Click button to send SSH command",
            font=("Arial", 10),
            fg="green"
        )
        self.status_label.pack(pady=5)
        
    def _update_readonly_field(self, data: str):
        """Update the read-only field with new data."""
        self.readonly_field.config(state=tk.NORMAL)
        self.readonly_field.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {data}\n")
        self.readonly_field.see(tk.END)
        self.readonly_field.config(state=tk.DISABLED)
        
    def _update_status(self, message: str, color: str = "black"):
        """Update the status label."""
        self.status_label.config(text=message, fg=color)
        
    def _send_ssh_command(self):
        """Send SSH command to target when button is pressed."""
        try:
            # Create SSH client
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to target
            self.ssh_client.connect(
                hostname=self.target_ip,
                port=self.target_ssh_port,
                username=self.target_username,
                password=self.target_password,
                timeout=10
            )
            
            # Send LED_ON command
            stdin, stdout, stderr = self.ssh_client.exec_command("LED_ON")
            response = stdout.read().decode().strip()
            
            # Update status
            self._update_status(f"SSH command sent: LED_ON - Response: {response}", "green")
            
            # Close SSH connection
            self.ssh_client.close()
            
        except Exception as e:
            self._update_status(f"SSH Error: {e}", "red")
            print(f"SSH Error: {e}")
            
    def _start_tcp_listener(self):
        """Start TCP listener thread for receiving data from target."""
        self.tcp_running = True
        self.tcp_thread = threading.Thread(target=self._tcp_listener, daemon=True)
        self.tcp_thread.start()
        
    def _tcp_listener(self):
        """TCP listener thread for receiving data from target."""
        try:
            self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_server.bind(("0.0.0.0", self.tcp_port))
            self.tcp_server.listen(1)
            
            self._update_status(f"TCP server listening on port {self.tcp_port}", "blue")
            
            while self.tcp_running:
                try:
                    # Accept connection from target
                    client_socket, client_address = self.tcp_server.accept()
                    print(f"TCP connection from {client_address}")
                    
                    # Keep connection open and receive data
                    while self.tcp_running:
                        try:
                            data = client_socket.recv(1024).decode().strip()
                            if data:
                                # Display received data in read-only field
                                self._update_readonly_field(data)
                                self._update_status(f"TCP data received from {client_address[0]}", "green")
                            else:
                                break
                        except socket.error as e:
                            break
                    
                    client_socket.close()
                    
                except socket.error as e:
                    if self.tcp_running:
                        print(f"TCP server error: {e}")
                        break
                        
        except Exception as e:
            print(f"TCP listener error: {e}")
        finally:
            if self.tcp_server:
                self.tcp_server.close()
                
    def run(self):
        """Run the host application."""
        print("SSH Datalink Host starting...")
        print(f"Target IP: {self.target_ip}:{self.target_ssh_port}")
        print(f"TCP Port: {self.tcp_port}")
        print("TCP data from target will be displayed in the read-only field")
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.stop()
            
    def stop(self):
        """Stop the host application."""
        self.tcp_running = False
        if self.tcp_server:
            self.tcp_server.close()
        if self.ssh_client:
            self.ssh_client.close()
        if self.root:
            self.root.quit()

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SSH Datalink Host")
    parser.add_argument("--target-ip", default="172.20.10.6", help="Target IP address")
    parser.add_argument("--target-ssh-port", type=int, default=2222, help="Target SSH port")
    parser.add_argument("--tcp-port", type=int, default=12345, help="TCP port for receiving data")
    parser.add_argument("--username", default="mdali", help="SSH username")
    parser.add_argument("--password", default="password", help="SSH password")
    
    args = parser.parse_args()
    
    # Create and run host application
    host = SSHDatalinkHost(
        target_ip=args.target_ip,
        target_ssh_port=args.target_ssh_port,
        tcp_port=args.tcp_port,
        target_username=args.username,
        target_password=args.password
    )
    
    host.run()

if __name__ == "__main__":
    main()
