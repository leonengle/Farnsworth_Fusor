import logging
from typing import Optional
from base_classes import CommandBuilderInterface

logger = logging.getLogger("CommandHandler")


class CommandHandler(CommandBuilderInterface):

    @staticmethod
    def build_led_on_command() -> str:
        return "LED_ON"

    @staticmethod
    def build_led_off_command() -> str:
        return "LED_OFF"

    @staticmethod
    def build_set_voltage_command(voltage: int) -> Optional[str]:
        if not isinstance(voltage, int):
            try:
                voltage = int(voltage)
            except (ValueError, TypeError):
                logger.error(f"Invalid voltage type: {type(voltage)}")
                return None

        if voltage < 0 or voltage > 28000:
            logger.warning(f"Voltage out of range: {voltage} (expected 0-28000)")
            return None

        return f"SET_VOLTAGE:{voltage}"

    @staticmethod
    def build_set_pump_power_command(power: int) -> Optional[str]:
        if not isinstance(power, int):
            try:
                power = int(power)
            except (ValueError, TypeError):
                logger.error(f"Invalid power type: {type(power)}")
                return None

        if power < 0 or power > 100:
            logger.warning(f"Power out of range: {power} (expected 0-100)")
            return None

        return f"SET_PUMP_POWER:{power}"

    @staticmethod
    def build_move_motor_command(steps: int) -> Optional[str]:
        if not isinstance(steps, int):
            try:
                steps = int(steps)
            except (ValueError, TypeError):
                logger.error(f"Invalid steps type: {type(steps)}")
                return None

        return f"MOVE_VAR:{steps}"

    @staticmethod
    def build_read_input_command() -> str:
        return "READ_INPUT"

    @staticmethod
    def build_read_adc_command() -> str:
        return "READ_ADC"
