from typing import Optional, Callable
from tcp_command_client import TCPCommandClient
from tcp_client_object import TCPClientObject
import logging

logger = logging.getLogger("ActuatorObject")


class ActuatorObject:
    def __init__(self, name: str, label: str, tcp_client: TCPCommandClient, command_builder: Optional[Callable[[str, float], str]] = None, tcp_client_object: Optional[TCPClientObject] = None):
        self.name = name
        self.label = label
        self.tcp_client = tcp_client
        self.command_builder = command_builder
        self.tcp_client_object = tcp_client_object
        self.value = 0.0

    def setAnalogValue(self, value: float):
        self.value = value
        if self.tcp_client_object:
            self.tcp_client_object.send_actuator_command(self.name, value, self.label)
        elif self.command_builder:
            command = self.command_builder(self.name, value)
            if command:
                if not self.tcp_client.is_connected():
                    if not self.tcp_client.connect():
                        logger.error(f"Failed to connect to target for actuator {self.name}")
                        return
                response = self.tcp_client.send_command(command)
                if response:
                    logger.info(f"Actuator {self.name} (label: {self.label}) -> Command: {command} -> Response: {response}")

    def setDigitalValue(self, value: bool):
        self.value = 1.0 if value else 0.0
        if self.tcp_client_object:
            self.tcp_client_object.send_actuator_command(self.name, self.value, self.label)
        elif self.command_builder:
            command = self.command_builder(self.name, self.value)
            if command:
                if not self.tcp_client.is_connected():
                    if not self.tcp_client.connect():
                        logger.error(f"Failed to connect to target for actuator {self.name}")
                        return
                response = self.tcp_client.send_command(command)
                if response:
                    logger.info(f"Actuator {self.name} (label: {self.label}) -> Command: {command} -> Response: {response}")

