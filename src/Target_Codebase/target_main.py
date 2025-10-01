"""
An example of using the Motor class to control two motors with different pulse widths,
per ChatGPT. This also shows what I feel like is the ideal program structure, where
all our classes are in their own files and the main program just creates instances
and calls methods on them.
"""

import pigpio
from motor_control import Motor
from logging_setup import setup_logging, get_logger

# Setup logging first
setup_logging()
logger = get_logger("TargetMain")

try:
    pi = pigpio.pi()
    logger.info("pigpio initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize pigpio: {e}")
    exit(1)

# Motor 1 needs 5 µs pulse width
motor1 = Motor(pi, step_pin=17, dir_pin=27, pulse_width=5)
logger.info("Motor 1 initialized (step_pin=17, dir_pin=27, pulse_width=5µs)")

# Motor 2 needs 20 µs pulse width
motor2 = Motor(pi, step_pin=22, dir_pin=23, pulse_width=20)
logger.info("Motor 2 initialized (step_pin=22, dir_pin=23, pulse_width=20µs)")

# Queue moves (step_delay is full step period)
logger.info("Starting motor movements...")
motor1.move(1000, direction=1, step_delay=1000)   # 1 kHz stepping
motor2.move(500, direction=0, step_delay=2000)    # 500 Hz stepping

logger.info("Waiting for motor movements to complete...")
motor1.command_queue.join()
motor2.command_queue.join()

logger.info("Stopping motors and cleaning up...")
motor1.stop()
motor2.stop()
pi.stop()
logger.info("Target main program completed successfully")
