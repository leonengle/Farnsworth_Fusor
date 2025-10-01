"""
Abstract Base Classes for Host_Codebase components.
This module defines the interfaces that all host-side components must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, Union


class CommunicationInterface(ABC):
    """Abstract base class for communication protocols."""
    
    def __init__(self, host: str, port: int, username: str, password: str, command_template: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.command_template = command_template
    
    @abstractmethod
    def send_command(self, data: Union[str, int, bytes]) -> bool:
        """
        Send a command to the remote device.
        
        Args:
            data: The data to send (string, int, or bytes)
            
        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def receive_response(self) -> Optional[str]:
        """
        Receive a response from the remote device.
        
        Returns:
            Optional[str]: The response data, or None if no response
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the communication channel is active.
        
        Returns:
            bool: True if connected, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close the communication channel."""
        pass


class PowerControlInterface(ABC):
    """Abstract base class for power supply control."""
    
    def __init__(self, name: str, max_voltage: float, max_current: float):
        self.name = name
        self.max_voltage = max_voltage
        self.max_current = max_current
        self._current_voltage = 0.0
        self._current_current = 0.0
        self._desired_voltage = 0.0
        self._desired_current = 0.0
    
    @abstractmethod
    def set_voltage(self, voltage: float) -> bool:
        """
        Set the desired voltage output.
        
        Args:
            voltage: Target voltage in volts
            
        Returns:
            bool: True if voltage was set successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def set_current(self, current: float) -> bool:
        """
        Set the desired current limit.
        
        Args:
            current: Target current in amperes
            
        Returns:
            bool: True if current was set successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_voltage(self) -> float:
        """
        Read the current voltage output.
        
        Returns:
            float: Current voltage reading in volts
        """
        pass
    
    @abstractmethod
    def get_current(self) -> float:
        """
        Read the current current output.
        
        Returns:
            float: Current current reading in amperes
        """
        pass
    
    @abstractmethod
    def enable_output(self) -> bool:
        """
        Enable the power supply output.
        
        Returns:
            bool: True if enabled successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def disable_output(self) -> bool:
        """
        Disable the power supply output.
        
        Returns:
            bool: True if disabled successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def is_output_enabled(self) -> bool:
        """
        Check if the power supply output is enabled.
        
        Returns:
            bool: True if output is enabled, False otherwise
        """
        pass
    
    def validate_voltage(self, voltage: float) -> bool:
        """Validate voltage is within safe limits."""
        return 0 <= voltage <= self.max_voltage
    
    def validate_current(self, current: float) -> bool:
        """Validate current is within safe limits."""
        return 0 <= current <= self.max_current


class VacuumControlInterface(ABC):
    """Abstract base class for vacuum system control."""
    
    def __init__(self, name: str):
        self.name = name
        self._power_setting = 0.0
        self._is_running = False
    
    @abstractmethod
    def set_power(self, power_percent: float) -> bool:
        """
        Set the pump power level.
        
        Args:
            power_percent: Power level as percentage (0-100)
            
        Returns:
            bool: True if power was set successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def start_pump(self) -> bool:
        """
        Start the vacuum pump.
        
        Returns:
            bool: True if pump started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop_pump(self) -> bool:
        """
        Stop the vacuum pump.
        
        Returns:
            bool: True if pump stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_pressure(self) -> float:
        """
        Read the current pressure.
        
        Returns:
            float: Current pressure reading
        """
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """
        Check if the pump is currently running.
        
        Returns:
            bool: True if pump is running, False otherwise
        """
        pass
    
    def validate_power(self, power_percent: float) -> float:
        """Clamp power percentage to valid range."""
        return max(0.0, min(100.0, power_percent))


