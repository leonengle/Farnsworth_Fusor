from typing import Dict, Optional
from sensor_object import SensorObject
import threading
import json
import logging

logger = logging.getLogger("UDPClientObject")


class UDPClientObject:
    def __init__(self, sensor_registry: Dict[str, SensorObject]):
        self.sensor_registry = sensor_registry
        self._registry_lock = threading.Lock()

    def process_received_data(self, data: str) -> Optional[str]:
        try:
            payload = json.loads(data)
            identifier = payload.get("id") or payload.get("name") or payload.get("identifier")
            value = payload.get("value")
            
            if identifier and value is not None:
                with self._registry_lock:
                    for sensor_name, sensor in self.sensor_registry.items():
                        if identifier == sensor.name or identifier.lower() in sensor.name.lower() or sensor.name.lower() in identifier.lower():
                            sensor.update_value(value)
                            logger.debug(f"UDP Client Object: Matched identifier '{identifier}' to sensor '{sensor.name}', updated value to {value}")
                            return sensor_name
                
                logger.debug(f"UDP Client Object: No sensor match for identifier '{identifier}'")
            
            return None
        except json.JSONDecodeError:
            if ":" in data:
                parts = data.split(":", 1)
                if len(parts) == 2:
                    identifier = parts[0].strip()
                    try:
                        value = float(parts[1].strip())
                        with self._registry_lock:
                            for sensor_name, sensor in self.sensor_registry.items():
                                if identifier == sensor.name or identifier.lower() in sensor.name.lower() or sensor.name.lower() in identifier.lower():
                                    sensor.update_value(value)
                                    logger.debug(f"UDP Client Object: Matched identifier '{identifier}' to sensor '{sensor.name}', updated value to {value}")
                                    return sensor_name
                    except ValueError:
                        pass
            
            logger.debug(f"UDP Client Object: Could not parse data: {data}")
            return None
        except Exception as e:
            logger.error(f"UDP Client Object error processing data: {e}")
            return None

