"""
Abstract Base Classes for Target_Codebase components.
This module defines the interfaces that all target-side components must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, List


class ADCInterface(ABC):
    """Abstract base class for Analog-to-Digital Converter operations."""
    
    def __init__(self, spi_port: int = 0, spi_device: int = 0):
        self.spi_port = spi_port
        self.spi_device = spi_device
        self._is_initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the ADC hardware.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def read_channel(self, channel: int) -> int:
        """
        Read a single ADC channel.
        
        Args:
            channel: Channel number to read (0-7 for MCP3008)
            
        Returns:
            int: ADC reading value (0-1023 for 10-bit ADC)
        """
        pass
    
    @abstractmethod
    def read_multiple_channels(self, channels: List[int]) -> List[int]:
        """
        Read multiple ADC channels.
        
        Args:
            channels: List of channel numbers to read
            
        Returns:
            List[int]: List of ADC readings corresponding to input channels
        """
        pass
    
    @abstractmethod
    def read_all_channels(self) -> List[int]:
        """
        Read all available ADC channels.
        
        Returns:
            List[int]: List of ADC readings for all channels
        """
        pass
    
    @abstractmethod
    def convert_to_voltage(self, adc_value: int, reference_voltage: float = 3.3) -> float:
        """
        Convert ADC reading to voltage.
        
        Args:
            adc_value: Raw ADC reading
            reference_voltage: Reference voltage for conversion
            
        Returns:
            float: Voltage value
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up ADC resources."""
        pass
    
    def validate_channel(self, channel: int) -> bool:
        """Validate channel number is within valid range."""
        return 0 <= channel <= 7
    
    def is_initialized(self) -> bool:
        """Check if ADC is initialized."""
        return self._is_initialized


class MotorControlInterface(ABC):
    """Abstract base class for motor control operations."""
    
    def __init__(self, step_pins: List[int], step_sequence: List[List[int]]):
        self.step_pins = step_pins
        self.step_sequence = step_sequence
        self._current_position = 0
        self._is_initialized = False
        self._step_delay = 0.25  # Default step delay in seconds
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the motor control hardware.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def move_steps(self, steps: int) -> bool:
        """
        Move the motor by a specified number of steps.
        
        Args:
            steps: Number of steps to move (positive for one direction, negative for opposite)
            
        Returns:
            bool: True if movement completed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def move_to_position(self, target_position: int) -> bool:
        """
        Move the motor to a specific position.
        
        Args:
            target_position: Target position in steps
            
        Returns:
            bool: True if movement completed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop_motor(self) -> bool:
        """
        Immediately stop the motor.
        
        Returns:
            bool: True if motor stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def set_step_delay(self, delay: float) -> None:
        """
        Set the delay between steps.
        
        Args:
            delay: Delay in seconds between steps
        """
        pass
    
    @abstractmethod
    def get_current_position(self) -> int:
        """
        Get the current motor position.
        
        Returns:
            int: Current position in steps
        """
        pass
    
    @abstractmethod
    def reset_position(self) -> None:
        """Reset the motor position counter to zero."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up motor control resources."""
        pass
    
    def is_initialized(self) -> bool:
        """Check if motor control is initialized."""
        return self._is_initialized


class VARIACControlInterface(ABC):
    """Abstract base class for VARIAC (Variable Autotransformer) control."""
    
    def __init__(self, motor_controller: MotorControlInterface):
        self.motor_controller = motor_controller
        self._min_position = 0
        self._max_position = 1000  # Example max steps
        self._current_voltage_ratio = 0.0
    
    @abstractmethod
    def set_voltage_ratio(self, ratio: float) -> bool:
        """
        Set the VARIAC voltage ratio.
        
        Args:
            ratio: Voltage ratio (0.0 to 1.0)
            
        Returns:
            bool: True if ratio set successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_voltage_ratio(self) -> float:
        """
        Get the current VARIAC voltage ratio.
        
        Returns:
            float: Current voltage ratio (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    def calibrate(self) -> bool:
        """
        Calibrate the VARIAC to known positions.
        
        Returns:
            bool: True if calibration successful, False otherwise
        """
        pass
    
    def validate_ratio(self, ratio: float) -> float:
        """Clamp voltage ratio to valid range."""
        return max(0.0, min(1.0, ratio))


