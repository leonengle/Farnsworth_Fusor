import communication as com
import random #remove later
import logging
from base_classes import PowerControlInterface

class PowerSupply(PowerControlInterface):
    def __init__(self, name, maxVoltage, maxCurrent, communication_client=None):
        super().__init__(name, maxVoltage, maxCurrent)
        # Keep old attributes for backward compatibility
        self.i = self._current_current
        self.v = self._current_voltage
        self.vDesired = self._desired_voltage
        self.iDesired = self._desired_current
        self._output_enabled = False
        self.communication_client = communication_client
        self.logger = logging.getLogger(f"PowerSupply.{name}")
        
        # Initialize logging
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def set_voltage(self, voltage):
        """Set the desired voltage output."""
        if not self.validate_voltage(voltage):
            error_msg = f"Voltage {voltage}V exceeds maximum {self.max_voltage}V"
            self.logger.error(error_msg)
            print(error_msg)
            return False
        
        self._desired_voltage = voltage
        self.vDesired = voltage  # Keep for backward compatibility
        
        # Send command to target if communication client is available
        if self.communication_client:
            try:
                success = self.communication_client.send_command(f"VOLTAGE:{voltage}")
                if not success:
                    self.logger.error(f"Failed to send voltage command: {voltage}V")
                    return False
            except Exception as e:
                self.logger.error(f"Communication error setting voltage: {e}")
                return False
        
        self.logger.info(f"Setting voltage to {voltage}V")
        print(f"Setting voltage to {voltage}V")
        return True

    def set_current(self, current):
        """Set the desired current limit."""
        if not self.validate_current(current):
            print(f"Current {current}A exceeds maximum {self.max_current}A")
            return False
        
        self._desired_current = current
        self.iDesired = current  # Keep for backward compatibility
        #RPi.send_ssh_command(current)
        print(f"Setting current to {current}A")
        return True

    def get_voltage(self):
        """Read the current voltage output."""
        self._current_voltage = random.random() * self.max_voltage  # Simulated reading
        self.v = self._current_voltage  # Keep for backward compatibility
        print(f"Voltmeter reading is {self._current_voltage:.2f}V")
        return self._current_voltage

    def get_current(self):
        """Read the current current output."""
        self._current_current = random.random() * self.max_current  # Simulated reading
        self.i = self._current_current  # Keep for backward compatibility
        print(f"Current meter reading is {self._current_current:.3f}A")
        return self._current_current

    def enable_output(self):
        """Enable the power supply output."""
        self._output_enabled = True
        print("Power supply output enabled")
        return True

    def disable_output(self):
        """Disable the power supply output."""
        self._output_enabled = False
        print("Power supply output disabled")
        return True

    def is_output_enabled(self):
        """Check if the power supply output is enabled."""
        return self._output_enabled

    # Keep old methods for backward compatibility
    def set_current_legacy(self, RPi, currentSetting):
        return self.set_current(currentSetting)

    def get_voltage_legacy(self, RPi):
        return self.get_voltage()

    def get_current_legacy(self, RPi):
        return self.get_current()

    #configure interrupt for if max current is exceeded, decrease voltage setting