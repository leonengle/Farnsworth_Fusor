"""
Configuration management for the Fusor control system.
"""

import json
import os
from typing import Dict, Any, Optional
import logging

class FusorConfig:
    """Configuration manager for fusor system parameters."""
    
    def __init__(self, config_file: str = "fusor_config.json"):
        self.config_file = config_file
        self.logger = logging.getLogger("FusorConfig")
        self._config = self._load_default_config()
        self.load_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration values."""
        return {
            "communication": {
                "host": "192.168.1.100",
                "port": 22,
                "username": "pi",
                "password": "raspberry",
                "command_template": "echo {} > ~/received_bits.txt"
            },
            "power_supply": {
                "name": "Fusor Supply",
                "max_voltage": 28000,
                "max_current": 0.040,
                "voltage_step": 100,
                "current_step": 0.001
            },
            "vacuum_pump": {
                "name": "TurboPump",
                "max_power": 100,
                "min_power": 0,
                "power_step": 5
            },
            "safety": {
                "max_voltage_limit": 25000,
                "max_current_limit": 0.035,
                "min_pressure": 1e-6,
                "max_pressure": 1e-3,
                "emergency_stop_enabled": True,
                "auto_shutdown_on_error": True
            },
            "logging": {
                "level": "INFO",
                "file": "fusor.log",
                "max_size_mb": 10,
                "backup_count": 5
            },
            "gui": {
                "window_size": "600x400",
                "update_interval_ms": 2000,
                "theme": "default"
            }
        }
    
    def load_config(self) -> bool:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self._config.update(file_config)
                self.logger.info(f"Configuration loaded from {self.config_file}")
                return True
            else:
                self.logger.warning(f"Config file {self.config_file} not found, using defaults")
                self.save_config()  # Create default config file
                return True
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return False
    
    def save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=4)
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            return False
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'power_supply.max_voltage')."""
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> bool:
        """Set configuration value using dot notation."""
        keys = key_path.split('.')
        config = self._config
        
        try:
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            config[keys[-1]] = value
            return True
        except Exception as e:
            self.logger.error(f"Failed to set config {key_path}: {e}")
            return False
    
    def validate_safety_limits(self, voltage: float, current: float, pressure: float) -> tuple[bool, str]:
        """Validate values against safety limits."""
        max_voltage = self.get("safety.max_voltage_limit", 25000)
        max_current = self.get("safety.max_current_limit", 0.035)
        min_pressure = self.get("safety.min_pressure", 1e-6)
        max_pressure = self.get("safety.max_pressure", 1e-3)
        
        if voltage > max_voltage:
            return False, f"Voltage {voltage}V exceeds safety limit {max_voltage}V"
        
        if current > max_current:
            return False, f"Current {current}A exceeds safety limit {max_current}A"
        
        if pressure < min_pressure or pressure > max_pressure:
            return False, f"Pressure {pressure:.2e} Torr outside safe range {min_pressure:.2e} - {max_pressure:.2e} Torr"
        
        return True, "All safety limits satisfied"
    
    def get_communication_config(self) -> Dict[str, Any]:
        """Get communication configuration."""
        return self.get("communication", {})
    
    def get_power_supply_config(self) -> Dict[str, Any]:
        """Get power supply configuration."""
        return self.get("power_supply", {})
    
    def get_vacuum_pump_config(self) -> Dict[str, Any]:
        """Get vacuum pump configuration."""
        return self.get("vacuum_pump", {})
    
    def get_safety_config(self) -> Dict[str, Any]:
        """Get safety configuration."""
        return self.get("safety", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get("logging", {})
    
    def get_gui_config(self) -> Dict[str, Any]:
        """Get GUI configuration."""
        return self.get("gui", {})

# Global configuration instance
config = FusorConfig()
