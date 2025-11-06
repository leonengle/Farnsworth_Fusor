"""
Abstract Base Classes for Host_Codebase components.
This module defines the interfaces that all host-side components must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional


class CommunicationInterface(ABC):
    """Abstract base class for communication protocols."""
    
    def __init__(self, host: str, port: int, username: str, password: str, command_template: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.command_template = command_template
    
    @abstractmethod
    def send_ssh_command(self, bitstring):
        """
        Send an SSH command to the remote device.
        
        Args:
            bitstring: The data to send
        """
        pass


class PowerControlInterface(ABC):
    """Abstract base class for power supply control."""
    
    def __init__(self, name: str, maxVoltage: float, maxCurrent: float):
        self.name = name
        self.maxVoltage = maxVoltage
        self.maxCurrent = maxCurrent
        self.i = 0
        self.v = 0
        self.vDesired = 0
        self.iDesired = 0
    
    @abstractmethod
    def set_voltage(self, voltageSetting):
        """
        Set the desired voltage output.
        
        Args:
            voltageSetting: Target voltage in volts
        """
        pass
    
    @abstractmethod
    def set_current(self, RPi, currentSetting):
        """
        Set the desired current limit.
        
        Args:
            RPi: Raspberry Pi communication object
            currentSetting: Target current in amperes
        """
        pass
    
    @abstractmethod
    def get_voltage(self, RPi):
        """
        Read the current voltage output.
        
        Args:
            RPi: Raspberry Pi communication object
            
        Returns:
            Current voltage reading
        """
        pass
    
    @abstractmethod
    def get_current(self, RPi):
        """
        Read the current current output.
        
        Args:
            RPi: Raspberry Pi communication object
            
        Returns:
            Current current reading
        """
        pass


class VacuumControlInterface(ABC):
    """Abstract base class for vacuum system control."""
    
    def __init__(self, name: str):
        self.name = name
        self.powerSetting = 0
    
    @abstractmethod
    def set_power(self, powerInput):
        """
        Set the pump power level.
        
        Args:
            powerInput: Power level as percentage (0-100)
        """
        pass

