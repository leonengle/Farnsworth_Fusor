import threading
import logging

logger = logging.getLogger("SensorObject")


class SensorObject:
    def __init__(self, name: str):
        self.name = name
        self.value = None
        self._value_lock = threading.Lock()

    def update_value(self, value):
        with self._value_lock:
            self.value = value
        logger.debug(f"Sensor {self.name} value updated to: {value}")

