"""
An example of using the Motor class to control two motors with different pulse widths,
per ChatGPT. This also shows what I feel like is the ideal program structure, where
all our classes are in their own files and the main program just creates instances
and calls methods on them.
"""

pi = pigpio.pi()

# Motor 1 needs 5 µs pulse width
motor1 = Motor(pi, step_pin=17, dir_pin=27, pulse_width=5)

# Motor 2 needs 20 µs pulse width
motor2 = Motor(pi, step_pin=22, dir_pin=23, pulse_width=20)

# Queue moves (step_delay is full step period)
motor1.move(1000, direction=1, step_delay=1000)   # 1 kHz stepping
motor2.move(500, direction=0, step_delay=2000)    # 500 Hz stepping

motor1.command_queue.join()
motor2.command_queue.join()

motor1.stop()
motor2.stop()
pi.stop()
