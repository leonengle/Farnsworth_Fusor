from abc import ABC, abstractmethod
from typing import Optional, Union


class MotorControlInterface(ABC):
    def __init__(self, name: str):
        self.name = name
        self.position = 0
        self.speed = 0
        self.enabled = False
    
    @abstractmethod
    def move_steps(self, steps: int):
        pass
    
    @abstractmethod
    def enable(self):
        pass
    
    @abstractmethod
    def disable(self):
        pass
    
    @abstractmethod
    def set_speed(self, speed: float):
        pass


class VARIACControlInterface(ABC):
    def __init__(self, name: str):
        self.name = name
        self.current_voltage = 0
        self.max_voltage = 100
    
    @abstractmethod
    def set_voltage(self, voltage_percent: float):
        pass
    
    @abstractmethod
    def get_voltage(self) -> float:
        pass
    
    @abstractmethod
    def emergency_stop(self):
        pass


class SensorInterface(ABC):
    def __init__(self, name: str):
        self.name = name
        self.value = 0
        self.unit = ""
    
    @abstractmethod
    def read(self) -> float:
        pass
    
    @abstractmethod
    def calibrate(self):
        pass


class GPIOInterface(ABC):
    def __init__(self, name: str):
        self.name = name
        self.pin = 0
        self.mode = "OUTPUT"
    
    @abstractmethod
    def setup(self, pin: int, mode: str):
        pass
    
    @abstractmethod
    def write(self, pin: int, value: int):
        pass
    
    @abstractmethod
    def read(self, pin: int) -> int:
        pass


class ADCInterface(ABC):
    def __init__(self, spi_port: int = 0, spi_device: int = 0):
        self.spi_port = spi_port
        self.spi_device = spi_device
        self._is_initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        pass
    
    @abstractmethod
    def read_channel(self, channel: int) -> int:
        pass
    
    @abstractmethod
    def read_all_channels(self) -> list:
        pass
    
    def validate_channel(self, channel: int) -> bool:
        return 0 <= channel <= 7
    
    def is_initialized(self) -> bool:
        return self._is_initialized
    
    @abstractmethod
    def cleanup(self):
        pass
