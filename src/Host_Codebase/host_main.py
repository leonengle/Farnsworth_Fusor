#!/usr/bin/env python3
import customtkinter as ctk
import time
import argparse
import logging
import signal
import sys
import atexit
import json
from enum import Enum, auto
from tcp_command_client import TCPCommandClient
from tcp_data_client import TCPDataClient
from udp_status_client import UDPStatusClient, UDPStatusReceiver
from command_handler import CommandHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HostMain")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class FusorComponent:
    def __init__(self, name: str, tcp_client: TCPCommandClient, component_map: dict = None):
        self.name = name
        self.tcp_client = tcp_client
        self.component_map = component_map or {}

    def _send_target_command(self, command: str):
        if not self.tcp_client.is_connected():
            if not self.tcp_client.connect():
                logger.error("Failed to connect to target for command: %s", command)
                return
        response = self.tcp_client.send_command(command)
        if response:
            logger.info("Command '%s' -> Response: %s", command, response)

    def setDigitalValue(self, command: bool):
        component_type = self.component_map.get(self.name, {}).get("type")
        if component_type == "valve":
            valve_id = self.component_map.get(self.name, {}).get("valve_id", 1)
            position = 100 if command else 0
            self._send_target_command(f"SET_VALVE{valve_id}:{position}")
        elif component_type == "power_supply":
            cmd = "POWER_SUPPLY_ENABLE" if command else "POWER_SUPPLY_DISABLE"
            self._send_target_command(cmd)
        elif component_type == "mechanical_pump":
            power = 100 if command else 0
            self._send_target_command(f"SET_MECHANICAL_PUMP:{power}")
        elif component_type == "turbo_pump":
            power = 100 if command else 0
            self._send_target_command(f"SET_TURBO_PUMP:{power}")

    def setAnalogValue(self, command: float):
        component_type = self.component_map.get(self.name, {}).get("type")
        if component_type == "power_supply":
            self._send_target_command(f"SET_VOLTAGE:{command}")
        elif component_type == "valve":
            valve_id = self.component_map.get(self.name, {}).get("valve_id", 1)
            position = int(command)
            position = max(0, min(position, 100))
            self._send_target_command(f"SET_VALVE{valve_id}:{position}")
        elif component_type == "mechanical_pump":
            power = int(command)
            power = max(0, min(power, 100))
            self._send_target_command(f"SET_MECHANICAL_PUMP:{power}")
        elif component_type == "turbo_pump":
            power = int(command)
            power = max(0, min(power, 100))
            self._send_target_command(f"SET_TURBO_PUMP:{power}")


class State(Enum):
    ALL_OFF = auto()
    ROUGH_PUMP_DOWN = auto()
    RP_DOWN_TURBO = auto()
    TURBO_PUMP_DOWN = auto()
    TP_DOWN_MAIN = auto()
    SETTLE_STEADY_PRESSURE = auto()
    SETTLING_10KV = auto()
    ADMIT_FUEL_TO_5MA = auto()
    NOMINAL_27KV = auto()
    DEENERGIZING = auto()
    CLOSING_MAIN = auto()
    VENTING_FORELINE = auto()


class Event(Enum):
    START = auto()
    APS_FORELINE_LT_100MT = auto()
    APS_TURBO_LT_100MT = auto()
    APS_TURBO_LT_0_1MT = auto()
    APS_MAIN_LT_0_1MT = auto()
    APS_MAIN_EQ_0_1_STEADY = auto()
    STEADY_STATE_VOLTAGE = auto()
    STEADY_STATE_CURRENT = auto()
    STOP_CMD = auto()
    ZERO_KV_STEADY = auto()
    TIMEOUT_5S = auto()
    APS_EQ_1_ATM = auto()
    FAULT_FORELINE_TURBO = auto()
    FAULT_MAIN_TURBO = auto()


