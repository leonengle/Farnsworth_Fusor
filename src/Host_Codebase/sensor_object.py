import logging

logger = logging.getLogger("SensorObject")


class SensorObject:
    def __init__(self, name: str):
        self.name = name
        self.value = None

    def update_value(self, value):
        self.value = value
        logger.debug(f"Sensor {self.name} value updated to: {value}")

