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
        response = self.tcp_client.send_command(command)

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
        if "valve" in actuator_name.lower():
            valve_id = self._extract_valve_id(actuator_name)
            if valve_id:
                return f"SET_VALVE{valve_id}:{int(value)}"
        elif "power" in actuator_name.lower() or "supply" in actuator_name.lower():
            return f"SET_VOLTAGE:{int(value)}"
        elif "pump" in actuator_name.lower():
            if (
                "mechanical" in actuator_name.lower()
                or "roughing" in actuator_name.lower()
            ):
                return f"SET_MECHANICAL_PUMP:{int(value)}"
            elif "turbo" in actuator_name.lower():
                return f"SET_TURBO_PUMP:{int(value)}"
        return f"SET_VALUE:{actuator_name}:{value}"

    def _extract_valve_id(self, actuator_name: str) -> Optional[int]:
        name_lower = actuator_name.lower()
        if "atm" in name_lower or "depressure" in name_lower:
            return 1
        elif "foreline" in name_lower:
            return 2
        elif "vacuum" in name_lower or "system" in name_lower:
            return 3
        elif "deuterium" in name_lower or "supply" in name_lower:
            return 4
        return None