class AutoController:
    def __init__(self, components, state_callback=None, log_callback=None):
        self.components = components
        self.currentState = State.ALL_OFF
        self.state_callback = state_callback
        self.log_callback = log_callback

        self.FSM = {
            (State.ALL_OFF, Event.START): State.ROUGH_PUMP_DOWN,
            (State.ROUGH_PUMP_DOWN, Event.APS_FORELINE_LT_100MT): State.RP_DOWN_TURBO,
            (State.RP_DOWN_TURBO, Event.APS_TURBO_LT_100MT): State.TURBO_PUMP_DOWN,
            (State.RP_DOWN_TURBO, Event.FAULT_FORELINE_TURBO): State.ALL_OFF,
            (State.TURBO_PUMP_DOWN, Event.APS_TURBO_LT_0_1MT): State.TP_DOWN_MAIN,
            (State.TP_DOWN_MAIN, Event.APS_MAIN_LT_0_1MT): State.SETTLE_STEADY_PRESSURE,
            (State.TP_DOWN_MAIN, Event.FAULT_MAIN_TURBO): State.ALL_OFF,
            (State.SETTLE_STEADY_PRESSURE, Event.APS_MAIN_EQ_0_1_STEADY): State.SETTLING_10KV,
            (State.SETTLING_10KV, Event.STEADY_STATE_VOLTAGE): State.ADMIT_FUEL_TO_5MA,
            (State.ADMIT_FUEL_TO_5MA, Event.STEADY_STATE_CURRENT): State.NOMINAL_27KV,
            (State.NOMINAL_27KV, Event.STOP_CMD): State.DEENERGIZING,
            (State.DEENERGIZING, Event.ZERO_KV_STEADY): State.CLOSING_MAIN,
            (State.CLOSING_MAIN, Event.TIMEOUT_5S): State.VENTING_FORELINE,
            (State.VENTING_FORELINE, Event.APS_EQ_1_ATM): State.ALL_OFF,
        }

        self._state_entry_actions = {
            State.ALL_OFF: self._enter_all_off,
            State.ROUGH_PUMP_DOWN: self._enter_rough_pump_down,
            State.RP_DOWN_TURBO: self._enter_rp_down_turbo,
            State.TURBO_PUMP_DOWN: self._enter_turbo_pump_down,
            State.TP_DOWN_MAIN: self._enter_tp_down_main,
            State.SETTLE_STEADY_PRESSURE: self._enter_settle_steady_pressure,
            State.SETTLING_10KV: self._enter_settling_10kv,
            State.ADMIT_FUEL_TO_5MA: self._enter_admit_fuel_5ma,
            State.NOMINAL_27KV: self._enter_nominal_27kv,
            State.DEENERGIZING: self._enter_deenergizing,
            State.CLOSING_MAIN: self._enter_closing_main,
            State.VENTING_FORELINE: self._enter_venting_foreline,
        }

        self._enter_state(State.ALL_OFF)

    def _log(self, message):
        if self.log_callback:
            self.log_callback(message)
        logger.info(message)

    def _set_voltage_kv(self, kv: float):
        self.components["power_supply"].setAnalogValue(kv * 1000.0)

    def dispatch_event(self, event: Event):
        key = (self.currentState, event)
        next_state = self.FSM.get(key)
        if next_state is None:
            self._log(f"No transition for {event.name} in {self.currentState.name}")
            return
        self._enter_state(next_state)

    def _enter_state(self, new_state: State):
        self._log(f"Entering state {new_state.name}")
        self.currentState = new_state
        action = self._state_entry_actions.get(new_state)
        if action:
            action()
        if self.state_callback:
            self.state_callback(new_state)

    def _enter_all_off(self):
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(False)
        c["turbo_pump"].setDigitalValue(False)
        c["foreline_valve"].setDigitalValue(False)
        c["fusor_valve"].setDigitalValue(False)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_rough_pump_down(self):
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(False)
        c["foreline_valve"].setDigitalValue(False)
        c["fusor_valve"].setDigitalValue(False)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_rp_down_turbo(self):
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(False)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(False)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_turbo_pump_down(self):
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(False)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_tp_down_main(self):
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_settle_steady_pressure(self):
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(True)
        self._set_voltage_kv(0)

    def _enter_settling_10kv(self):
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(True)
        self._set_voltage_kv(10)

    def _enter_admit_fuel_5ma(self):
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(True)
        self._set_voltage_kv(10)

    def _enter_nominal_27kv(self):
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(True)
        self._set_voltage_kv(27)

    def _enter_deenergizing(self):
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_closing_main(self):
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(False)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_venting_foreline(self):
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)


