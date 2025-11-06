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
    [1, 0, 0, 1]   
]

class StepperMotor(MotorControlInterface):
    def __init__(self, name, step_pin, dir_pin, enable_pin):
        super().__init__(name)
        self.step_pin = step_pin
        self.dir_pin = dir_pin
        self.enable_pin = enable_pin
        self.current_step = 0
        self.step_delay = 0.001  # 1ms delay between steps
        
        # Setup GPIO pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.step_pin, GPIO.OUT)
        GPIO.setup(self.dir_pin, GPIO.OUT)
        GPIO.setup(self.enable_pin, GPIO.OUT)
        
        # Enable motor by default
        GPIO.output(self.enable_pin, GPIO.LOW)
        
    def move_steps(self, steps):
        """Move motor by specified number of steps"""
        if steps == 0:
            return
            
        # Set direction
        direction = GPIO.HIGH if steps > 0 else GPIO.LOW
        GPIO.output(self.dir_pin, direction)
        
        # Move steps
        for _ in range(abs(steps)):
            self._step()
            time.sleep(self.step_delay)
            
    def _step(self):
        """Execute one step"""
        sequence = step_sequence[self.current_step % len(step_sequence)]
        
        # Set coil states
        GPIO.output(pin29, sequence[0])
        GPIO.output(pin31, sequence[1])
        GPIO.output(pin36, sequence[2])
        GPIO.output(pin37, sequence[3])
        
        self.current_step += 1
        
    def enable(self):
        """Enable motor"""
        GPIO.output(self.enable_pin, GPIO.LOW)
        
    def disable(self):
        """Disable motor"""
        GPIO.output(self.enable_pin, GPIO.HIGH)
        
    def set_speed(self, delay):
        """Set step delay (lower = faster)"""
        self.step_delay = delay

class VARIAC(VARIACControlInterface):
    def __init__(self, name, motor):
        super().__init__(name)
        self.motor = motor
        self.current_position = 0
        self.max_position = 2000  # Maximum steps for full rotation
        
    def set_voltage(self, voltage_percent):
        """Set VARIAC voltage as percentage (0-100)"""
        if voltage_percent < 0 or voltage_percent > 100:
            raise ValueError("Voltage percentage must be between 0 and 100")
            
        target_position = int((voltage_percent / 100) * self.max_position)
        steps_to_move = target_position - self.current_position
        
        if steps_to_move != 0:
            self.motor.move_steps(steps_to_move)
            self.current_position = target_position
            
        print(f"VARIAC set to {voltage_percent}% voltage")
        
    def get_voltage(self):
        """Get current voltage percentage"""
        return (self.current_position / self.max_position) * 100
        
    def emergency_stop(self):
        """Emergency stop - disable motor"""
        self.motor.disable()
        print("VARIAC emergency stop activated")

def main():
    try:
        # Initialize motor and VARIAC
        motor = StepperMotor("VARIAC_Motor", pin29, pin31, pin36)
        variac = VARIAC("Main_VARIAC", motor)
        
        print("VARIAC Control System Ready")
        print("Commands: set <0-100>, get, stop, exit")
        
        while True:
            try:
                command = input("VARIAC> ").strip().lower()
                
                if command == "exit":
                    break
                elif command == "stop":
                    variac.emergency_stop()
                elif command == "get":
                    print(f"Current voltage: {variac.get_voltage():.1f}%")
                elif command.startswith("set "):
                    try:
                        voltage = float(command.split()[1])
                        variac.set_voltage(voltage)
                    except (ValueError, IndexError):
                        print("Invalid voltage. Use: set <0-100>")
                else:
                    print("Unknown command. Use: set <0-100>, get, stop, exit")
                    
            except KeyboardInterrupt:
                print("\nEmergency stop!")
                variac.emergency_stop()
                break
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up")

if __name__ == "__main__":
    main()