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
            identifier = (
                payload.get("id") or payload.get("name") or payload.get("identifier")
            )
            value = payload.get("value")

            if identifier and value is not None:
                with self._registry_lock:
                    for sensor_name, sensor in self.sensor_registry.items():
                        if (
                            identifier == sensor.name
                            or identifier.lower() in sensor.name.lower()
                            or sensor.name.lower() in identifier.lower()
                        ):
                            sensor.update_value(value)
                            logger.debug(
                                f"UDP Client Object: Matched identifier '{identifier}' to sensor '{sensor.name}', updated value to {value}"
                            )
                            return sensor_name

                logger.debug(
                    f"UDP Client Object: No sensor match for identifier '{identifier}'"
                )

            return None
        except json.JSONDecodeError:
            # Handle PRESSURE_SENSOR_X_VALUE format: PRESSURE_SENSOR_1_VALUE:123.456|TC1|TC Gauge 1|123.46 mTorr
            if data.startswith("PRESSURE_SENSOR_") and "_VALUE:" in data:
                try:
                    # Extract sensor ID from format: PRESSURE_SENSOR_1_VALUE:...
                    sensor_id_match = data.split("_VALUE:")[0].replace("PRESSURE_SENSOR_", "")
                    sensor_id = int(sensor_id_match)
                    sensor_key = f"pressure_sensor_{sensor_id}"
                    
                    # Parse the value part: 123.456|TC1|TC Gauge 1|0.050000 Torr
                    value_part = data.split("_VALUE:")[1]
                    parts = value_part.split("|")
                    pressure_value = float(parts[0])  # First part is numeric value in mTorr
                    
                    # Get formatted value (last part should have units)
                    if len(parts) >= 4:
                        formatted_value = parts[3]  # Last part is formatted string with units
                    elif len(parts) >= 1:
                        # Fallback: convert mTorr to Torr and add units
                        pressure_torr = pressure_value / 1000.0
                        formatted_value = f"{pressure_torr:.6f} Torr"
                    else:
                        formatted_value = "---"
                    
                    # Ensure units are present
                    if "Torr" not in formatted_value and "mTorr" not in formatted_value and formatted_value != "---":
                        # If no units found, assume it's in mTorr and convert to Torr
                        try:
                            pressure_torr = float(formatted_value) / 1000.0
                            formatted_value = f"{pressure_torr:.6f} Torr"
                        except (ValueError, TypeError):
                            formatted_value = f"{pressure_value / 1000.0:.6f} Torr"
                    
                    with self._registry_lock:
                        sensor = self.sensor_registry.get(sensor_key)
                        if sensor:
                            # Store the formatted value string for display
                            sensor.update_value(formatted_value)
                            logger.debug(
                                f"UDP Client Object: Matched PRESSURE_SENSOR_{sensor_id} to sensor '{sensor.name}', updated value to {formatted_value}"
                            )
                            return sensor_key
                except (ValueError, IndexError) as e:
                    logger.debug(f"UDP Client Object: Error parsing PRESSURE_SENSOR format: {e}")
            
            # Handle simple "identifier:value" format
            if ":" in data:
                parts = data.split(":", 1)
                if len(parts) == 2:
                    identifier = parts[0].strip()
                    try:
                        value = float(parts[1].strip())
                        with self._registry_lock:
                            for sensor_name, sensor in self.sensor_registry.items():
                                if (
                                    identifier == sensor.name
                                    or identifier.lower() in sensor.name.lower()
                                    or sensor.name.lower() in identifier.lower()
                                ):
                                    sensor.update_value(value)
                                    logger.debug(
                                        f"UDP Client Object: Matched identifier '{identifier}' to sensor '{sensor.name}', updated value to {value}"
                                    )
                                    return sensor_name
                    except ValueError:
                        pass

            logger.debug(f"UDP Client Object: Could not parse data: {data}")
            return None
        except Exception as e:
            logger.error(f"UDP Client Object error processing data: {e}")
            return None
