"""
Abstract Base Classes for Target_Codebase components.
This module defines the interfaces that all target-side components must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, Union


class MotorControlInterface(ABC):
    """Abstract base class for motor control."""
    
    def __init__(self, name: str):
        self.name = name
        self.position = 0
        self.speed = 0
        self.enabled = False
    
    @abstractmethod
    def move_steps(self, steps: int):
        """
        Move motor by specified number of steps.
        
        Args:
            steps: Number of steps to move (positive or negative)
        """
        pass
    
    @abstractmethod
    def enable(self):
        """Enable motor."""
        pass
    
    @abstractmethod
    def disable(self):
        """Disable motor."""
        pass
    
    @abstractmethod
    def set_speed(self, speed: float):
        """
        Set motor speed.
        
        Args:
            speed: Speed in steps per second
        """
        pass


class VARIACControlInterface(ABC):
    """Abstract base class for VARIAC control."""
    
    def __init__(self, name: str):
        self.name = name
        self.current_voltage = 0
        self.max_voltage = 100
    
    @abstractmethod
    def set_voltage(self, voltage_percent: float):
        """
        Set VARIAC voltage as percentage.
        
        Args:
            voltage_percent: Voltage percentage (0-100)
        """
        pass
    
    @abstractmethod
    def get_voltage(self) -> float:
        """
        Get current voltage percentage.
        
        Returns:
            Current voltage percentage
        """
        pass
    
    @abstractmethod
    def emergency_stop(self):
        """Emergency stop VARIAC."""
        pass


class SensorInterface(ABC):
    """Abstract base class for sensor readings."""
    
    def __init__(self, name: str):
        self.name = name
        self.value = 0
        self.unit = ""
    
    @abstractmethod
    def read(self) -> float:
        """
        Read sensor value.
        
        Returns:
            Current sensor reading
        """
        pass
    
    @abstractmethod
    def calibrate(self):
        """Calibrate sensor."""
        pass


class GPIOInterface(ABC):
    """Abstract base class for GPIO control."""
    
    def __init__(self, name: str):
        self.name = name
        self.pin = 0
        self.mode = "OUTPUT"
    
    @abstractmethod
    def setup(self, pin: int, mode: str):
        """
        Setup GPIO pin.
        
        Args:
            pin: GPIO pin number
            mode: Pin mode ("INPUT" or "OUTPUT")
        """
        pass
    
    @abstractmethod
    def write(self, pin: int, value: int):
        """
        Write value to GPIO pin.
        
        Args:
            pin: GPIO pin number
            value: Value to write (0 or 1)
        """
        pass
    
    @abstractmethod
    def read(self, pin: int) -> int:
        """
        Read value from GPIO pin.
        
        Args:
            pin: GPIO pin number
            
        Returns:
            Pin value (0 or 1)
        """
        pass