import pigpio
import threading
import queue

"""
Asked ChatGPT to write a general framework, with the threading library that 
would allow us to control motors simultaneously without blocking the main thread.
"""

class Motor:
    def __init__(self, pi, step_pin, dir_pin, pulse_width=10):
        """
        pi          : pigpio.pi() instance
        step_pin    : GPIO for step signal
        dir_pin     : GPIO for direction signal
        pulse_width : microseconds the step pin stays high
        """
        self.pi = pi
        self.step_pin = step_pin
        self.dir_pin = dir_pin
        self.pulse_width = pulse_width
        
        # Set up pins
        self.pi.set_mode(step_pin, pigpio.OUTPUT)
        self.pi.set_mode(dir_pin, pigpio.OUTPUT)
        
        # Initialize pins
        self.pi.write(step_pin, 0)
        self.pi.write(dir_pin, 0)
        
        # Motor state
        self.position = 0
        self.target_position = 0
        self.speed = 1000  # steps per second
        self.running = False
        
        # Threading
        self.command_queue = queue.Queue()
        self.motor_thread = threading.Thread(target=self._motor_loop, daemon=True)
        self.motor_thread.start()
    
    def _motor_loop(self):
        """Main motor control loop running in separate thread"""
        while True:
            try:
                # Get command from queue (blocking)
                command = self.command_queue.get(timeout=1.0)
                
                if command[0] == "move":
                    steps = command[1]
                    self._move_steps(steps)
                elif command[0] == "stop":
                    self.running = False
                elif command[0] == "set_speed":
                    self.speed = command[1]
                    
                self.command_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Motor error: {e}")
    
    def _move_steps(self, steps):
        """Move motor by specified number of steps"""
        if steps == 0:
            return
            
        self.running = True
        
        # Set direction
        direction = 1 if steps > 0 else 0
        self.pi.write(self.dir_pin, direction)
        
        # Calculate step delay
        step_delay = 1.0 / self.speed
        
        # Move steps
        for _ in range(abs(steps)):
            if not self.running:
                break
                
            # Generate step pulse
            self.pi.write(self.step_pin, 1)
            self.pi.gpio_delay(self.pulse_width)
            self.pi.write(self.step_pin, 0)
            
            # Update position
            self.position += 1 if steps > 0 else -1
            
            # Wait for next step
            time.sleep(step_delay)
    
    def move_relative(self, steps):
        """Move motor relative to current position"""
        self.command_queue.put(("move", steps))
    
    def move_absolute(self, position):
        """Move motor to absolute position"""
        steps = position - self.position
        self.move_relative(steps)
    
    def stop(self):
        """Stop motor immediately"""
        self.command_queue.put(("stop",))
    
    def set_speed(self, speed):
        """Set motor speed in steps per second"""
        self.command_queue.put(("set_speed", speed))
    
    def get_position(self):
        """Get current motor position"""
        return self.position
    
    def home(self):
        """Home motor to position 0"""
        self.move_absolute(0)

# Example usage
if __name__ == "__main__":
    pi = pigpio.pi()
    
    # Create motor instance
    motor = Motor(pi, step_pin=18, dir_pin=19)
    
    try:
        print("Motor control ready. Commands: move <steps>, home, stop, speed <steps/sec>")
        
        while True:
            command = input("Motor> ").strip().lower()
            
            if command == "stop":
                motor.stop()
            elif command == "home":
                motor.home()
            elif command.startswith("move "):
                try:
                    steps = int(command.split()[1])
                    motor.move_relative(steps)
                except ValueError:
                    print("Invalid steps value")
            elif command.startswith("speed "):
                try:
                    speed = int(command.split()[1])
                    motor.set_speed(speed)
                except ValueError:
                    print("Invalid speed value")
            else:
                print("Unknown command")
                
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        motor.stop()
        pi.stop()