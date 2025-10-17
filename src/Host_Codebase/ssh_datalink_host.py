"""
SSH Datalink Host Implementation
This implements the Host Codebase as described in the system architecture diagram.

Features:
- Tkinter UI with Button and Read-only field
- SSH command sending with specific bitstring when button is pressed
- TCP data reception and display in read-only field
- Verifies SSH datalink functionality
"""

import tkinter as tk
import threading
import socket
import paramiko
import time
from typing import Optional

class SSHDatalinkHost:
    """
    Host system that implements the SSH datalink verification system.
    """
    
    def __init__(self, target_ip: str = "192.168.1.101", ssh_port: int = 2222, 
                 tcp_port: int = 12345, username: str = "pi", password: str = "raspberry"):
        """
        Initialize the SSH datalink host.
        
        Args:
            target_ip: IP address of the target system
            ssh_port: SSH port on target system
            tcp_port: TCP port for receiving data from target
            username: SSH username
            password: SSH password
        """
        self.target_ip = target_ip
        self.ssh_port = ssh_port
        self.tcp_port = tcp_port
        self.username = username
        self.password = password
        
        # SSH client for sending commands
        self.ssh_client: Optional[paramiko.SSHClient] = None
        
        # TCP server for receiving data
        self.tcp_server: Optional[socket.socket] = None
        self.tcp_running = False
        self.tcp_thread: Optional[threading.Thread] = None
        
        # Specific bitstring as mentioned in diagram
        self.command_bitstring = "LED_ON"
        
        # Initialize UI
        self._setup_ui()
        
        print(f"SSH Datalink Host initialized")
        print(f"Target: {target_ip}:{ssh_port}")
        print(f"TCP Listener: {tcp_port}")
    
    def _setup_ui(self):
        """Setup the Tkinter UI as shown in the diagram."""
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
            text="Ready",
            font=("Arial", 10),
            fg="green"
        )
        self.status_label.pack(pady=5)
    
    def _update_status(self, message: str, color: str = "black"):
        """Update the status label."""
        self.status_label.config(text=message, fg=color)
        self.root.update()
    
    def _update_readonly_field(self, data: str):
        """Update the read-only field with received TCP data."""
        self.readonly_field.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.readonly_field.insert(tk.END, f"[{timestamp}] {data}\n")
        self.readonly_field.see(tk.END)
        self.readonly_field.config(state=tk.DISABLED)
        self.root.update()
    
    def _send_ssh_command(self):
        """Send SSH command with specific bitstring when button is pressed."""
        self._update_status("Sending SSH command...", "orange")
        
        try:
            # Create SSH client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to target
            client.connect(
                hostname=self.target_ip,
                port=self.ssh_port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            
            # Send the command with specific bitstring
            stdin, stdout, stderr = client.exec_command(self.command_bitstring)
            
            # Get response
            response = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            
            if error:
                self._update_status(f"SSH Error: {error}", "red")
            else:
                self._update_status(f"SSH Success: {response}", "green")
                print(f"SSH command '{self.command_bitstring}' sent successfully")
                print(f"Target response: {response}")
            
            client.close()
            
        except Exception as e:
            error_msg = f"SSH Connection Failed: {str(e)}"
            self._update_status(error_msg, "red")
            print(error_msg)
    
    def _tcp_listener(self):
        """TCP listener thread for receiving data from target."""
        try:
            # Create TCP server socket
            self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_server.bind(("0.0.0.0", self.tcp_port))
            self.tcp_server.listen(1)
            
            print(f"TCP listener started on port {self.tcp_port}")
            self._update_status(f"TCP listening on port {self.tcp_port}", "blue")
            
            while self.tcp_running:
                try:
                    # Accept connection from target
                    client_socket, client_address = self.tcp_server.accept()
                    print(f"TCP connection from {client_address}")
                    self._update_status(f"TCP connected to {client_address[0]}", "green")
                    
                    # Keep connection alive for persistent data reception
                    while self.tcp_running:
                        try:
                            # Receive data
                            data = client_socket.recv(1024).decode().strip()
                            if data:
                                print(f"Received TCP data: {data}")
                                self._update_readonly_field(data)
                                self._update_status(f"TCP data received from {client_address[0]}", "green")
                            else:
                                # Connection closed by client
                                break
                                
                        except socket.error as e:
                            print(f"TCP receive error: {e}")
                            break
                    
                    client_socket.close()
                    print(f"TCP connection closed with {client_address}")
                    
                except socket.error as e:
                    if self.tcp_running:
                        print(f"TCP socket error: {e}")
                    break
                    
        except Exception as e:
            print(f"TCP listener error: {e}")
            self._update_status(f"TCP Error: {str(e)}", "red")
        finally:
            if self.tcp_server:
                self.tcp_server.close()
    
    def start_tcp_listener(self):
        """Start the TCP listener thread."""
        if self.tcp_running:
            print("TCP listener already running")
            return
        
        self.tcp_running = True
        self.tcp_thread = threading.Thread(target=self._tcp_listener, daemon=True)
        self.tcp_thread.start()
    
    def stop_tcp_listener(self):
        """Stop the TCP listener."""
        self.tcp_running = False
        if self.tcp_server:
            self.tcp_server.close()
        if self.tcp_thread:
            self.tcp_thread.join(timeout=2)
        print("TCP listener stopped")
    
    def run(self):
        """Run the SSH datalink host application."""
        print("Starting SSH Datalink Host...")
        print("Press the button to send SSH commands to the target")
        print("TCP data from target will be displayed in the read-only field")
        
        # Start TCP listener
        self.start_tcp_listener()
        
        # Start the UI
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.stop_tcp_listener()
            print("SSH Datalink Host stopped")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SSH Datalink Host")
    parser.add_argument("--target-ip", default="192.168.1.101", 
                       help="Target IP address (default: 192.168.1.101)")
    parser.add_argument("--ssh-port", type=int, default=2222,
                       help="SSH port (default: 2222)")
    parser.add_argument("--tcp-port", type=int, default=12345,
                       help="TCP port for receiving data (default: 12345)")
    parser.add_argument("--username", default="pi",
                       help="SSH username (default: pi)")
    parser.add_argument("--password", default="raspberry",
                       help="SSH password (default: raspberry)")
    
    args = parser.parse_args()
    
    # Create and run the SSH datalink host
    host = SSHDatalinkHost(
        target_ip=args.target_ip,
        ssh_port=args.ssh_port,
        tcp_port=args.tcp_port,
        username=args.username,
        password=args.password
    )
    
    host.run()


if __name__ == "__main__":
    main()
