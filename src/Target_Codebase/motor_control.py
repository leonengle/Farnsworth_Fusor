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
        self.pulse_width = pulse_width  # µs

        # Setup pins
        self.pi.set_mode(step_pin, pigpio.OUTPUT)
        self.pi.set_mode(dir_pin, pigpio.OUTPUT)

        # Command queue
        self.command_queue = queue.Queue()

        # Worker thread
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def move(self, steps, direction=1, step_delay=1000):
        """
        Queue a move command.
        steps     : number of step pulses
        direction : 1=forward, 0=reverse
        step_delay: total period of one step (µs).
                    Must be >= pulse_width.
        """
        if step_delay < self.pulse_width:
            raise ValueError("step_delay must be >= pulse_width")
        self.command_queue.put((steps, direction, step_delay))

    def _worker(self):
        while not self._stop_event.is_set():
            try:
                steps, direction, step_delay = self.command_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            self.pi.write(self.dir_pin, direction)

            # Build waveform for this move
            pulses = []
            low_time = step_delay - self.pulse_width
            for _ in range(steps):
                pulses.append(pigpio.pulse(1 << self.step_pin, 0, self.pulse_width))
                pulses.append(pigpio.pulse(0, 1 << self.step_pin, low_time))

            self.pi.wave_clear()
            self.pi.wave_add_generic(pulses)
            wid = self.pi.wave_create()

            if wid >= 0:
                self.pi.wave_send_once(wid)
                while self.pi.wave_tx_busy():
                    pass
                self.pi.wave_delete(wid)

            self.command_queue.task_done()

    def stop(self):
        self._stop_event.set()
        self.thread.join()