class TelemetryToEventMapper:
    def __init__(self, controller: AutoController):
        self.controller = controller

    def handle_telemetry(self, telemetry: dict):
        aps_loc = telemetry.get("APS_location")
        aps_p = telemetry.get("APS_pressure_mT")
        v_kv = telemetry.get("voltage_kV")
        i_mA = telemetry.get("current_mA")
        aps_atm_flag = telemetry.get("APS_atm_flag", False)
        s = self.controller.currentState

        if s == State.ROUGH_PUMP_DOWN and aps_loc == "Foreline" and aps_p is not None:
            if aps_p < 100.0:
                self.controller.dispatch_event(Event.APS_FORELINE_LT_100MT)

        if s == State.RP_DOWN_TURBO and aps_loc == "Turbo" and aps_p is not None:
            if aps_p < 100.0:
                self.controller.dispatch_event(Event.APS_TURBO_LT_100MT)

        if s == State.TURBO_PUMP_DOWN and aps_loc == "Turbo" and aps_p is not None:
            if aps_p < 0.1:
                self.controller.dispatch_event(Event.APS_TURBO_LT_0_1MT)

        if s == State.TP_DOWN_MAIN and aps_loc == "Main" and aps_p is not None:
            if aps_p < 0.1:
                self.controller.dispatch_event(Event.APS_MAIN_LT_0_1MT)

        if s == State.SETTLE_STEADY_PRESSURE and aps_loc == "Main" and aps_p is not None:
            if 0.095 <= aps_p <= 0.105:
                self.controller.dispatch_event(Event.APS_MAIN_EQ_0_1_STEADY)

        if s == State.SETTLING_10KV and v_kv is not None:
            if 9.8 <= v_kv <= 10.2:
                self.controller.dispatch_event(Event.STEADY_STATE_VOLTAGE)

        if s == State.ADMIT_FUEL_TO_5MA and i_mA is not None:
            if 4.8 <= i_mA <= 5.2:
                self.controller.dispatch_event(Event.STEADY_STATE_CURRENT)

        if s == State.DEENERGIZING and v_kv is not None:
            if abs(v_kv) < 0.1:
                self.controller.dispatch_event(Event.ZERO_KV_STEADY)

        if s == State.VENTING_FORELINE and aps_atm_flag:
            self.controller.dispatch_event(Event.APS_EQ_1_ATM)


