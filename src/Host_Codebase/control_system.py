#!/usr/bin/env python3
# ==========================================================
# CONTROL SYSTEM MODULE FOR FUSOR
# (Sensors, Actuators, PID, Split-Range PID, Interlocks)
# ==========================================================

import time
import threading


# ==========================================================
# SENSOR ABSTRACTION
# ==========================================================
class Sensor:
    """
    A simple sensor object whose .value is updated externally
    via telemetry from host_main.py.
    """
    def __init__(self, name: str, initial=0.0):
        self.name = name
        self.value = initial
        self.timestamp = time.time()

    def update(self, new_value):
        self.value = float(new_value)
        self.timestamp = time.time()

    def read(self):
        return self.value


# ==========================================================
# ACTUATOR ABSTRACTION
# ==========================================================
class Actuator:
    """
    Wraps a FusorComponent and provides a uniform .write(value) API
    for PIDs and interlocks.
    """
    def __init__(self, name: str, component, min_val=0, max_val=100):
        self.name = name
        self.component = component
        self.min_val = min_val
        self.max_val = max_val

    def write(self, value):
        value = max(self.min_val, min(self.max_val, value))
        self.component.setAnalogValue(value)


class VariacActuator(Actuator):
    """
    Special actuator for the AC Variac
    using the SET_VARIAC:<raw> command.
    Range: 0–28000 (1 V per unit)
    """
    def __init__(self, component):
        super().__init__("variac", component, 0, 28000)

    def write(self, value):
        raw = int(max(0, min(28000, value)))
        self.component._send_target_command(f"SET_VARIAC:{raw}")


# ==========================================================
# BASIC PID CONTROLLER
# ==========================================================
class PID:
    """
    Fully generic PID controller running in its own thread.
    """
    def __init__(self, name, sensor: Sensor, actuator: Actuator,
                 kp, ki, kd,
                 setpoint=0.0,
                 output_limits=(0, 100),
                 sample_time=0.1):

        self.name = name
        self.sensor = sensor
        self.actuator = actuator

        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.setpoint = setpoint
        self.sample_time = sample_time

        self.out_min, self.out_max = output_limits

        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = time.time()

        self.enabled = False
        self.thread = None

    def enable(self):
        if not self.enabled:
            self.enabled = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def disable(self):
        self.enabled = False

    def set_setpoint(self, value):
        self.setpoint = float(value)
        self.integral = 0
        self.prev_error = 0

    def _loop(self):
        while self.enabled:
            now = time.time()
            dt = now - self.prev_time
            if dt < self.sample_time:
                time.sleep(0.001)
                continue
            self.prev_time = now

            measurement = self.sensor.read()
            error = self.setpoint - measurement

            # PID terms
            self.integral += error * dt
            derivative = (error - self.prev_error) / dt if dt > 0 else 0

            output = (
                self.kp * error +
                self.ki * self.integral +
                self.kd * derivative
            )

            # clamp output
            output = max(self.out_min, min(self.out_max, output))

            self.prev_error = error

            # Apply actuator
            self.actuator.write(output)

            time.sleep(0.001)


# ==========================================================
# SPLIT-RANGE PID (FAST VARIAC + SLOW DEUTERIUM VALVE)
# ==========================================================
class SplitRangePID:
    """
    For fusion current control:
        - fast actuator = Variac
        - slow actuator = Deuterium fuel valve
    """

    def __init__(self, name, sensor: Sensor,
                 fast_actuator: Actuator,
                 slow_actuator: Actuator,
                 kp, ki, kd,
                 setpoint=0.0,
                 fast_range=(0, 28000),
                 slow_range=(0, 100),
                 hysteresis=0.03,
                 sample_time=0.05):

        self.name = name
        self.sensor = sensor
        self.fast = fast_actuator
        self.slow = slow_actuator

        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.setpoint = setpoint
        self.sample_time = sample_time

        self.fast_min, self.fast_max = fast_range
        self.slow_min, self.slow_max = slow_range

        self.hysteresis = hysteresis
        self.mode = "FAST"  # FAST or SLOW

        self.integral = 0
        self.prev_error = 0
        self.prev_time = time.time()

        self.enabled = False
        self.thread = None

    def enable(self):
        if not self.enabled:
            self.enabled = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def disable(self):
        self.enabled = False

    def set_setpoint(self, value):
        self.setpoint = float(value)
        self.integral = 0
        self.prev_error = 0

    def _loop(self):
        while self.enabled:
            now = time.time()
            dt = now - self.prev_time
            if dt < self.sample_time:
                time.sleep(0.001)
                continue

            self.prev_time = now

            measurement = self.sensor.read()
            error = self.setpoint - measurement

            # PID terms
            self.integral += error * dt
            deriv = (error - self.prev_error) / dt if dt > 0 else 0
            pid_out = self.kp * error + self.ki * self.integral + self.kd * deriv
            self.prev_error = error

            # Mode switching
            if self.mode == "FAST":
                if abs(error) < self.setpoint * self.hysteresis:
                    self.mode = "SLOW"
            else:
                if abs(error) > self.setpoint * (self.hysteresis * 2):
                    self.mode = "FAST"

            # Apply output
            if self.mode == "FAST":
                out = max(self.fast_min, min(self.fast_max, pid_out))
                self.fast.write(out)
            else:
                out = max(self.slow_min, min(self.slow_max, pid_out))
                self.slow.write(out)

            time.sleep(0.001)


# ==========================================================
# INTERLOCK MANAGEMENT
# ==========================================================
class InterlockRule:
    def __init__(self, name, condition_fn, action_fn):
        self.name = name
        self.condition_fn = condition_fn
        self.action_fn = action_fn


class InterlockManager:
    def __init__(self):
        self.rules = []

    def add_rule(self, rule: InterlockRule):
        self.rules.append(rule)

    def evaluate(self):
        for rule in self.rules:
            if rule.condition_fn():
                rule.action_fn()


# ==========================================================
# CONTROL SYSTEM MANAGER
# ==========================================================
class ControlSystemManager:
    """
    Holds all sensors, actuators, PIDs, and interlocks.
    Runs interlock evaluation continuously.
    """

    def __init__(self):
        self.sensors = {}
        self.actuators = {}
        self.pids = {}
        self.interlocks = InterlockManager()

        self.enabled = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    # Registration API
    def add_sensor(self, key, sensor):
        self.sensors[key] = sensor

    def add_actuator(self, key, act):
        self.actuators[key] = act

    def add_pid(self, key, pid):
        self.pids[key] = pid

    def enable_pid(self, key):
        if key in self.pids:
            self.pids[key].enable()

    def disable_pid(self, key):
        if key in self.pids:
            self.pids[key].disable()

    def _loop(self):
        while self.enabled:
            self.interlocks.evaluate()
            time.sleep(0.01)
