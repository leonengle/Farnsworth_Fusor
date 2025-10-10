import RPi.GPIO as GPIO
import time
import sys
from base_classes import MotorControlInterface, VARIACControlInterface

# GPIO pin configuration
pin29 = 5
pin31 = 6
pin36 = 16
pin37 = 26

# Half-stepping sequence for bipolar stepper motor
step_sequence = [
    [1, 0, 0, 0],  
    [1, 0, 1, 0],  
    [0, 0, 1, 0],  
    [0, 1, 1, 0],  
    [0, 1, 0, 0],  
    [0, 1, 0, 1],  
    [0, 0, 0, 1],  
    [1, 0, 0, 1], 
]

class StepperMotorController(MotorControlInterface):
    """Stepper motor controller implementation."""
    
    def __init__(self, step_pins=None, step_sequence=None):
        if step_pins is None:
            step_pins = [pin29, pin31, pin36, pin37]
        if step_sequence is None:
            step_sequence = step_sequence
        
        super().__init__(step_pins, step_sequence)
        self._step_count = len(step_sequence)
        self._current_position = 0
    
    def initialize(self):
        """Initialize the motor control hardware."""
        try:
            GPIO.setmode(GPIO.BCM)
            for pin in self.step_pins:
                GPIO.setup(pin, GPIO.OUT)
            self._is_initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize motor controller: {e}")
            return False
    
    def move_steps(self, steps):
        """Move the motor by a specified number of steps."""
        if not self._is_initialized:
            print("Motor controller not initialized")
            return False
        
        if steps == 0:
            return True
        
        # Determine direction
        step_dir = 1 if steps > 0 else -1
        steps = abs(steps)
        
        # Move the specified number of steps
        step_index = 0
        for _ in range(steps):
            for pin in range(4):
                GPIO.output(self.step_pins[pin], self.step_sequence[step_index][pin])
            step_index = (step_index + step_dir) % self._step_count
            time.sleep(self._step_delay)
        
        # Turn off all coils
        for pin in self.step_pins:
            GPIO.output(pin, 0)
        
        # Update position
        self._current_position += steps * step_dir
        return True
    
    def move_to_position(self, target_position):
        """Move the motor to a specific position."""
        steps_needed = target_position - self._current_position
        return self.move_steps(steps_needed)
    
    def stop_motor(self):
        """Immediately stop the motor."""
        # Turn off all coils
        for pin in self.step_pins:
            GPIO.output(pin, 0)
        return True
    
    def set_step_delay(self, delay):
        """Set the delay between steps."""
        self._step_delay = delay
    
    def get_current_position(self):
        """Get the current motor position."""
        return self._current_position
    
    def reset_position(self):
        """Reset the motor position counter to zero."""
        self._current_position = 0
    
    def cleanup(self):
        """Clean up motor control resources."""
        for pin in self.step_pins:
            GPIO.output(pin, 0)
        GPIO.cleanup()
        self._is_initialized = False

class VARIACController(VARIACControlInterface):
    """VARIAC controller implementation."""
    
    def __init__(self, motor_controller=None):
        if motor_controller is None:
            motor_controller = StepperMotorController()
        super().__init__(motor_controller)
    
    def set_voltage_ratio(self, ratio):
        """Set the VARIAC voltage ratio."""
        ratio = self.validate_ratio(ratio)
        target_position = int(ratio * (self._max_position - self._min_position))
        success = self.motor_controller.move_to_position(target_position)
        if success:
            self._current_voltage_ratio = ratio
        return success
    
    def get_voltage_ratio(self):
        """Get the current VARIAC voltage ratio."""
        current_pos = self.motor_controller.get_current_position()
        self._current_voltage_ratio = current_pos / (self._max_position - self._min_position)
        return self._current_voltage_ratio
    
    def calibrate(self):
        """Calibrate the VARIAC to known positions."""
        # Move to minimum position
        self.motor_controller.move_to_position(self._min_position)
        self.motor_controller.reset_position()
        
        # Move to maximum position to verify range
        self.motor_controller.move_to_position(self._max_position)
        
        # Return to zero position
        self.motor_controller.move_to_position(0)
        return True

# Legacy function for backward compatibility
def moveVARIAC(steps):
    """Legacy function for moving VARIAC motor."""
    step_count = len(step_sequence)
    #direction of rotation logic
    step_dir = 1 
    if steps > 0:
        step_dir = -1
    if steps == 0:
        return
    #index will be used to point to the next step in the sequence
    step_index = 0
    
    for _ in range(abs(steps)):
        for pin in range(4):
            #the output of the pins will be based on the step sequence 
            GPIO.output([pin29, pin31, pin36, pin37][pin], step_sequence[step_index][pin])
            #update the index to the next step in the sequence
        step_index = (step_index + step_dir) % step_count
        time.sleep(0.25)
    #turn off all coils after execution is done
    for pin in [pin29, pin31, pin36, pin37]:
        GPIO.output(pin, 0)

if __name__ == "__main__":
    #error handling as well as cleanup for the pins
    try:
        if len(sys.argv) != 2:
            sys.exit(1)
        steps_input = int(sys.argv[1])
        moveVARIAC(steps_input)
    except ValueError:
        print("Provide an integer for steps desired")
    finally:
        GPIO.cleanup()