class FusorHostApp:
    def __init__(
        self,
        target_ip: str = "192.168.0.2",
        target_tcp_command_port: int = 2222,
        tcp_data_port: int = 12345,
        udp_status_port: int = 8888,
    ):
        self.target_ip = target_ip
        self.target_tcp_command_port = target_tcp_command_port
        self.tcp_data_port = tcp_data_port
        self.udp_status_port = udp_status_port

        self.command_handler = CommandHandler()

        self.tcp_command_client = TCPCommandClient(target_ip, target_tcp_command_port)

        self.tcp_data_client = TCPDataClient(
            target_ip=target_ip,
            target_port=tcp_data_port,
            data_callback=self._handle_tcp_data,
        )

        self.udp_status_client = UDPStatusClient(target_ip, 8889)
        self.udp_status_receiver = UDPStatusReceiver(
            udp_status_port, self._handle_udp_status
        )

        component_map = {
            "Main Supply": {"type": "power_supply"},
            "Atm Depressure Valve": {"type": "valve", "valve_id": 1},
            "Foreline Valve": {"type": "valve", "valve_id": 2},
            "Vacuum System Valve": {"type": "valve", "valve_id": 3},
            "Roughing Pump": {"type": "mechanical_pump"},
            "Turbo Pump": {"type": "turbo_pump"},
            "Deuterium Supply Valve": {"type": "valve", "valve_id": 4},
        }

        self.components = {
            "power_supply": FusorComponent("Main Supply", self.tcp_command_client, component_map),
            "atm_valve": FusorComponent("Atm Depressure Valve", self.tcp_command_client, component_map),
            "foreline_valve": FusorComponent("Foreline Valve", self.tcp_command_client, component_map),
            "fusor_valve": FusorComponent("Vacuum System Valve", self.tcp_command_client, component_map),
            "mech_pump": FusorComponent("Roughing Pump", self.tcp_command_client, component_map),
            "turbo_pump": FusorComponent("Turbo Pump", self.tcp_command_client, component_map),
            "deuterium_valve": FusorComponent("Deuterium Supply Valve", self.tcp_command_client, component_map),
        }

        self.auto_controller = AutoController(
            self.components,
            state_callback=self._auto_update_state_label,
            log_callback=self._auto_log_event,
        )
        self.telemetry_mapper = TelemetryToEventMapper(self.auto_controller)

        self.root = None
        self.data_display = None
        self.status_label = None
        self.voltage_scale = None
        self.pump_power_scale = None
        self.manual_mech_slider = None
        self.manual_mech_label = None
        self.pressure_label = None
        self.auto_state_label = None
        self.auto_log_display = None

        self._setup_ui()

        if not self.tcp_command_client.connect():
            self._update_status("Failed to connect to target on startup", "red")
            self._update_data_display(
                "[ERROR] Failed to connect to target - check network connection"
            )
        else:
            self._update_status("Connected to target", "green")
            self._update_data_display("[System] Connected to target successfully")

        self.tcp_data_client.start()

        self.udp_status_client.start()
        self.udp_status_receiver.start()

    def _setup_ui(self):
        self.root = ctk.CTk()
        self.root.title("Farnsworth Fusor Control Panel")
        self.root.geometry("1100x800")

        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        title_label = ctk.CTkLabel(
            main_frame,
            text="Farnsworth Fusor Control Panel (Manual + FSM)",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title_label.pack(pady=10)

        self.tabview = ctk.CTkTabview(main_frame)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        manual_tab = self.tabview.add("Manual Control")
        auto_tab = self.tabview.add("Auto / FSM")

        manual_header = ctk.CTkLabel(
            manual_tab,
            text="Manual Controls & Telemetry",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        manual_header.pack(pady=5)

        slider_frame = ctk.CTkFrame(manual_tab)
        slider_frame.pack(fill="x", padx=10, pady=5)

        self.manual_mech_slider = ctk.CTkSlider(
            slider_frame, from_=0.0, to=100.0, command=self._manual_slider_change
        )
        self.manual_mech_slider.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        self.manual_mech_slider.set(0)
        self.manual_mech_label = ctk.CTkLabel(
            slider_frame, text="Mechanical Pump (Live %): 0"
        )
        self.manual_mech_label.pack(side="left", padx=10)

        self.pressure_label = ctk.CTkLabel(
            manual_tab,
            text="Pressure Sensor 1: --- mT",
            font=ctk.CTkFont(size=14),
        )
        self.pressure_label.pack(pady=5)

        led_frame = ctk.CTkFrame(manual_tab)
        led_frame.pack(fill="x", padx=10, pady=5)

        led_label = ctk.CTkLabel(led_frame, text="LED Control", font=ctk.CTkFont(size=14, weight="bold"))
        led_label.pack(pady=5)

        led_button_frame = ctk.CTkFrame(led_frame)
        led_button_frame.pack(pady=5)

        led_on_button = ctk.CTkButton(
            led_button_frame,
            text="LED ON",
            command=lambda: self._send_command("LED_ON"),
            font=ctk.CTkFont(size=14),
            width=150,
            height=40,
            fg_color="green",
            hover_color="darkgreen",
        )
        led_on_button.pack(side="left", padx=10, pady=10)

        led_off_button = ctk.CTkButton(
            led_button_frame,
            text="LED OFF",
            command=lambda: self._send_command("LED_OFF"),
            font=ctk.CTkFont(size=14),
            width=150,
            height=40,
            fg_color="red",
            hover_color="darkred",
        )
        led_off_button.pack(side="left", padx=10, pady=10)

        power_frame = ctk.CTkFrame(manual_tab)
        power_frame.pack(fill="x", padx=10, pady=5)

        power_label = ctk.CTkLabel(power_frame, text="Power Control", font=ctk.CTkFont(size=14, weight="bold"))
        power_label.pack(pady=5)

        power_control_frame = ctk.CTkFrame(power_frame)
        power_control_frame.pack(pady=5)

        voltage_label = ctk.CTkLabel(
            power_control_frame, text="Desired Voltage (V):", font=ctk.CTkFont(size=12)
        )
        voltage_label.pack(side="left", padx=5)

        self.voltage_value_label = ctk.CTkLabel(
            power_control_frame, text="0", font=ctk.CTkFont(size=12), width=60
        )
        self.voltage_value_label.pack(side="left", padx=5)

        self.voltage_scale = ctk.CTkSlider(
            power_control_frame,
            from_=0,
            to=28000,
            width=300,
            command=self._update_voltage_label,
        )
        self.voltage_scale.pack(side="left", padx=5)

        voltage_button = ctk.CTkButton(
            power_control_frame,
            text="Set Voltage",
            command=self._set_voltage,
            font=ctk.CTkFont(size=12),
            width=120,
        )
        voltage_button.pack(side="left", padx=5)

        vacuum_frame = ctk.CTkFrame(manual_tab)
        vacuum_frame.pack(fill="x", padx=10, pady=5)

        vacuum_label = ctk.CTkLabel(
            vacuum_frame,
            text="Vacuum Control",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        vacuum_label.pack(pady=5)

        vacuum_control_frame = ctk.CTkFrame(vacuum_frame)
        vacuum_control_frame.pack(pady=5)

        pump_label = ctk.CTkLabel(
            vacuum_control_frame, text="Pump Power (%):", font=ctk.CTkFont(size=12)
        )
        pump_label.pack(side="left", padx=5)

        self.pump_value_label = ctk.CTkLabel(
            vacuum_control_frame, text="0", font=ctk.CTkFont(size=12), width=60
        )
        self.pump_value_label.pack(side="left", padx=5)

        self.pump_power_scale = ctk.CTkSlider(
            vacuum_control_frame,
            from_=0,
            to=100,
            width=300,
            command=self._update_pump_label,
        )
        self.pump_power_scale.pack(side="left", padx=5)

        pump_button = ctk.CTkButton(
            vacuum_control_frame,
            text="Set Pump Power",
            command=self._set_pump_power,
            font=ctk.CTkFont(size=12),
            width=120,
        )
        pump_button.pack(side="left", padx=5)

        motor_frame = ctk.CTkFrame(manual_tab)
        motor_frame.pack(fill="x", padx=10, pady=5)

        motor_label = ctk.CTkLabel(
            motor_frame, text="Motor Control", font=ctk.CTkFont(size=14, weight="bold")
        )
        motor_label.pack(pady=5)

        motor_control_frame = ctk.CTkFrame(motor_frame)
        motor_control_frame.pack(pady=5)

        steps_label = ctk.CTkLabel(
            motor_control_frame, text="Steps:", font=ctk.CTkFont(size=12)
        )
        steps_label.pack(side="left", padx=5)

        self.steps_entry = ctk.CTkEntry(
            motor_control_frame, width=100, font=ctk.CTkFont(size=12)
        )
        self.steps_entry.pack(side="left", padx=5)
        self.steps_entry.insert(0, "100")

        motor_button = ctk.CTkButton(
            motor_control_frame,
            text="Move Motor",
            command=self._move_motor,
            font=ctk.CTkFont(size=12),
            width=120,
        )
        motor_button.pack(side="left", padx=5)

        read_frame = ctk.CTkFrame(manual_tab)
        read_frame.pack(fill="x", padx=10, pady=5)

        read_label = ctk.CTkLabel(
            read_frame, text="Read Data", font=ctk.CTkFont(size=14, weight="bold")
        )
        read_label.pack(pady=5)

        read_button_frame = ctk.CTkFrame(read_frame)
        read_button_frame.pack(pady=5)

        read_input_button = ctk.CTkButton(
            read_button_frame,
            text="Read GPIO Input",
            command=lambda: self._send_command(
                self.command_handler.build_read_input_command()
            ),
            font=ctk.CTkFont(size=12),
            width=150,
        )
        read_input_button.pack(side="left", padx=5)

        read_adc_button = ctk.CTkButton(
            read_button_frame,
            text="Read ADC",
            command=lambda: self._send_command(
                self.command_handler.build_read_adc_command()
            ),
            font=ctk.CTkFont(size=12),
            width=150,
        )
        read_adc_button.pack(side="left", padx=5)

        data_frame = ctk.CTkFrame(manual_tab)
        data_frame.pack(fill="both", expand=True, padx=10, pady=5)

        data_label = ctk.CTkLabel(
            data_frame,
            text="Data Display (Read-Only from Target)",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        data_label.pack(pady=5)

        # Text display with built-in scrolling
        self.data_display = ctk.CTkTextbox(
            data_frame,
            font=ctk.CTkFont(size=11, family="Courier"),
            wrap="word",
            height=200,
        )
        self.data_display.pack(fill="both", expand=True, padx=5, pady=5)

        auto_section = ctk.CTkFrame(auto_tab)
        auto_section.pack(fill="both", expand=True, padx=10, pady=10)

        auto_header = ctk.CTkLabel(
            auto_section,
            text="Finite State Machine Control",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        auto_header.pack(pady=5)

        auto_button_frame = ctk.CTkFrame(auto_section)
        auto_button_frame.pack(pady=5)

        auto_start = ctk.CTkButton(
            auto_button_frame, text="Start Auto Sequence", command=self._auto_start, width=180
        )
        auto_start.pack(side="left", padx=5, pady=5)

        auto_stop = ctk.CTkButton(
            auto_button_frame, text="Stop / Emergency", command=self._auto_stop, width=180, fg_color="red"
        )
        auto_stop.pack(side="left", padx=5, pady=5)

        self.auto_state_label = ctk.CTkLabel(
            auto_section,
            text="Current State: ALL_OFF",
            font=ctk.CTkFont(size=16),
        )
        self.auto_state_label.pack(pady=10)

        self.auto_log_display = ctk.CTkTextbox(
            auto_section,
            font=ctk.CTkFont(size=11, family="Courier"),
            wrap="word",
            height=300,
        )
        self.auto_log_display.pack(fill="both", expand=True, padx=10, pady=10)
        self.auto_log_display.insert("end", "[FSM] Ready.\n")
        self.auto_log_display.configure(state="disabled")

        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Ready - Waiting for commands",
            font=ctk.CTkFont(size=12),
            text_color="blue",
        )
        self.status_label.pack(pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _send_command(self, command: str):
        if not command:
            logger.warning("Attempted to send empty command")
            return

        try:
            # Ensure connected - try to connect if not connected
            if not self.tcp_command_client.is_connected():
                self._update_status(
                    f"Connecting to {self.target_ip}:{self.target_tcp_command_port}...",
                    "blue",
                )
                self._update_data_display(
                    f"[System] Attempting to connect to target at {self.target_ip}:{self.target_tcp_command_port}"
                )

                if not self.tcp_command_client.connect():
                    self._update_status(
                        f"Failed to connect to {self.target_ip}:{self.target_tcp_command_port}",
                        "red",
                    )
                    self._update_data_display(
                        f"[ERROR] Cannot send command {command} - connection failed"
                    )
                    self._update_data_display(f"[TROUBLESHOOTING] Check:")
                    self._update_data_display(
                        f"  - Is target running? (python src/Target_Codebase/target_main.py)"
                    )
                    self._update_data_display(
                        f"  - Is target IP correct? (Expected: {self.target_ip})"
                    )
                    self._update_data_display(
                        f"  - Can you ping target? (ping {self.target_ip})"
                    )
                    self._update_data_display(
                        f"  - Is firewall blocking port {self.target_tcp_command_port}?"
                    )
                    return

            # Send command
            self._update_status(f"Sending command: {command}...", "blue")
            response = self.tcp_command_client.send_command(command)

            # Display response
            if response:
                self._update_status(
                    f"Command sent: {command} - Response: {response}", "green"
                )
                self._update_data_display(
                    f"[COMMAND] {command} -> [RESPONSE] {response}"
                )
            else:
                self._update_status(f"Command sent: {command} - No response", "yellow")
                self._update_data_display(
                    f"[COMMAND] {command} -> [RESPONSE] (no response)"
                )

        except Exception as e:
            logger.error(f"Error sending command {command}: {e}")
            self._update_status(f"Error sending command: {e}", "red")
            self._update_data_display(f"[ERROR] Command {command} failed: {e}")

    def _update_voltage_label(self, value):
        self.voltage_value_label.configure(text=str(int(value)))

    def _update_pump_label(self, value):
        self.pump_value_label.configure(text=f"{int(value)}%")

    def _manual_slider_change(self, value):
        if self.manual_mech_label:
            self.manual_mech_label.configure(text=f"Mechanical Pump (Live %): {int(value)}")
        component = self.components.get("mech_pump")
        if component:
            component.setAnalogValue(value)

    def _update_pressure_display(self, value):
        if self.pressure_label:
            self.pressure_label.configure(text=f"Pressure Sensor 1: {value} mT")

    def _auto_start(self):
        if self.auto_log_display:
            self.auto_log_display.configure(state="normal")
            self.auto_log_display.insert("end", "[FSM] Start requested\n")
            self.auto_log_display.configure(state="disabled")
        self.auto_controller.dispatch_event(Event.START)

    def _auto_stop(self):
        if self.auto_log_display:
            self.auto_log_display.configure(state="normal")
            self.auto_log_display.insert("end", "[FSM] Stop requested\n")
            self.auto_log_display.configure(state="disabled")
        self.auto_controller.dispatch_event(Event.STOP_CMD)

    def _auto_update_state_label(self, state: State):
        if self.auto_state_label:
            self.auto_state_label.configure(text=f"Current State: {state.name}")

    def _auto_log_event(self, message: str):
        if not self.auto_log_display:
            return
        timestamp = time.strftime("%H:%M:%S")
        self.auto_log_display.configure(state="normal")
        self.auto_log_display.insert("end", f"[{timestamp}] {message}\n")
        self.auto_log_display.see("end")
        self.auto_log_display.configure(state="disabled")

    def _set_voltage(self):
        voltage = int(self.voltage_scale.get())
        command = self.command_handler.build_set_voltage_command(voltage)
        if command:
            self._send_command(command)
        else:
            self._update_status("Invalid voltage value", "red")
            self._update_data_display(f"[ERROR] Invalid voltage: {voltage}")

    def _set_pump_power(self):
        power = int(self.pump_power_scale.get())
        command = self.command_handler.build_set_pump_power_command(power)
        if command:
            self._send_command(command)
        else:
            self._update_status("Invalid power value", "red")
            self._update_data_display(f"[ERROR] Invalid power: {power}")

    def _move_motor(self):
        try:
            steps = int(self.steps_entry.get())
            command = self.command_handler.build_move_motor_command(steps)
            if command:
                self._send_command(command)
            else:
                self._update_status("Invalid steps value", "red")
                self._update_data_display("[ERROR] Steps must be a number")
        except ValueError:
            self._update_status("Invalid steps value", "red")
            self._update_data_display("[ERROR] Steps must be a number")

    def _handle_tcp_data(self, data: str):
        self._update_data_display(f"[TCP Data] {data}")

    def _handle_udp_status(self, message: str, address: tuple):
        self._update_data_display(f"[UDP Status] From {address[0]}: {message}")
        try:
            payload = json.loads(message)
            identifier = payload.get("id")
            value = payload.get("value")
            if identifier == "Pressure Sensor 1" and value is not None:
                self._update_pressure_display(value)
            telemetry = payload.get("telemetry")
            if telemetry:
                self.telemetry_mapper.handle_telemetry(telemetry)
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.error("Error parsing UDP status message: %s", exc)

    def _update_data_display(self, data: str):
        if not self.data_display or not self.root:
            return
        try:
            timestamp = time.strftime("%H:%M:%S")
            self.data_display.insert("end", f"{timestamp} - {data}\n")
            # Auto-scroll to bottom
            self.data_display.see("end")
        except Exception:
            pass

    def _update_status(self, message: str, color: str = "white"):
        if not self.status_label or not self.root:
            return
        try:
            self.status_label.configure(text=message, text_color=color)
        except Exception:
            pass

    def _on_closing(self):
        # Send LED_OFF command before shutting down
        self._turn_off_led()
        # Destroy root first to prevent UI update errors
        if self.root:
            try:
                self.root.destroy()
            except:
                pass
        self.stop()

    def _turn_off_led(self):
        # Try to send LED_OFF command - attempt multiple times if needed
        try:
            # Try to connect if not connected
            if not self.tcp_command_client.is_connected():
                self.tcp_command_client.connect()

            # Send LED_OFF command
            if self.tcp_command_client.is_connected():
                self.tcp_command_client.send_command("LED_OFF")
                if self.data_display and self.root:
                    self._update_data_display("[System] LED turned OFF during shutdown")
            else:
                if self.data_display and self.root:
                    self._update_data_display(
                        "[WARNING] Could not connect to turn off LED"
                    )
        except Exception as e:
            if self.data_display and self.root:
                try:
                    self._update_data_display(f"[ERROR] Could not turn off LED: {e}")
                except:
                    pass
            # Try one more time
            try:
                if self.tcp_command_client.connect():
                    self.tcp_command_client.send_command("LED_OFF")
            except:
                pass

    def run(self):
        print("Fusor Host Application starting...")
        print(f"Target IP: {self.target_ip}:{self.target_tcp_command_port}")
        print(f"TCP Data Port: {self.tcp_data_port}")
        print(f"UDP Status Port: {self.udp_status_port}")
        print("\nControl panel opening...")
        print("All buttons send commands to target.")
        print("Target listens, takes action, and sends read-only data back.")

        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"\nUnexpected error: {e}")
        finally:
            # Always try to turn off LED before stopping
            self._turn_off_led()
            self.stop()

    def stop(self):
        # Try to turn off LED before disconnecting
        try:
            self._turn_off_led()
        except Exception as e:
            logger.error(f"Error turning off LED in stop: {e}")

        # Disconnect TCP command client
        try:
            self.tcp_command_client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting TCP client: {e}")

        # Stop TCP data client
        try:
            self.tcp_data_client.stop()
        except Exception as e:
            logger.error(f"Error stopping TCP data client: {e}")

        # Stop UDP status communication
        try:
            self.udp_status_client.stop()
            self.udp_status_receiver.stop()
        except Exception as e:
            logger.error(f"Error stopping UDP communication: {e}")


# Global app instance for signal handler access
_app_instance = None


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    if _app_instance:
        try:
            _app_instance._turn_off_led()
            _app_instance.stop()
        except Exception as e:
            logger.error(f"Error during signal handler shutdown: {e}")
    sys.exit(0)


def atexit_handler():
    if _app_instance:
        try:
            _app_instance._turn_off_led()
        except Exception as e:
            logger.error(f"Error during atexit handler: {e}")


def main():
    global _app_instance

    # Set up signal handlers for graceful shutdown
    try:
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, signal_handler)
    except Exception as e:
        logger.warning(f"Could not set up signal handlers: {e}")

    # Register atexit handler as fallback
    atexit.register(atexit_handler)

    parser = argparse.ArgumentParser(
        description="Fusor Host Application - TCP/UDP Control Panel"
    )
    parser.add_argument(
        "--target-ip",
        default="192.168.0.2",
        help="Target IP address (default: 192.168.0.2)",
    )
    parser.add_argument(
        "--target-tcp-command-port",
        type=int,
        default=2222,
        help="Target TCP command port (default: 2222)",
    )
    parser.add_argument(
        "--tcp-data-port",
        type=int,
        default=12345,
        help="TCP port for receiving data (default: 12345)",
    )
    parser.add_argument(
        "--udp-status-port",
        type=int,
        default=8888,
        help="UDP port for status communication (default: 8888)",
    )

    args = parser.parse_args()

    # Create and run host application - control panel pops up
    app = FusorHostApp(
        target_ip=args.target_ip,
        target_tcp_command_port=args.target_tcp_command_port,
        tcp_data_port=args.tcp_data_port,
        udp_status_port=args.udp_status_port,
    )

    _app_instance = app
    app.run()


if __name__ == "__main__":
    main()
