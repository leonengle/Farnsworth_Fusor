from typing import Optional, Tuple, Dict
from logging_setup import setup_logging, get_logger

setup_logging()
logger = get_logger("ArduinoCommandValidator")


class ArduinoCommandValidator:
    VALID_MOTOR_IDS = [1, 2, 3, 4]
    MIN_MOTOR_STEPS = -10000
    MAX_MOTOR_STEPS = 10000
    MIN_MOTOR_DEGREE = 0.0
    MAX_MOTOR_DEGREE = 360.0
    MIN_MOTOR_SPEED = 0.0
    MAX_MOTOR_SPEED = 100.0
    VALID_DIRECTIONS = ["FORWARD", "BACKWARD", "REVERSE"]

    VALID_ANALOG_LABELS = {
        "POWER_SUPPLY_VOLTAGE_SETPOINT",
        "ATM_DEPRESSURE_VALVE",
        "FORELINE_VALVE",
        "VACUUM_SYSTEM_VALVE",
        "DEUTERIUM_SUPPLY_VALVE",
        "RESERVED_VALVE_5",
        "RESERVED_VALVE_6",
        "ROUGHING_PUMP_POWER",
        "TURBO_PUMP_POWER",
        "LEGACY_PUMP_POWER",
    }

    ANALOG_VALUE_RANGES: Dict[str, Tuple[float, float]] = {
        "POWER_SUPPLY_VOLTAGE_SETPOINT": (0.0, 28000.0),
        "ATM_DEPRESSURE_VALVE": (0.0, 100.0),
        "FORELINE_VALVE": (0.0, 100.0),
        "VACUUM_SYSTEM_VALVE": (0.0, 100.0),
        "DEUTERIUM_SUPPLY_VALVE": (0.0, 100.0),
        "RESERVED_VALVE_5": (0.0, 100.0),
        "RESERVED_VALVE_6": (0.0, 100.0),
        "ROUGHING_PUMP_POWER": (0.0, 100.0),
        "TURBO_PUMP_POWER": (0.0, 100.0),
        "LEGACY_PUMP_POWER": (0.0, 100.0),
    }

    def __init__(self):
        logger.info("Arduino Command Validator initialized")

    @staticmethod
    def map_percentage_to_degree(percentage: float) -> float:
        """
        Maps percentage (0-100) or power level (0-100) to motor degree (0-360).

        Args:
            percentage: Value between 0 and 100 (slider percentage or power level)

        Returns:
            Motor degree value between 0 and 360
        """
        percentage = max(0.0, min(100.0, float(percentage)))
        degree = (percentage / 100.0) * 360.0
        return round(degree, 2)

    def validate_motor_degree_object(
        self, component_name: str, motor_degree: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates a motor command object with component_name and motor_degree.

        Args:
            component_name: Name of the motor component (e.g., "MOTOR_1", "MOTOR_2")
            motor_degree: Motor degree value (0-360)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not component_name or not isinstance(component_name, str):
            return False, "Component name must be a non-empty string"

        try:
            motor_id = None
            if component_name.upper().startswith("MOTOR_"):
                try:
                    motor_id = int(component_name.upper().replace("MOTOR_", ""))
                except ValueError:
                    pass

            if motor_id is None or motor_id not in self.VALID_MOTOR_IDS:
                return (
                    False,
                    f"Invalid component name: {component_name} (must be MOTOR_1, MOTOR_2, MOTOR_3, or MOTOR_4)",
                )

            try:
                degree_float = float(motor_degree)
                if (
                    degree_float < self.MIN_MOTOR_DEGREE
                    or degree_float > self.MAX_MOTOR_DEGREE
                ):
                    return (
                        False,
                        f"Motor degree out of range: {degree_float} (must be {self.MIN_MOTOR_DEGREE} to {self.MAX_MOTOR_DEGREE})",
                    )

                return True, None
            except (ValueError, TypeError):
                return False, f"Invalid motor degree value: {motor_degree}"
        except Exception as e:
            return False, f"Error validating motor degree object: {e}"

    def validate_motor_command(
        self, motor_id: int, command: str, *args
    ) -> Tuple[bool, Optional[str]]:
        if motor_id not in self.VALID_MOTOR_IDS:
            return False, f"Invalid motor ID: {motor_id} (must be 1-4)"

        if command == "MOVE_MOTOR":
            if len(args) < 1:
                return False, "MOVE_MOTOR requires at least steps argument"

            try:
                steps = int(args[0])
                if steps < self.MIN_MOTOR_STEPS or steps > self.MAX_MOTOR_STEPS:
                    return (
                        False,
                        f"Steps out of range: {steps} (must be {self.MIN_MOTOR_STEPS} to {self.MAX_MOTOR_STEPS})",
                    )

                if len(args) > 1:
                    direction = str(args[1]).upper()
                    if direction not in self.VALID_DIRECTIONS:
                        return (
                            False,
                            f"Invalid direction: {direction} (must be FORWARD, BACKWARD, or REVERSE)",
                        )

                return True, None
            except (ValueError, TypeError):
                return False, f"Invalid steps value: {args[0]}"

        elif command == "ENABLE_MOTOR":
            return True, None

        elif command == "DISABLE_MOTOR":
            return True, None

        elif command == "SET_MOTOR_SPEED":
            if len(args) < 1:
                return False, "SET_MOTOR_SPEED requires speed argument"

            try:
                speed = float(args[0])
                if speed < self.MIN_MOTOR_SPEED or speed > self.MAX_MOTOR_SPEED:
                    return (
                        False,
                        f"Speed out of range: {speed} (must be {self.MIN_MOTOR_SPEED} to {self.MAX_MOTOR_SPEED})",
                    )

                return True, None
            except (ValueError, TypeError):
                return False, f"Invalid speed value: {args[0]}"

        else:
            return False, f"Unknown motor command: {command}"

    def validate_analog_command(
        self, label: str, value: float
    ) -> Tuple[bool, Optional[str]]:
        if not label or not isinstance(label, str):
            return False, "Component label must be a non-empty string"

        if label not in self.VALID_ANALOG_LABELS:
            return False, f"Unknown component label: {label}"

        try:
            value_float = float(value)
        except (ValueError, TypeError):
            return False, f"Invalid value type: {value}"

        if label in self.ANALOG_VALUE_RANGES:
            min_val, max_val = self.ANALOG_VALUE_RANGES[label]
            if value_float < min_val or value_float > max_val:
                return (
                    False,
                    f"Value out of range for {label}: {value_float} (must be {min_val} to {max_val})",
                )

        return True, None

    def build_motor_command_string(
        self, motor_id: int, command: str, *args
    ) -> Optional[str]:
        is_valid, error = self.validate_motor_command(motor_id, command, *args)
        if not is_valid:
            logger.error(f"Motor command validation failed: {error}")
            return None

        cmd_parts = [command, str(motor_id)]
        if args:
            cmd_parts.extend(str(arg) for arg in args)

        return ":".join(cmd_parts)

    def build_analog_command_string(self, label: str, value: float) -> Optional[str]:
        is_valid, error = self.validate_analog_command(label, value)
        if not is_valid:
            logger.error(f"Analog command validation failed: {error}")
            return None

        if isinstance(value, float):
            value_str = f"{value:.2f}".rstrip("0").rstrip(".")
            if not value_str:
                value_str = "0"
        else:
            value_str = str(value)

        return f"ANALOG:{label}:{value_str}"
