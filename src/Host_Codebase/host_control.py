# host_control.py
# host_control.py
"""
Host-side script for controlling the Fusor target system.
- Connects to Raspberry Pi over TCP (port 2222)
- Sends LED and motor commands
- Receives and logs telemetry sent by Pi via TCP (future support)
"""

import sys
import logging
from tcp_command_client import TCPCommandClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("host_control.log"),
        logging.StreamHandler()
    ]
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("host_control.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("HostControl")
logger = logging.getLogger("HostControl")

# TCP Config
PI_HOST = "192.168.0.2"  # Target Pi IP
PI_PORT = 2222

class TCPController:
    def __init__(self, host, port):
        self.client = TCPCommandClient(host, port)
        self.host = host
        self.port = port

    def connect(self):
        try:
            if self.client.connect():
                logger.info(f"Connected to {self.host}:{self.port}")
                return True
            else:
                logger.error(f"Failed to connect to target")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to target: {e}")
            return False

    def send_command(self, command):
        try:
            response = self.client.send_command(command)
            if response:
                logger.info(f"Target Response: {response}")
            else:
                logger.warning("No response from target")
            return response
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return None

    def disconnect(self):
        self.client.disconnect()
        logger.info("Disconnected from target")


def telemetry_listener():
    logger.info("Telemetry listener started (waiting for TCP data)...")
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
                line = line.strip()
                logger.info(f"[Telemetry] {line}")
                logfile.write(line + "\n")
                logfile.flush()
    except KeyboardInterrupt:
        logger.info("Telemetry listener stopped")


def main():
    controller = TCPController(PI_HOST, PI_PORT)
    if not controller.connect():
        return

    try:
        while True:
            cmd = input("Command (on/off/move:<steps>/exit): ").strip().lower()
            if cmd == "on":
                controller.send_command("LED_ON")
            cmd = input("Command (on/off/move:<steps>/exit): ").strip().lower()
            if cmd == "on":
                controller.send_command("LED_ON")
            elif cmd == "off":
                controller.send_command("LED_OFF")
                controller.send_command("LED_OFF")
            elif cmd.startswith("move:"):
                try:
                    steps = int(cmd.split(":")[1])
                    controller.send_command(f"MOVE_VAR:{steps}")
                except ValueError:
                    logger.warning("Invalid move command. Use move:<steps>")
            elif cmd == "exit":
                break
                try:
                    steps = int(cmd.split(":")[1])
                    controller.send_command(f"MOVE_VAR:{steps}")
                except ValueError:
                    logger.warning("Invalid move command. Use move:<steps>")
            elif cmd == "exit":
                break
            else:
                print("Unknown command. Use 'on', 'off', 'move:<steps>', or 'exit'.")
                print("Unknown command. Use 'on', 'off', 'move:<steps>', or 'exit'.")
    except KeyboardInterrupt:
        print("\nExiting.")
        print("\nExiting.")
    finally:
        controller.disconnect()

        controller.disconnect()


if __name__ == "__main__":
    # Optionally enable telemetry log capture
    # threading.Thread(target=telemetry_listener, daemon=True).start()
    # Optionally enable telemetry log capture
    # threading.Thread(target=telemetry_listener, daemon=True).start()
    main()