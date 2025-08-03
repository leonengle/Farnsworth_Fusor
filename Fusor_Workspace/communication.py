import paramiko
import tkinter as tk

class SSHClient:
    def __init__(self, host, port, username, password, command):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.command = command

    def send_ssh_command(self, bitstring):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.host, port=self.port, username=self.username, password=self.password)

            # Send the command
            command = self.command.format(bitstring)
            stdin, stdout, stderr = client.exec_command(command)

            # Collect any errors (optional)
            error = stderr.read().decode()
            if error:
                tk.showError("Error sending data:", error)
            else:
                tk.showError("Sent successfully:", bitstring)
            client.close()
        except Exception as e:
            tk.showError("SSH Connection Failed", str(e))