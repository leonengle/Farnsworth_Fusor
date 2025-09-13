import RPi.GPIO as GPIO
import time
import sys

GPIO.setmode(GPIO.BCM)
#represent the coils for the bipolar stepper motor (assuming we're using H-bridge as our driver circuit)
pin29 = 5
pin31 = 6
pin36 = 16
pin37 = 26
#setting GPIO pins to output mode
GPIO.setup(pin29, GPIO.OUT)
GPIO.setup(pin31, GPIO.OUT)
GPIO.setup(pin36, GPIO.OUT)
GPIO.setup(pin37, GPIO.OUT)
#code will be based on half-stepping (assuming we're using H-bridge 
# as our driver circuit and check notes for why implement half stepping)
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

def moveVARIAC(steps):
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