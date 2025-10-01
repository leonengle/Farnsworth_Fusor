import paramiko
import tkinter as tk
from tkinter import messagebox
from base_classes import CommunicationInterface

class SSHClient(CommunicationInterface):
    def __init__(self, host, port, username, password, command):
        super().__init__(host, port, username, password, command)
        self.command = command
        self._client = None
        self._connected = False

    def send_command(self, data):
        """Send a command to the remote device."""
        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client.connect(self.host, port=self.port, username=self.username, password=self.password)
            self._connected = True

            # Send the command
            command = self.command.format(data)
            stdin, stdout, stderr = self._client.exec_command(command)

            # Collect any errors (optional)
            error = stderr.read().decode()
            if error:
                messagebox.showerror("Error sending data", error)
                return False
            else:
                messagebox.showinfo("Success", f"Sent successfully: {str(data)}")
                return True
        except Exception as e:
            messagebox.showerror("SSH Connection Failed", str(e))
            return False
        finally:
            if self._client:
                self._client.close()
                self._connected = False

    def receive_response(self):
        """Receive a response from the remote device."""
        # SSH doesn't typically maintain persistent connections for responses
        # This would need to be implemented based on specific use case
        return None

    def is_connected(self):
        """Check if the communication channel is active."""
        return self._connected

    def disconnect(self):
        """Close the communication channel."""
        if self._client:
            self._client.close()
            self._connected = False

    # Keep the old method for backward compatibility
    def send_ssh_command(self, bitstring):
        return self.send_command(bitstring)