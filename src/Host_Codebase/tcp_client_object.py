from typing import Dict, Optional
from tcp_command_client import TCPCommandClient
import threading
import logging

logger = logging.getLogger("TCPClientObject")


class TCPClientObject:
    def __init__(self, tcp_client: TCPCommandClient):
        self.tcp_client = tcp_client
        self.actuator_registry: Dict[str, Dict] = {}
        self.label_counter = 0
        self._registry_lock = threading.Lock()

    def register_actuator(self, actuator_name: str, actuator_label: str):
        with self._registry_lock:
            label_hex = format(self.label_counter, "04x")
            self.actuator_registry[actuator_name] = {
                "name": actuator_name,
                "label": actuator_label,
                "label_hex": label_hex,
            }
            self.label_counter += 1
            logger.info(
                f"Registered actuator: {actuator_name} with label '{actuator_label}' (hex: {label_hex})"
            )

    def send_actuator_command(
        self, actuator_name: str, actuator_value: float, actuator_label: str
    ):
        with self._registry_lock:
            if actuator_name not in self.actuator_registry:
                label_hex = format(self.label_counter, "04x")
                self.actuator_registry[actuator_name] = {
                    "name": actuator_name,
                    "label": actuator_label,
                    "label_hex": label_hex,
                }
                self.label_counter += 1
                logger.info(
                    f"Registered actuator: {actuator_name} with label '{actuator_label}' (hex: {label_hex})"
                )

            actuator_info = self.actuator_registry[actuator_name]

        if not self.tcp_client.is_connected():
            if not self.tcp_client.connect():
                logger.error(f"Failed to connect for actuator {actuator_name}")
                return None

        command = self._build_command(actuator_name, actuator_value)
        if not command:
            logger.error(f"Cannot build command for actuator {actuator_name} with value {actuator_value}")
            return None
        
        logger.info(f"Sending actuator command: {actuator_name} = {actuator_value} -> {command}")
        response = self.tcp_client.send_command(command)
        
        if response:
            logger.info(f"Actuator command response: {response}")
        else:
            logger.warning(f"No response from target for command: {command}")

        logger.debug(
            f"TCP Client Object: Actuator {actuator_name} (label: {actuator_label}, hex: {actuator_info['label_hex']}) -> value: {actuator_value} -> command: {command} -> response: {response}"
        )

        return {
            "name": actuator_name,
            "value": actuator_value,
            "label": actuator_label,
            "label_hex": actuator_info["label_hex"],
            "response": response,
        }

    def _build_command(self, actuator_name: str, value: float) -> str:
        name_lower = actuator_name.lower()
        if "valve" in name_lower:
            valve_id = self._extract_valve_id(actuator_name)
            if valve_id:
                return f"SET_VALVE{valve_id}:{int(value)}"
            else:
                logger.warning(f"Could not extract valve ID from actuator name: {actuator_name}")
                return None
        elif "power" in name_lower or ("supply" in name_lower and "power" in name_lower):
            return f"SET_VOLTAGE:{int(value)}"
        elif "pump" in name_lower:
            if (
                "mechanical" in name_lower
                or "roughing" in name_lower
            ):
                return f"SET_MECHANICAL_PUMP:{int(value)}"
            elif "turbo" in name_lower:
                return f"SET_TURBO_PUMP:{int(value)}"
        logger.warning(f"Unknown actuator type: {actuator_name}, cannot build command")
        return None

    def _extract_valve_id(self, actuator_name: str) -> Optional[int]:
        name_lower = actuator_name.lower()
        
        # Try to extract valve ID directly from patterns like "valve1", "valve_1", "valve 1"
        import re
        match = re.search(r'valve[_\s]*(\d+)', name_lower)
        if match:
            valve_id = int(match.group(1))
            if 1 <= valve_id <= 6:
                return valve_id
        
        # Fallback to keyword matching
        if "atm" in name_lower or "depressure" in name_lower:
            return 1
        elif "foreline" in name_lower:
            return 2
        elif "vacuum" in name_lower or "system" in name_lower or "fusor" in name_lower:
            return 3
        elif "deuterium" in name_lower or ("supply" in name_lower and "deuterium" in name_lower):
            return 4
        elif "turbo" in name_lower and "valve" in name_lower:
            return 5
        
        return None
