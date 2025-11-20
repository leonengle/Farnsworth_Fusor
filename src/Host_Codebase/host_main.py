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
from udp_data_client import UDPDataClient
from udp_status_client import UDPStatusClient, UDPStatusReceiver
from command_handler import CommandHandler
from actuator_object import ActuatorObject
from sensor_object import SensorObject
from tcp_client_object import TCPClientObject
from udp_client_object import UDPClientObject

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HostMain")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def _build_actuator_command(actuator_name: str, value: float) -> str:
    if "valve" in actuator_name.lower():
        if "atm" in actuator_name.lower() or "depressure" in actuator_name.lower():
            return f"SET_VALVE1:{int(value)}"
        elif "foreline" in actuator_name.lower():
            return f"SET_VALVE2:{int(value)}"
        elif "vacuum" in actuator_name.lower() or "system" in actuator_name.lower():
            return f"SET_VALVE3:{int(value)}"
        elif "deuterium" in actuator_name.lower() or "supply" in actuator_name.lower():
            return f"SET_VALVE4:{int(value)}"
    elif "power" in actuator_name.lower() or "supply" in actuator_name.lower():
        return f"SET_VOLTAGE:{int(value)}"
    elif "pump" in actuator_name.lower():
        if "mechanical" in actuator_name.lower() or "roughing" in actuator_name.lower():
            return f"SET_MECHANICAL_PUMP:{int(value)}"
        elif "turbo" in actuator_name.lower():
            return f"SET_TURBO_PUMP:{int(value)}"
    return ""


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
    def __init__(self, actuators: dict, sensors: dict = None, state_callback=None, log_callback=None):
        self.actuators = actuators
        self.sensors = sensors or {}
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
        if "power_supply" in self.actuators:
            self.actuators["power_supply"].setAnalogValue(kv * 1000.0)

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
        a = self.actuators
        if "atm_valve" in a:
            a["atm_valve"].setDigitalValue(False)
        if "mech_pump" in a:
            a["mech_pump"].setDigitalValue(False)
        if "turbo_pump" in a:
            a["turbo_pump"].setDigitalValue(False)
        if "foreline_valve" in a:
            a["foreline_valve"].setDigitalValue(False)
        if "fusor_valve" in a:
            a["fusor_valve"].setDigitalValue(False)
        if "deuterium_valve" in a:
            a["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_rough_pump_down(self):
        a = self.actuators
        if "atm_valve" in a:
            a["atm_valve"].setDigitalValue(False)
        if "mech_pump" in a:
            a["mech_pump"].setDigitalValue(True)
        if "turbo_pump" in a:
            a["turbo_pump"].setDigitalValue(False)
        if "foreline_valve" in a:
            a["foreline_valve"].setDigitalValue(False)
        if "fusor_valve" in a:
            a["fusor_valve"].setDigitalValue(False)
        if "deuterium_valve" in a:
            a["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_rp_down_turbo(self):
        a = self.actuators
        if "atm_valve" in a:
            a["atm_valve"].setDigitalValue(False)
        if "mech_pump" in a:
            a["mech_pump"].setDigitalValue(True)
        if "turbo_pump" in a:
            a["turbo_pump"].setDigitalValue(False)
        if "foreline_valve" in a:
            a["foreline_valve"].setDigitalValue(True)
        if "fusor_valve" in a:
            a["fusor_valve"].setDigitalValue(False)
        if "deuterium_valve" in a:
            a["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_turbo_pump_down(self):
        a = self.actuators
        if "atm_valve" in a:
            a["atm_valve"].setDigitalValue(False)
        if "mech_pump" in a:
            a["mech_pump"].setDigitalValue(True)
        if "turbo_pump" in a:
            a["turbo_pump"].setDigitalValue(True)
        if "foreline_valve" in a:
            a["foreline_valve"].setDigitalValue(True)
        if "fusor_valve" in a:
            a["fusor_valve"].setDigitalValue(False)
        if "deuterium_valve" in a:
            a["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_tp_down_main(self):
        a = self.actuators
        if "atm_valve" in a:
            a["atm_valve"].setDigitalValue(False)
        if "mech_pump" in a:
            a["mech_pump"].setDigitalValue(True)
        if "turbo_pump" in a:
            a["turbo_pump"].setDigitalValue(True)
        if "foreline_valve" in a:
            a["foreline_valve"].setDigitalValue(True)
        if "fusor_valve" in a:
            a["fusor_valve"].setDigitalValue(True)
        if "deuterium_valve" in a:
            a["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_settle_steady_pressure(self):
        a = self.actuators
        if "atm_valve" in a:
            a["atm_valve"].setDigitalValue(False)
        if "mech_pump" in a:
            a["mech_pump"].setDigitalValue(True)
        if "turbo_pump" in a:
            a["turbo_pump"].setDigitalValue(True)
        if "foreline_valve" in a:
            a["foreline_valve"].setDigitalValue(True)
        if "fusor_valve" in a:
            a["fusor_valve"].setDigitalValue(True)
        if "deuterium_valve" in a:
            a["deuterium_valve"].setDigitalValue(True)
        self._set_voltage_kv(0)

    def _enter_settling_10kv(self):
        a = self.actuators
        if "atm_valve" in a:
            a["atm_valve"].setDigitalValue(False)
        if "mech_pump" in a:
            a["mech_pump"].setDigitalValue(True)
        if "turbo_pump" in a:
            a["turbo_pump"].setDigitalValue(True)
        if "foreline_valve" in a:
            a["foreline_valve"].setDigitalValue(True)
        if "fusor_valve" in a:
            a["fusor_valve"].setDigitalValue(True)
        if "deuterium_valve" in a:
            a["deuterium_valve"].setDigitalValue(True)
        self._set_voltage_kv(10)

    def _enter_admit_fuel_5ma(self):
        a = self.actuators
        if "atm_valve" in a:
            a["atm_valve"].setDigitalValue(False)
        if "mech_pump" in a:
            a["mech_pump"].setDigitalValue(True)
        if "turbo_pump" in a:
            a["turbo_pump"].setDigitalValue(True)
        if "foreline_valve" in a:
            a["foreline_valve"].setDigitalValue(True)
        if "fusor_valve" in a:
            a["fusor_valve"].setDigitalValue(True)
        if "deuterium_valve" in a:
            a["deuterium_valve"].setDigitalValue(True)
        self._set_voltage_kv(10)

    def _enter_nominal_27kv(self):
        a = self.actuators
        if "atm_valve" in a:
            a["atm_valve"].setDigitalValue(False)
        if "mech_pump" in a:
            a["mech_pump"].setDigitalValue(True)
        if "turbo_pump" in a:
            a["turbo_pump"].setDigitalValue(True)
        if "foreline_valve" in a:
            a["foreline_valve"].setDigitalValue(True)
        if "fusor_valve" in a:
            a["fusor_valve"].setDigitalValue(True)
        if "deuterium_valve" in a:
            a["deuterium_valve"].setDigitalValue(True)
        self._set_voltage_kv(27)

    def _enter_deenergizing(self):
        a = self.actuators
        if "atm_valve" in a:
            a["atm_valve"].setDigitalValue(False)
        if "mech_pump" in a:
            a["mech_pump"].setDigitalValue(True)
        if "turbo_pump" in a:
            a["turbo_pump"].setDigitalValue(True)
        if "foreline_valve" in a:
            a["foreline_valve"].setDigitalValue(True)
        if "fusor_valve" in a:
            a["fusor_valve"].setDigitalValue(True)
        if "deuterium_valve" in a:
            a["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_closing_main(self):
        a = self.actuators
        if "atm_valve" in a:
            a["atm_valve"].setDigitalValue(False)
        if "mech_pump" in a:
            a["mech_pump"].setDigitalValue(True)
        if "turbo_pump" in a:
            a["turbo_pump"].setDigitalValue(True)
        if "foreline_valve" in a:
            a["foreline_valve"].setDigitalValue(True)
        if "fusor_valve" in a:
            a["fusor_valve"].setDigitalValue(False)
        if "deuterium_valve" in a:
            a["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_venting_foreline(self):
        a = self.actuators
        if "atm_valve" in a:
            a["atm_valve"].setDigitalValue(False)
        if "mech_pump" in a:
            a["mech_pump"].setDigitalValue(True)
        if "turbo_pump" in a:
            a["turbo_pump"].setDigitalValue(True)
        if "foreline_valve" in a:
            a["foreline_valve"].setDigitalValue(True)
        if "fusor_valve" in a:
            a["fusor_valve"].setDigitalValue(True)
        if "deuterium_valve" in a:
            a["deuterium_valve"].setDigitalValue(False)
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
        terminal_updates: bool = True,
    ):
        self.target_ip = target_ip
        self.target_tcp_command_port = target_tcp_command_port
        self.tcp_data_port = tcp_data_port
        self.udp_status_port = udp_status_port

        self.command_handler = CommandHandler()

        self.tcp_command_client = TCPCommandClient(target_ip, target_tcp_command_port)

        self.udp_data_client = UDPDataClient(
            target_ip=target_ip,
            target_port=tcp_data_port,
            data_callback=self._handle_udp_data,
        )

        self.udp_status_client = UDPStatusClient(target_ip, 8889)
        self.udp_status_receiver = UDPStatusReceiver(
            udp_status_port, self._handle_udp_status
        )

        self.root = None
        self.data_display = None
        self.status_label = None
        self.voltage_scale = None
        self.pump_power_scale = None
        self.manual_mech_slider = None
        self.manual_mech_label = None
        self.pressure_label = None
        self.adc_label = None
        self.auto_state_label = None
        self.auto_log_display = None
        self.target_snapshot_var = None
        self.target_snapshot_entry = None
        self.terminal_updates_enabled = terminal_updates
        
        # Track previous values to only log changes
        self.previous_values = {}

        self.tcp_client_object = TCPClientObject(self.tcp_command_client)
        
        self.actuators = {
            "power_supply": ActuatorObject("power supply", "power supply", self.tcp_command_client, _build_actuator_command, self.tcp_client_object),
            "atm_valve": ActuatorObject("valve1", "valve1", self.tcp_command_client, _build_actuator_command, self.tcp_client_object),
            "foreline_valve": ActuatorObject("valve 2", "valve 2", self.tcp_command_client, _build_actuator_command, self.tcp_client_object),
            "fusor_valve": ActuatorObject("valve 3", "valve 3", self.tcp_command_client, _build_actuator_command, self.tcp_client_object),
            "mech_pump": ActuatorObject("roughing pump", "roughing pump", self.tcp_command_client, _build_actuator_command, self.tcp_client_object),
            "turbo_pump": ActuatorObject("turbo pump", "turbo pump", self.tcp_command_client, _build_actuator_command, self.tcp_client_object),
            "deuterium_valve": ActuatorObject("valve 4", "valve 4", self.tcp_command_client, _build_actuator_command, self.tcp_client_object),
        }
        
        for actuator_name, actuator in self.actuators.items():
            self.tcp_client_object.register_actuator(actuator.name, actuator.label)
        
        self.sensors = {
            "pressure_sensor_1": SensorObject("pressure sensor 1"),
            "pressure_sensor_2": SensorObject("pressure sensor 2"),
        }
        
        self.udp_client_object = UDPClientObject(self.sensors)

        self.auto_controller = AutoController(
            self.actuators,
            sensors=self.sensors,
            state_callback=self._auto_update_state_label,
            log_callback=self._auto_log_event,
        )
        self.telemetry_mapper = TelemetryToEventMapper(self.auto_controller)

        self._setup_ui()

        if not self.tcp_command_client.connect():
            self._update_status("Failed to connect to target on startup", "red")
            self._update_data_display(
                "[ERROR] Failed to connect to target - check network connection"
            )
        else:
            self._update_status("Connected to target", "green")
            self._update_data_display("[System] Connected to target successfully")

        self.udp_data_client.start()
        logger.info("UDP data client started - receiving telemetry from target...")
        print("UDP data client started - receiving telemetry from target...")

        self.udp_status_client.start()
        self.udp_status_receiver.start()
        logger.info("UDP status receiver started - waiting for status updates from target...")
        print("UDP status receiver started - waiting for status updates from target...")

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

        self.adc_label = ctk.CTkLabel(
            manual_tab,
            text="ADC CH0: ---",
            font=ctk.CTkFont(size=14),
        )
        self.adc_label.pack(pady=5)

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

        snapshot_frame = ctk.CTkFrame(manual_tab)
        snapshot_frame.pack(fill="x", padx=10, pady=5)

        snapshot_label = ctk.CTkLabel(
            snapshot_frame,
            text="Latest Target Message (read-only)",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        snapshot_label.pack(side="left", padx=5)

        self.target_snapshot_var = ctk.StringVar(value="(no data yet)")
        self.target_snapshot_entry = ctk.CTkEntry(
            snapshot_frame,
            textvariable=self.target_snapshot_var,
            state="disabled",
            width=600,
        )
        self.target_snapshot_entry.pack(side="left", padx=5, fill="x", expand=True)

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
                # Check for success/failure in response
                if "SUCCESS" in response.upper():
                    self._update_status(
                        f"Command sent: {command} - Response: {response}", "green"
                )
                elif "FAILED" in response.upper() or "ERROR" in response.upper():
                    self._update_status(
                        f"Command sent: {command} - Response: {response}", "red"
                    )
                    
                    # Extract and display detailed error message
                    if ":" in response:
                        error_detail = response.split(":", 1)[1].strip()
                        
                        # Comprehensive terminal logging for LED errors
                        if command in ["LED_ON", "LED_OFF"]:
                            print("\n" + "="*70, flush=True)
                            print(f"LED COMMAND FAILED: {command}", flush=True)
                            print("="*70, flush=True)
                            print(f"Error from target: {error_detail}", flush=True)
                            print("-"*70, flush=True)
                            
                            # Provide specific troubleshooting based on error type
                            if "GPIO not initialized" in error_detail:
                                print("ROOT CAUSE: GPIO hardware not initialized on target", flush=True)
                                print("SOLUTION: Target must be running with 'sudo' privileges", flush=True)
                                print("ACTION: Run target with: sudo python3 target_main.py", flush=True)
                                self._update_data_display(
                                    "[TROUBLESHOOTING] GPIO not initialized - ensure target is running with 'sudo'"
                                )
                            elif "Permission denied" in error_detail:
                                print("ROOT CAUSE: Insufficient permissions to access GPIO pins", flush=True)
                                print("SOLUTION: Target process needs root/sudo access", flush=True)
                                print("ACTION: Restart target with: sudo python3 target_main.py", flush=True)
                                self._update_data_display(
                                    "[TROUBLESHOOTING] Permission denied - target must run with 'sudo' to access GPIO"
                                )
                            elif "RuntimeError" in error_detail or "GPIO channels already in use" in error_detail:
                                print("ROOT CAUSE: GPIO pins are locked/in use by another process", flush=True)
                                print("SOLUTION: Clean up GPIO state and restart target", flush=True)
                                print("ACTION: Restart target with: sudo python3 target_main.py", flush=True)
                                print("        Or stop any other processes using GPIO pins", flush=True)
                                self._update_data_display(
                                    "[TROUBLESHOOTING] GPIO RuntimeError - pins may be in use, restart target"
                                )
                            elif "OS Error" in error_detail:
                                print("ROOT CAUSE: GPIO hardware access error", flush=True)
                                print("SOLUTION: Check hardware connections and GPIO wiring", flush=True)
                                print("ACTION: Verify LED is connected to correct GPIO pin (default: pin 26)", flush=True)
                                self._update_data_display(
                                    "[TROUBLESHOOTING] GPIO hardware error - check wiring and GPIO connections"
                                )
                            else:
                                print(f"ROOT CAUSE: {error_detail}", flush=True)
                                print("SOLUTION: Check target logs for more details", flush=True)
                            
                            print("="*70 + "\n", flush=True)
                            
                            # Also log via standard method
                            self._log_terminal_update("LED_ERROR", f"{command} failed: {error_detail}")
                        else:
                            # Non-LED errors - standard logging
                            self._log_terminal_update("COMMAND_ERROR", f"{command} -> {response}")
                        
                        self._update_data_display(f"[ERROR] {command} failed: {error_detail}")
                    else:
                        # No detailed error message
                        self._log_terminal_update("COMMAND_ERROR", f"{command} -> {response}")
                        self._update_data_display(f"[ERROR] {command} failed: {response}")
                else:
                    self._update_status(
                        f"Command sent: {command} - Response: {response}", "blue"
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
        actuator = self.actuators.get("mech_pump")
        if actuator:
            actuator.setAnalogValue(value)

    def _update_pressure_display(self, value):
        if self.pressure_label:
            self.pressure_label.configure(text=f"Pressure Sensor 1: {value} mT")

    def _update_adc_display(self, value):
        if self.adc_label:
            self.adc_label.configure(text=f"ADC CH0: {value}")

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
        if not hasattr(self, "auto_log_display") or self.auto_log_display is None:
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

    def _handle_udp_data(self, data: str):
        self._update_data_display(f"[UDP Data] {data}")
        self._update_target_snapshot(data)
        parsed = self._parse_periodic_packet(data)
        
        # Check for errors first (always log errors)
        has_error = any(
            "ERROR" in str(v).upper() or 
            "NOT_AVAILABLE" in str(v).upper() or 
            "NOT_INITIALIZED" in str(v).upper() or
            "DISCONNECTED" in str(v).upper()
            for v in (parsed.values() if parsed else [data])
        )
        
        if parsed:
            # Check if any values changed
            values_changed = False
            changed_items = []
            
            for key, value in parsed.items():
                # Skip TIME field for change detection (always changes)
                if key == "TIME":
                    continue
                    
                prev_value = self.previous_values.get(key)
                
                # For numeric values (like ADC_CH0), compare as numbers to handle string/int differences
                try:
                    if key.startswith("ADC_CH") or key == "Pressure_Sensor_1":
                        value_num = float(value) if value else None
                        prev_value_num = float(prev_value) if prev_value else None
                        if prev_value_num is None or abs(value_num - prev_value_num) >= 1.0:  # At least 1 unit change
                            values_changed = True
                            changed_items.append(f"{key}={value}")
                            self.previous_values[key] = value
                    else:
                        # String comparison for non-numeric values
                        if prev_value != value:
                            values_changed = True
                            changed_items.append(f"{key}={value}")
                            self.previous_values[key] = value
                        elif key not in self.previous_values:
                            # First time seeing this value
                            values_changed = True
                            changed_items.append(f"{key}={value}")
                            self.previous_values[key] = value
                except (ValueError, TypeError):
                    # Fallback to string comparison if conversion fails
                    if prev_value != value:
                        values_changed = True
                        changed_items.append(f"{key}={value}")
                        self.previous_values[key] = value
                    elif key not in self.previous_values:
                        values_changed = True
                        changed_items.append(f"{key}={value}")
                        self.previous_values[key] = value
            
            # Update ADC display
            adc_value = parsed.get("ADC_CH0")
            if adc_value is not None:
                self._update_adc_display(adc_value)
            
            # Only log to terminal if values changed or there's an error
            if values_changed or has_error:
                if changed_items:
                    summary = ", ".join(changed_items)
                    if has_error:
                        summary += " [ERROR DETECTED]"
                    self._log_terminal_update("TARGET_DATA", summary)
                elif has_error:
                    # Error but no value changes
                    summary = ", ".join(f"{k}={v}" for k, v in parsed.items() if 
                                       "ERROR" in str(v).upper() or 
                                       "NOT_AVAILABLE" in str(v).upper() or 
                                       "NOT_INITIALIZED" in str(v).upper())
                    self._log_terminal_update("TARGET_ERROR", summary)
        else:
            # Unparsed data - check for error keywords
            if has_error or "ERROR" in data.upper():
                self._log_terminal_update("TARGET_ERROR", data)

    def _handle_udp_status(self, message: str, address: tuple):
        self._update_data_display(f"[UDP Status] From {address[0]}: {message}")
        self._update_target_snapshot(message)
        
        has_error = "ERROR" in message.upper() or "FAILED" in message.upper() or "WARNING" in message.upper()
        
        matched_sensor = self.udp_client_object.process_received_data(message)
        
        if matched_sensor:
            sensor = self.sensors.get(matched_sensor)
            if sensor and sensor.value is not None:
                if matched_sensor == "pressure_sensor_1":
                    self._update_pressure_display(sensor.value)
                    prev_pressure = self.previous_values.get("Pressure_Sensor_1")
                    if prev_pressure != sensor.value:
                        self._log_terminal_update("TARGET_STATUS", f"Pressure Sensor 1: {sensor.value} mT")
                        self.previous_values["Pressure_Sensor_1"] = sensor.value
        
        try:
            payload = json.loads(message)
            telemetry = payload.get("telemetry")
            if telemetry:
                self.telemetry_mapper.handle_telemetry(telemetry)
            
            if has_error:
                self._log_terminal_update("TARGET_ERROR", message)
                
        except json.JSONDecodeError:
            if has_error:
                self._log_terminal_update("TARGET_ERROR", message)
        except Exception as exc:
            logger.error("Error parsing UDP status message: %s", exc)
            self._log_terminal_update("TARGET_ERROR", f"Parse error: {exc}")

    def _update_data_display(self, data: str):
        # Only log to terminal if it's an error (when GUI not available)
        if not self.data_display or not self.root:
            if "ERROR" in data.upper() or "FAILED" in data.upper():
                self._log_terminal_update("ERROR", data)
            return
        try:
            timestamp = time.strftime("%H:%M:%S")
            self.data_display.insert("end", f"{timestamp} - {data}\n")
            # Auto-scroll to bottom
            self.data_display.see("end")
        except Exception:
            pass

    def _log_terminal_update(self, tag: str, message: str):
        """Log periodic updates to terminal for visibility."""
        timestamp = time.strftime("%H:%M:%S")
        try:
            print(f"{timestamp} [{tag}] {message}", flush=True)
            # Also log via logger for file logging
            logger.info(f"[{tag}] {message}")
        except Exception:
            logger.debug("Failed to write terminal log entry", exc_info=True)

    def _update_status(self, message: str, color: str = "white"):
        if not self.status_label or not self.root:
            return
        try:
            self.status_label.configure(text=message, text_color=color)
        except Exception:
            pass

    def _update_target_snapshot(self, message: str):
        if not self.target_snapshot_var:
            return
        truncated = message.strip()
        if len(truncated) > 200:
            truncated = truncated[:197] + "..."
        self.target_snapshot_var.set(truncated if truncated else "(empty message)")

    def _parse_periodic_packet(self, payload: str) -> dict:
        result = {}
        if not payload:
            return result
        parts = payload.split("|")
        for part in parts:
            if ":" not in part:
                continue
            key, value = part.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key:
                result[key] = value
        return result

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
        print("=" * 70)
        print("Fusor Host Application starting...")
        print(f"Target IP: {self.target_ip}")
        print(f"  TCP Commands: Port {self.target_tcp_command_port} (Host → RPi)")
        print(f"  UDP Data: Port {self.tcp_data_port} (RPi → Host)")
        print(f"  UDP Status: Port {self.udp_status_port} (Bidirectional)")
        print("\nControl panel opening...")
        print("Commands sent via TCP (reliable), data received via UDP (efficient)")
        print("\n" + "=" * 70)
        print("TELEMETRY FROM TARGET (displayed below):")
        print("=" * 70)

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

        try:
            self.udp_data_client.stop()
        except Exception as e:
            logger.error(f"Error stopping UDP data client: {e}")

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
    parser.add_argument(
        "--no-terminal-updates",
        action="store_true",
        help="Disable mirrored target data in the host terminal",
    )

    args = parser.parse_args()

    # Create and run host application - control panel pops up
    app = FusorHostApp(
        target_ip=args.target_ip,
        target_tcp_command_port=args.target_tcp_command_port,
        tcp_data_port=args.tcp_data_port,
        udp_status_port=args.udp_status_port,
        terminal_updates=not args.no_terminal_updates,
    )

    _app_instance = app
    app.run()


if __name__ == "__main__":
    main()
