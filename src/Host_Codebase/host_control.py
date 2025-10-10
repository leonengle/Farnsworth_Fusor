# host_control.py
"""
Host-side script for controlling the Fusor target system.
- Connects to Raspberry Pi over SSH (port 2222)
- Sends LED and motor commands
- Receives and logs telemetry sent by Pi via echo (future support)
"""

import paramiko
import threading
import time
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("host_control.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("HostControl")

# SSH Config
PI_HOST = "192.168.1.101"  # Target Pi IP
PI_PORT = 2222
PI_USERNAME = "pi"
PI_PASSWORD = "raspberry"

class SSHController:
    def __init__(self, host, port, username, password):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def connect(self):
        try:
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            logger.info(f"Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to target: {e}")
            return False

    def send_command(self, command):
        try:
            channel = self.client.get_transport().open_session()
            channel.exec_command(command)
            response = channel.recv(1024).decode().strip()
            logger.info(f"Target Response: {response}")
            return response
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return None

    def disconnect(self):
        self.client.close()
        logger.info("Disconnected from target")


def telemetry_listener():
    logger.info("Telemetry listener started (waiting for reverse SSH echo)...")
    try:
        with open("telemetry.log", "a") as logfile:
            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.strip()
                logger.info(f"[Telemetry] {line}")
                logfile.write(line + "\n")
                logfile.flush()
    except KeyboardInterrupt:
        logger.info("Telemetry listener stopped")


def main():
    controller = SSHController(PI_HOST, PI_PORT, PI_USERNAME, PI_PASSWORD)
    if not controller.connect():
        return

    try:
        while True:
            cmd = input("Command (on/off/move:<steps>/exit): ").strip().lower()
            if cmd == "on":
                controller.send_command("LED_ON")
            elif cmd == "off":
                controller.send_command("LED_OFF")
            elif cmd.startswith("move:"):
                try:
                    steps = int(cmd.split(":")[1])
                    controller.send_command(f"MOVE_VAR:{steps}")
                except ValueError:
                    logger.warning("Invalid move command. Use move:<steps>")
            elif cmd == "exit":
                break
            else:
                print("Unknown command. Use 'on', 'off', 'move:<steps>', or 'exit'.")
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        controller.disconnect()


if __name__ == "__main__":
    # Optionally enable telemetry log capture
    # threading.Thread(target=telemetry_listener, daemon=True).start()
    main()
