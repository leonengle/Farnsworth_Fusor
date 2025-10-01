from base_classes import VacuumControlInterface

class TurboPump(VacuumControlInterface):
    def __init__(self, name):
        super().__init__(name)
        self.powerSetting = self._power_setting  # Keep for backward compatibility

    def set_power(self, power_percent):
        """Set the pump power level."""
        self._power_setting = self.validate_power(power_percent)
        self.powerSetting = self._power_setting  # Keep for backward compatibility
        print(f"Vacuum pump set to {self._power_setting}%")
        return True

    def start_pump(self):
        """Start the vacuum pump."""
        self._is_running = True
        print(f"Turbo pump {self.name} started")
        return True

    def stop_pump(self):
        """Stop the vacuum pump."""
        self._is_running = False
        print(f"Turbo pump {self.name} stopped")
        return True

    def get_pressure(self):
        """Read the current pressure."""
        # Simulated pressure reading
        pressure = 1e-6 + (100 - self._power_setting) * 1e-8  # Simulated pressure
        print(f"Current pressure: {pressure:.2e} Torr")
        return pressure

    def is_running(self):
        """Check if the pump is currently running."""
        return self._is_running