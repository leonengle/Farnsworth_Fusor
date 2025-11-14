from abc import ABC, abstractmethod
from typing import Optional, Callable


class CommunicationClientInterface(ABC):
    def __init__(self, target_ip: str, target_port: int):
        self.target_ip = target_ip
        self.target_port = target_port
        self.connected = False

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def send_command(self, command: str, wait_response: bool = True) -> Optional[str]:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass


class DataReceiverInterface(ABC):
    def __init__(
        self,
        target_ip: str,
        target_port: int,
        data_callback: Optional[Callable[[str], None]] = None,
    ):
        self.target_ip = target_ip
        self.target_port = target_port
        self.data_callback = data_callback
        self.running = False

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def set_data_callback(self, callback: Callable[[str], None]):
        pass


class CommandBuilderInterface(ABC):
    @abstractmethod
    def build_led_on_command(self) -> str:
        pass

    @abstractmethod
    def build_led_off_command(self) -> str:
        pass

    @abstractmethod
    def build_set_voltage_command(self, voltage: int) -> Optional[str]:
        pass

    @abstractmethod
    def build_set_pump_power_command(self, power: int) -> Optional[str]:
        pass

    @abstractmethod
    def build_move_motor_command(self, steps: int) -> Optional[str]:
        pass
