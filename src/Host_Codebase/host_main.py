#!/usr/bin/env python3
import customtkinter as ctk
import time
import argparse
import logging
import signal
import sys
import atexit
import json
import threading
from enum import Enum, auto
from queue import Queue
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
        elif "turbo" in actuator_name.lower():
            return f"SET_VALVE5:{int(value)}"
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
    def __init__(
        self,
        actuators: dict,
        sensors: dict = None,
        state_callback=None,
        log_callback=None,
    ):
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
            (
                State.SETTLE_STEADY_PRESSURE,
                Event.APS_MAIN_EQ_0_1_STEADY,
            ): State.SETTLING_10KV,
            (State.SETTLING_10KV, Event.STEADY_STATE_VOLTAGE): State.ADMIT_FUEL_TO_5MA,
            (State.ADMIT_FUEL_TO_5MA, Event.STEADY_STATE_CURRENT): State.NOMINAL_27KV,
            (State.DEENERGIZING, Event.ZERO_KV_STEADY): State.CLOSING_MAIN,
            (State.CLOSING_MAIN, Event.TIMEOUT_5S): State.VENTING_FORELINE,
            (State.VENTING_FORELINE, Event.APS_EQ_1_ATM): State.ALL_OFF,
            # Emergency stop from any state - immediately go to ALL_OFF
            (State.ROUGH_PUMP_DOWN, Event.STOP_CMD): State.ALL_OFF,
            (State.RP_DOWN_TURBO, Event.STOP_CMD): State.ALL_OFF,
            (State.TURBO_PUMP_DOWN, Event.STOP_CMD): State.ALL_OFF,
            (State.TP_DOWN_MAIN, Event.STOP_CMD): State.ALL_OFF,
            (State.SETTLE_STEADY_PRESSURE, Event.STOP_CMD): State.ALL_OFF,
            (State.SETTLING_10KV, Event.STOP_CMD): State.ALL_OFF,
            (State.ADMIT_FUEL_TO_5MA, Event.STOP_CMD): State.ALL_OFF,
            (State.NOMINAL_27KV, Event.STOP_CMD): State.ALL_OFF,
            (State.DEENERGIZING, Event.STOP_CMD): State.ALL_OFF,
            (State.CLOSING_MAIN, Event.STOP_CMD): State.ALL_OFF,
            (State.VENTING_FORELINE, Event.STOP_CMD): State.ALL_OFF,
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
        # Note: AutoController accesses actuators, but it's called from main thread
        # via telemetry mapper, so no lock needed here
        if "power_supply" in self.actuators:
            self.actuators["power_supply"].setAnalogValue(kv * 1000.0)

    def dispatch_event(self, event: Event):
        # Emergency stop always goes to ALL_OFF from any state
        if event == Event.STOP_CMD:
            self._enter_state(State.ALL_OFF)
            return
        
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

        if (
            s == State.SETTLE_STEADY_PRESSURE
            and aps_loc == "Main"
            and aps_p is not None
        ):
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
        self.data_log_window = None
        self.data_reading_window = None
        self.target_logs_display = None
        self.adc_ch0_label = None
        self.adc_ch1_label = None
        self.adc_ch2_label = None
        self.adc_ch3_label = None
        self.adc_ch4_label = None
        self.adc_ch5_label = None
        self.adc_ch6_label = None
        self.adc_ch7_label = None
        self.status_label = None
        self.voltage_scale = None
        self.pump_power_scale = None
        self.manual_mech_switch = None
        self.manual_mech_switch_state = False
        self.turbo_pump_switch = None
        self.turbo_pump_switch_state = False
        self.voltage_set_button = None
        self.valve_set_buttons = {}
        self.pressure_label = None
        self.adc_label = None
        self.auto_state_label = None
        self.auto_log_display = None
        self.terminal_updates_enabled = terminal_updates
        self._initial_log_message = None
        
        self.previous_values = {}

        self._previous_values_lock = threading.Lock()
        self._actuators_lock = threading.Lock()
        self._sensors_lock = threading.Lock()
        self._gui_update_queue = Queue()
        self._shutdown_event = threading.Event()

        self.tcp_client_object = TCPClientObject(self.tcp_command_client)
        
        self.actuators = {
            "power_supply": ActuatorObject(
                "power supply",
                "power supply",
                self.tcp_command_client,
                _build_actuator_command,
                self.tcp_client_object,
            ),
            "atm_valve": ActuatorObject(
                "valve1",
                "valve1",
                self.tcp_command_client,
                _build_actuator_command,
                self.tcp_client_object,
            ),
            "foreline_valve": ActuatorObject(
                "valve 2",
                "valve 2",
                self.tcp_command_client,
                _build_actuator_command,
                self.tcp_client_object,
            ),
            "turbo_valve": ActuatorObject(
                "turbo valve",
                "turbo valve",
                self.tcp_command_client,
                _build_actuator_command,
                self.tcp_client_object,
            ),
            "fusor_valve": ActuatorObject(
                "valve 3",
                "valve 3",
                self.tcp_command_client,
                _build_actuator_command,
                self.tcp_client_object,
            ),
            "mech_pump": ActuatorObject(
                "roughing pump",
                "roughing pump",
                self.tcp_command_client,
                _build_actuator_command,
                self.tcp_client_object,
            ),
            "turbo_pump": ActuatorObject(
                "turbo pump",
                "turbo pump",
                self.tcp_command_client,
                _build_actuator_command,
                self.tcp_client_object,
            ),
            "deuterium_valve": ActuatorObject(
                "valve 4",
                "valve 4",
                self.tcp_command_client,
                _build_actuator_command,
                self.tcp_client_object,
            ),
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

        if self.root:
            self.root.update()
            self.root.update_idletasks()

        if not self.tcp_command_client.connect():
            self._update_status("Failed to connect to target on startup", "red")
            initial_msg = (
                "[ERROR] Failed to connect to target - check network connection"
            )
            self._initial_log_message = initial_msg
            if self.data_display:
                self._update_data_display(initial_msg)
        else:
            self._update_status("Connected to target", "green")
            initial_msg = "[System] Connected to target successfully"
            self._initial_log_message = initial_msg
            if self.data_display:
                self._update_data_display(initial_msg)

        self.udp_data_client.start()
        logger.info("UDP data client started - receiving telemetry from target...")
        print("UDP data client started - receiving telemetry from target...")

        self.udp_status_client.start()
        self.udp_status_receiver.start()
        logger.info(
            "UDP status receiver started - waiting for status updates from target..."
        )
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
        auto_tab = self.tabview.add("Auto Control")
        log_reading_tab = self.tabview.add("Log Reading")

        # Data Reading will be a popup window, not a tab
        self.data_reading_window = None

        title_label_manual = ctk.CTkLabel(
            manual_tab,
            text="Fusor Manual Control Panel",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label_manual.pack(pady=10)

        main_container = ctk.CTkFrame(manual_tab)
        main_container.pack(fill="both", expand=True, padx=10, pady=5)

        left_column = ctk.CTkFrame(main_container)
        left_column.pack(fill="both", expand=True, padx=5)

        power_supply_section = ctk.CTkFrame(left_column)
        power_supply_section.pack(fill="x", padx=5, pady=5)

        voltage_slider_frame = ctk.CTkFrame(power_supply_section)
        voltage_slider_frame.pack(fill="x", padx=5, pady=5)

        voltage_slider_label = ctk.CTkLabel(
            voltage_slider_frame,
            text="Voltage Output Slider",
            font=ctk.CTkFont(size=12),
        )
        voltage_slider_label.pack(pady=2)

        self.voltage_scale = ctk.CTkSlider(
            voltage_slider_frame,
            from_=0,
            to=28000,
            command=self._update_voltage_label,
        )
        self.voltage_scale.set(0)
        self.voltage_scale.pack(fill="x", padx=5, pady=5)

        self.voltage_value_label = ctk.CTkLabel(
            voltage_slider_frame, text="0 V", font=ctk.CTkFont(size=11)
        )
        self.voltage_value_label.pack()

        self.voltage_set_button = ctk.CTkButton(
            voltage_slider_frame,
            text="Set Voltage",
            command=self._set_voltage,
            font=ctk.CTkFont(size=11),
            width=100,
        )
        self.voltage_set_button.pack(pady=5)

        pump_section = ctk.CTkFrame(left_column)
        pump_section.pack(fill="x", padx=5, pady=5)

        pump_row = ctk.CTkFrame(pump_section)
        pump_row.pack(fill="x", padx=5, pady=5)

        mech_pump_frame = ctk.CTkFrame(pump_row)
        mech_pump_frame.pack(side="left", fill="both", expand=True, padx=5)

        mech_pump_label = ctk.CTkLabel(
            mech_pump_frame, text="Mechanical Vacuum", font=ctk.CTkFont(size=12)
        )
        mech_pump_label.pack(pady=2)

        self.manual_mech_switch = ctk.CTkSwitch(
            mech_pump_frame,
            text="OFF",
            command=self._toggle_mech_pump,
            font=ctk.CTkFont(size=11),
        )
        self.manual_mech_switch.pack(pady=10)
        self.manual_mech_switch_state = False

        turbo_pump_frame = ctk.CTkFrame(pump_row)
        turbo_pump_frame.pack(side="left", fill="both", expand=True, padx=5)

        turbo_pump_label = ctk.CTkLabel(
            turbo_pump_frame, text="Turbo Vacuum", font=ctk.CTkFont(size=12)
        )
        turbo_pump_label.pack(pady=2)

        self.turbo_pump_switch = ctk.CTkSwitch(
            turbo_pump_frame,
            text="OFF",
            command=self._toggle_turbo_pump,
            font=ctk.CTkFont(size=11),
        )
        self.turbo_pump_switch.pack(pady=10)
        self.turbo_pump_switch_state = False

        valve_section = ctk.CTkFrame(left_column)
        valve_section.pack(fill="x", padx=5, pady=5)

        valve_label = ctk.CTkLabel(
            valve_section,
            text="Valve Controls",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        valve_label.pack(pady=5)

        valve_row = ctk.CTkFrame(valve_section)
        valve_row.pack(fill="x", padx=5, pady=5)

        valve_names = ["ATM/Depressure", "Foreline", "Vacsys", "Deuterium", "Turbo"]
        valve_actuator_keys = [
            "atm_valve",
            "foreline_valve",
            "fusor_valve",
            "deuterium_valve",
            "turbo_valve",
        ]
        self.valve_sliders = {}
        self.valve_value_labels = {}

        for i, (valve_name, actuator_key) in enumerate(
            zip(valve_names, valve_actuator_keys)
        ):
            valve_frame = ctk.CTkFrame(valve_row)
            valve_frame.pack(side="left", fill="both", expand=True, padx=2)

            valve_title = ctk.CTkLabel(
                valve_frame, text=valve_name, font=ctk.CTkFont(size=10)
            )
            valve_title.pack(pady=2)

            slider = ctk.CTkSlider(
                valve_frame,
                from_=0,
                to=100,
                command=lambda v, k=actuator_key, idx=i: self._update_valve_label(
                    k, idx, v
                ),
            )
            slider.set(0)
            slider.pack(fill="x", padx=3, pady=3)

            value_label = ctk.CTkLabel(valve_frame, text="0%", font=ctk.CTkFont(size=9))
            value_label.pack()

            set_button = ctk.CTkButton(
                valve_frame,
                text="Set",
                command=lambda k=actuator_key, s=slider: self._set_valve(k, s.get()),
                font=ctk.CTkFont(size=9),
                width=50,
                height=25,
            )
            set_button.pack(pady=2)

            self.valve_sliders[actuator_key] = slider
            self.valve_value_labels[actuator_key] = value_label
            self.valve_set_buttons[actuator_key] = set_button

        self.foreline_manual_slider = self.valve_sliders.get("foreline_valve")
        self.turbo_valve_manual_slider = self.valve_sliders.get("turbo_valve")
        self.vacsys_manual_slider = self.valve_sliders.get("fusor_valve")
        self.deuterium_manual_slider = self.valve_sliders.get("deuterium_valve")
        self.foreline_value_label = self.valve_value_labels.get("foreline_valve")
        self.turbo_valve_value_label = self.valve_value_labels.get("turbo_valve")
        self.vacsys_value_label = self.valve_value_labels.get("fusor_valve")
        self.deuterium_value_label = self.valve_value_labels.get("deuterium_valve")

        # Button to open Data Reading popup window
        data_reading_button_frame = ctk.CTkFrame(left_column)
        data_reading_button_frame.pack(fill="x", padx=5, pady=10)

        open_data_reading_button = ctk.CTkButton(
            data_reading_button_frame,
            text="Open Data Reading Window",
            command=self._open_data_reading_window,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=250,
            height=40,
            fg_color="green",
            hover_color="darkgreen",
        )
        open_data_reading_button.pack(pady=10)

        # Initialize data reading window widgets as None (will be created in popup)
        self.pressure_display1 = None
        self.pressure_display2 = None
        self.pressure_display3 = None
        self.adc_ch0_label = None
        self.adc_ch1_label = None
        self.adc_ch2_label = None
        self.adc_ch3_label = None
        self.adc_ch4_label = None
        self.adc_ch5_label = None
        self.adc_ch6_label = None
        self.adc_ch7_label = None
        self.pressure_label = None
        self.adc_label = None

        log_reading_title = ctk.CTkLabel(
            log_reading_tab,
            text="Target Logs (Live from Raspberry Pi)",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        log_reading_title.pack(pady=10)

        log_reading_container = ctk.CTkFrame(log_reading_tab)
        log_reading_container.pack(fill="both", expand=True, padx=10, pady=10)

        target_logs_frame = ctk.CTkFrame(log_reading_container)
        target_logs_frame.pack(fill="both", expand=True, padx=5, pady=8)

        target_logs_label = ctk.CTkLabel(
            target_logs_frame,
            text="Live Target Logs",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        target_logs_label.pack(pady=8)

        self.target_logs_display = ctk.CTkTextbox(
            target_logs_frame,
            font=ctk.CTkFont(size=10, family="Courier"),
            wrap="word",
        )
        self.target_logs_display.pack(fill="both", expand=True, padx=10, pady=10)
        self.target_logs_display.insert(
            "end", "[Target Logs] Waiting for logs from Raspberry Pi...\n"
        )
        self.target_logs_display.configure(state="disabled")

        test_buttons_frame = ctk.CTkFrame(target_logs_frame)
        test_buttons_frame.pack(pady=10)
        
        clear_target_logs_button = ctk.CTkButton(
            test_buttons_frame,
            text="Clear Target Logs",
            command=self._clear_target_logs,
            font=ctk.CTkFont(size=12),
            width=150,
            height=35,
        )
        clear_target_logs_button.pack(side="left", padx=5)

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
            auto_button_frame,
            text="Start Auto Sequence",
            command=self._auto_start,
            width=180,
        )
        auto_start.pack(side="left", padx=5, pady=5)

        auto_stop = ctk.CTkButton(
            auto_button_frame,
            text="Stop / Emergency",
            command=self._auto_stop,
            width=180,
            fg_color="red",
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

        self._process_gui_updates()

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
                            print("\n" + "=" * 70, flush=True)
                            print(f"LED COMMAND FAILED: {command}", flush=True)
                            print("=" * 70, flush=True)
                            print(f"Error from target: {error_detail}", flush=True)
                            print("-" * 70, flush=True)
                            
                            # Provide specific troubleshooting based on error type
                            if "GPIO not initialized" in error_detail:
                                print(
                                    "ROOT CAUSE: GPIO hardware not initialized on target",
                                    flush=True,
                                )
                                print(
                                    "SOLUTION: Target must be running with 'sudo' privileges",
                                    flush=True,
                                )
                                print(
                                    "ACTION: Run target with: sudo python3 target_main.py",
                                    flush=True,
                                )
                                self._update_data_display(
                                    "[TROUBLESHOOTING] GPIO not initialized - ensure target is running with 'sudo'"
                                )
                            elif "Permission denied" in error_detail:
                                print(
                                    "ROOT CAUSE: Insufficient permissions to access GPIO pins",
                                    flush=True,
                                )
                                print(
                                    "SOLUTION: Target process needs root/sudo access",
                                    flush=True,
                                )
                                print(
                                    "ACTION: Restart target with: sudo python3 target_main.py",
                                    flush=True,
                                )
                                self._update_data_display(
                                    "[TROUBLESHOOTING] Permission denied - target must run with 'sudo' to access GPIO"
                                )
                            elif (
                                "RuntimeError" in error_detail
                                or "GPIO channels already in use" in error_detail
                            ):
                                print(
                                    "ROOT CAUSE: GPIO pins are locked/in use by another process",
                                    flush=True,
                                )
                                print(
                                    "SOLUTION: Clean up GPIO state and restart target",
                                    flush=True,
                                )
                                print(
                                    "ACTION: Restart target with: sudo python3 target_main.py",
                                    flush=True,
                                )
                                print(
                                    "        Or stop any other processes using GPIO pins",
                                    flush=True,
                                )
                                self._update_data_display(
                                    "[TROUBLESHOOTING] GPIO RuntimeError - pins may be in use, restart target"
                                )
                            elif "OS Error" in error_detail:
                                print(
                                    "ROOT CAUSE: GPIO hardware access error", flush=True
                                )
                                print(
                                    "SOLUTION: Check hardware connections and GPIO wiring",
                                    flush=True,
                                )
                                print(
                                    "ACTION: Verify LED is connected to correct GPIO pin (default: pin 26)",
                                    flush=True,
                                )
                                self._update_data_display(
                                    "[TROUBLESHOOTING] GPIO hardware error - check wiring and GPIO connections"
                                )
                            else:
                                print(f"ROOT CAUSE: {error_detail}", flush=True)
                                print(
                                    "SOLUTION: Check target logs for more details",
                                    flush=True,
                                )
                            
                            print("=" * 70 + "\n", flush=True)
                            
                            # Also log via standard method
                            self._log_terminal_update(
                                "LED_ERROR", f"{command} failed: {error_detail}"
                            )
                        else:
                            # Non-LED errors - standard logging
                            self._log_terminal_update(
                                "COMMAND_ERROR", f"{command} -> {response}"
                            )
                        
                        self._update_data_display(
                            f"[ERROR] {command} failed: {error_detail}"
                        )
                    else:
                        # No detailed error message
                        self._log_terminal_update(
                            "COMMAND_ERROR", f"{command} -> {response}"
                        )
                        self._update_data_display(
                            f"[ERROR] {command} failed: {response}"
                        )
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
        if hasattr(self, "voltage_value_label"):
            self.voltage_value_label.configure(text=f"{int(value)} V")

    def _update_pump_label(self, value):
        if hasattr(self, "pump_value_label"):
            self.pump_value_label.configure(text=f"{int(value)}%")

    # Removed _manual_slider_change and _update_turbo_pump_label - replaced with toggle switches

    def _update_valve_label(self, valve_key, idx, value):
        if valve_key and valve_key in self.valve_value_labels:
            self.valve_value_labels[valve_key].configure(text=f"{int(value)}%")

    def _set_valve(self, valve_name: str, value: float):
        if self._is_auto_mode_active():
            self._update_status("Cannot control manually while auto mode is active", "red")
            return
        
        if value < 0 or value > 100:
            self._update_status(f"Invalid valve value: {value} (must be 0-100)", "red")
            return
        
        with self._actuators_lock:
            actuator = self.actuators.get(valve_name)
        
        if actuator:
            self._update_status(f"Setting {valve_name} to {int(value)}%...", "blue")
            actuator.setAnalogValue(value)
            self._update_data_display(f"[VALVE] Setting {valve_name} to {int(value)}%")
        else:
            self._update_status(f"Valve {valve_name} not found", "red")
            self._update_data_display(f"[ERROR] Valve {valve_name} not found")

    def _update_pressure_display(self, value):
        if not self.root:
            return

        def _do_update():
            try:
                if hasattr(self, "pressure_display1") and self.pressure_display1:
                    self.pressure_display1.configure(
                        text=f"Turbo Pressure Sensor [ADC CH1]: {value} mT"
                    )
                if hasattr(self, "pressure_label") and self.pressure_label:
                    self.pressure_label.configure(
                        text=f"Turbo Pressure Sensor [ADC CH1]: {value} mT"
                    )
            except Exception:
                pass

        self._schedule_gui_update(_do_update)

    def _update_adc_display(self, value):
        if not self.root:
            return

        def _do_update():
            try:
                if hasattr(self, "adc_ch0_label") and self.adc_ch0_label:
                    self.adc_ch0_label.configure(
                        text=f"ADC CH0 [Potentiometer - Testing]: {value}"
                    )
                if hasattr(self, "adc_label") and self.adc_label:
                    self.adc_label.configure(
                        text=f"ADC CH0 [Potentiometer - Testing]: {value}"
                    )
            except Exception:
                pass

        self._schedule_gui_update(_do_update)

    def _update_all_adc_channels(self, adc_data):
        if not self.root:
            return

        def _do_update():
            try:
                adc_channels = {
                    "adc_ch0_label": 0,
                    "adc_ch1_label": 1,
                    "adc_ch2_label": 2,
                    "adc_ch3_label": 3,
                    "adc_ch4_label": 4,
                    "adc_ch5_label": 5,
                    "adc_ch6_label": 6,
                    "adc_ch7_label": 7,
                }

                if isinstance(adc_data, (list, tuple)) and len(adc_data) >= 8:
                    channel_labels = {
                        0: "ADC CH0 [Potentiometer - Testing]",
                        1: "ADC CH1",
                        2: "ADC CH2",
                        3: "ADC CH3",
                        4: "ADC CH4",
                        5: "ADC CH5",
                        6: "ADC CH6",
                        7: "ADC CH7",
                    }
                    for label_attr, channel in adc_channels.items():
                        if hasattr(self, label_attr):
                            label = getattr(self, label_attr)
                            if label:
                                label_text = channel_labels.get(
                                    channel, f"ADC CH{channel}"
                                )
                                label.configure(
                                    text=f"{label_text}: {adc_data[channel]}"
                                )
            except Exception:
                pass

        self._schedule_gui_update(_do_update)

    def _is_auto_mode_active(self):
        """Check if auto mode is currently active (not in ALL_OFF state)"""
        return self.auto_controller.currentState != State.ALL_OFF

    def _enable_manual_controls(self):
        """Enable all manual control widgets"""
        if not self.root:
            return
        def _do_update():
            try:
                if self.voltage_scale:
                    self.voltage_scale.configure(state="normal")
                if self.voltage_set_button:
                    self.voltage_set_button.configure(state="normal")
                if self.manual_mech_switch:
                    self.manual_mech_switch.configure(state="normal")
                if self.turbo_pump_switch:
                    self.turbo_pump_switch.configure(state="normal")
                for slider in self.valve_sliders.values():
                    if slider:
                        slider.configure(state="normal")
                for button in self.valve_set_buttons.values():
                    if button:
                        button.configure(state="normal")
            except Exception:
                pass
        self._schedule_gui_update(_do_update)

    def _disable_manual_controls(self):
        """Disable all manual control widgets"""
        if not self.root:
            return
        def _do_update():
            try:
                if self.voltage_scale:
                    self.voltage_scale.configure(state="disabled")
                if self.voltage_set_button:
                    self.voltage_set_button.configure(state="disabled")
                if self.manual_mech_switch:
                    self.manual_mech_switch.configure(state="disabled")
                if self.turbo_pump_switch:
                    self.turbo_pump_switch.configure(state="disabled")
                for slider in self.valve_sliders.values():
                    if slider:
                        slider.configure(state="disabled")
                for button in self.valve_set_buttons.values():
                    if button:
                        button.configure(state="disabled")
            except Exception:
                pass
        self._schedule_gui_update(_do_update)

    def _auto_start(self):
        if self._is_auto_mode_active():
            self._update_status("Auto mode is already running", "orange")
            return
        if self.auto_log_display:
            self.auto_log_display.configure(state="normal")
            self.auto_log_display.insert("end", "[FSM] Start requested\n")
            self.auto_log_display.configure(state="disabled")
        self._disable_manual_controls()
        self.auto_controller.dispatch_event(Event.START)

    def _auto_stop(self):
        if self.auto_log_display:
            self.auto_log_display.configure(state="normal")
            self.auto_log_display.insert("end", "[FSM] Emergency stop requested - returning to ALL_OFF\n")
            self.auto_log_display.configure(state="disabled")
        # Dispatch stop event to transition to ALL_OFF immediately
        self.auto_controller.dispatch_event(Event.STOP_CMD)
        # Immediately re-enable manual controls for emergency stop
        # (State will be ALL_OFF after dispatch_event completes)
        self._enable_manual_controls()

    def _auto_update_state_label(self, state: State):
        if not self.auto_state_label or not self.root:
            return

        def _do_update():
            try:
                self.auto_state_label.configure(text=f"Current State: {state.name}")
                # Re-enable manual controls when auto mode returns to ALL_OFF
                if state == State.ALL_OFF:
                    self._enable_manual_controls()
            except Exception:
                pass

        self._schedule_gui_update(_do_update)

    def _auto_log_event(self, message: str):
        if (
            not hasattr(self, "auto_log_display")
            or self.auto_log_display is None
            or not self.root
        ):
            return

        def _do_update():
            try:
                timestamp = time.strftime("%H:%M:%S")
                self.auto_log_display.configure(state="normal")
                self.auto_log_display.insert("end", f"[{timestamp}] {message}\n")
                self.auto_log_display.see("end")
                self.auto_log_display.configure(state="disabled")
            except Exception:
                pass

        self._schedule_gui_update(_do_update)

    def _set_voltage(self):
        if self._is_auto_mode_active():
            self._update_status("Cannot control manually while auto mode is active", "red")
            return
        
        try:
            voltage = int(self.voltage_scale.get())
        except (ValueError, AttributeError):
            self._update_status("Invalid voltage value", "red")
            self._update_data_display("[ERROR] Could not read voltage from slider")
            return
        
        if voltage < 0 or voltage > 28000:
            self._update_status(f"Voltage out of range: {voltage}V (must be 0-28000V)", "red")
            self._update_data_display(f"[ERROR] Voltage out of range: {voltage}V")
            return
        
        # Enable power supply if voltage > 0
        if voltage > 0:
            self._update_status("Enabling power supply...", "blue")
            self._send_command("POWER_SUPPLY_ENABLE")
            self._update_data_display(f"[POWER] Enabling power supply for {voltage}V")
        
        # Set voltage
        command = self.command_handler.build_set_voltage_command(voltage)
        if command:
            self._update_status(f"Setting voltage to {voltage}V...", "blue")
            self._send_command(command)
            self._update_data_display(f"[POWER] Setting voltage to {voltage}V")
        else:
            self._update_status("Failed to build voltage command", "red")
            self._update_data_display(f"[ERROR] Failed to build voltage command for {voltage}V")

    def _set_pump_power(self):
        power = int(self.pump_power_scale.get())
        command = self.command_handler.build_set_pump_power_command(power)
        if command:
            self._send_command(command)
        else:
            self._update_status("Invalid power value", "red")
            if hasattr(self, "data_display") and self.data_display:
                self._update_data_display(f"[ERROR] Invalid power: {power}")

    def _toggle_mech_pump(self):
        if self._is_auto_mode_active():
            self._update_status("Cannot control manually while auto mode is active", "red")
            # Reset switch to previous state
            self.manual_mech_switch.deselect() if not self.manual_mech_switch_state else self.manual_mech_switch.select()
            return
        
        self.manual_mech_switch_state = self.manual_mech_switch.get()
        power = 100 if self.manual_mech_switch_state else 0
        self.manual_mech_switch.configure(text="ON" if self.manual_mech_switch_state else "OFF")
        command = f"SET_MECHANICAL_PUMP:{power}"
        self._send_command(command)

    def _toggle_turbo_pump(self):
        if self._is_auto_mode_active():
            self._update_status("Cannot control manually while auto mode is active", "red")
            # Reset switch to previous state
            self.turbo_pump_switch.deselect() if not self.turbo_pump_switch_state else self.turbo_pump_switch.select()
            return
        
        self.turbo_pump_switch_state = self.turbo_pump_switch.get()
        power = 100 if self.turbo_pump_switch_state else 0
        self.turbo_pump_switch.configure(text="ON" if self.turbo_pump_switch_state else "OFF")
        command = f"SET_TURBO_PUMP:{power}"
        self._send_command(command)

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
        parsed = self._parse_periodic_packet(data)
        
        # Check for errors first (always log errors)
        has_error = any(
            "ERROR" in str(v).upper()
            or "NOT_AVAILABLE" in str(v).upper()
            or "NOT_INITIALIZED" in str(v).upper()
            or "DISCONNECTED" in str(v).upper()
            for v in (parsed.values() if parsed else [data])
        )
        
        if parsed:
            # Check if any values changed
            values_changed = False
            changed_items = []
            
            with self._previous_values_lock:
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
                            if (
                                prev_value_num is None
                                or abs(value_num - prev_value_num) >= 5.0
                            ):  # At least 5 unit change (noise filtering)
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
            
            # Update ADC displays
            adc_values = []
            for ch in range(8):
                adc_key = f"ADC_CH{ch}"
                adc_value = parsed.get(adc_key)
                if adc_value is not None:
                    adc_values.append(adc_value)
                    if ch == 0:
                        self._update_adc_display(adc_value)
            
            if len(adc_values) >= 8:
                self._update_all_adc_channels(adc_values)

            adc_data = parsed.get("ADC_DATA")
            if adc_data:
                try:
                    if isinstance(adc_data, str):
                        adc_list = [int(x.strip()) for x in adc_data.split(",")]
                    else:
                        adc_list = list(adc_data)
                    if len(adc_list) >= 8:
                        self._update_all_adc_channels(adc_list)
                except (ValueError, TypeError):
                    pass
            
            if values_changed or has_error:
                if changed_items:
                    summary = ", ".join(changed_items)
                    if has_error:
                        summary += " [ERROR DETECTED]"
                    self._update_target_logs(f"[UDP Data] {summary}")
                    self._log_terminal_update("TARGET_DATA", summary)
                elif has_error:
                    summary = ", ".join(
                        f"{k}={v}"
                        for k, v in parsed.items()
                        if "ERROR" in str(v).upper()
                        or "NOT_AVAILABLE" in str(v).upper()
                        or "NOT_INITIALIZED" in str(v).upper()
                        or "DISCONNECTED" in str(v).upper()
                    )
                    self._update_target_logs(f"[UDP Data] {summary}")
                    self._log_terminal_update("TARGET_ERROR", summary)
        else:
            if has_error or "ERROR" in data.upper():
                self._update_target_logs(f"[UDP Data] {data}")
                self._log_terminal_update("TARGET_ERROR", data)
            else:
                self._update_target_logs(f"[UDP Data] {data}")

    def _handle_udp_status(self, message: str, address: tuple):
        self._update_data_display(f"[UDP Status] From {address[0]}: {message}")
        
        has_error = (
            "ERROR" in message.upper()
            or "FAILED" in message.upper()
            or "WARNING" in message.upper()
        )
        
        if message.startswith("STATUS:"):
            status_msg = message[7:].strip()
            self._update_target_logs(f"[Status] {status_msg}")
        elif message.startswith("ARDUINO_DATA:"):
            arduino_msg = message[13:].strip()
            if has_error:
                self._update_target_logs(f"[Arduino] [ERROR] {arduino_msg}")
            else:
                self._update_target_logs(f"[Arduino] {arduino_msg}")
        else:
            self._update_target_logs(f"[UDP Status] {message}")
        
        if has_error:
            self._update_target_logs(f"[ERROR] {message}")
        
        matched_sensor = self.udp_client_object.process_received_data(message)
        
        if matched_sensor:
            with self._sensors_lock:
                sensor = self.sensors.get(matched_sensor)
                if sensor and sensor.value is not None:
                    if matched_sensor == "pressure_sensor_1":
                        try:
                            self._update_pressure_display(sensor.value)
                        except Exception:
                            pass
                        with self._previous_values_lock:
                            prev_pressure = self.previous_values.get(
                                "Pressure_Sensor_1"
                            )
                            if prev_pressure != sensor.value:
                                try:
                                    self._log_terminal_update(
                                        "TARGET_STATUS",
                                        f"Pressure Sensor 1: {sensor.value} mT",
                                    )
                                except Exception:
                                    pass
                            self.previous_values["Pressure_Sensor_1"] = sensor.value
        
        try:
            payload = json.loads(message)
            telemetry = payload.get("telemetry")
            if telemetry:
                self.telemetry_mapper.handle_telemetry(telemetry)
        except json.JSONDecodeError:
            if has_error:
                try:
                    self._log_terminal_update("TARGET_ERROR", message)
                except Exception:
                    pass
        except Exception as exc:
            if has_error:
                try:
                    logger.error("Error parsing UDP status message: %s", exc)
                    self._log_terminal_update("TARGET_ERROR", f"Parse error: {exc}")
                except Exception:
                    pass

    def _process_gui_updates(self):
        try:
            while not self._gui_update_queue.empty():
                try:
                    update_func, args, kwargs = self._gui_update_queue.get_nowait()
                    update_func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error processing GUI update: {e}")
        except Exception:
            pass

        if self.root and not self._shutdown_event.is_set():
            self.root.after(50, self._process_gui_updates)

    def _schedule_gui_update(self, func, *args, **kwargs):
        if self.root and not self._shutdown_event.is_set():
            self._gui_update_queue.put((func, args, kwargs))

    def _open_data_log_window(self):
        if self.data_log_window is not None:
            try:
                if self.data_log_window.winfo_exists():
                    self.data_log_window.lift()
                    self.data_log_window.focus()
                    return
            except:
                self.data_log_window = None

        self.data_log_window = ctk.CTkToplevel(self.root)
        self.data_log_window.title("Data Logs - Read-Only from Target")
        self.data_log_window.geometry("900x600")

        log_window_frame = ctk.CTkFrame(self.data_log_window)
        log_window_frame.pack(fill="both", expand=True, padx=10, pady=10)

        log_title = ctk.CTkLabel(
            log_window_frame,
            text="Data Logs (Read-Only from Target)",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        log_title.pack(pady=10)

        self.data_display = ctk.CTkTextbox(
            log_window_frame,
            font=ctk.CTkFont(size=11, family="Courier"),
            wrap="word",
        )
        self.data_display.pack(fill="both", expand=True, padx=10, pady=10)

        clear_button = ctk.CTkButton(
            log_window_frame,
            text="Clear Logs",
            command=self._clear_data_display,
            font=ctk.CTkFont(size=12),
            width=120,
            height=35,
        )
        clear_button.pack(pady=5)

        self.data_log_window.protocol("WM_DELETE_WINDOW", self._close_data_log_window)

        if hasattr(self, "_initial_log_message"):
            self._update_data_display(self._initial_log_message)

    def _close_data_log_window(self):
        if hasattr(self, "data_log_window") and self.data_log_window:
            try:
                self.data_log_window.destroy()
            except:
                pass
            self.data_log_window = None
            self.data_display = None

    def _open_data_reading_window(self):
        if self.data_reading_window is not None:
            try:
                if self.data_reading_window.winfo_exists():
                    self.data_reading_window.lift()
                    self.data_reading_window.focus()
                    return
            except:
                self.data_reading_window = None

        self.data_reading_window = ctk.CTkToplevel(self.root)
        self.data_reading_window.title("Sensor Data Readouts")
        self.data_reading_window.geometry("800x600")

        data_reading_container = ctk.CTkFrame(self.data_reading_window)
        data_reading_container.pack(fill="both", expand=True, padx=10, pady=10)

        data_reading_title = ctk.CTkLabel(
            data_reading_container,
            text="Sensor Data Readouts",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        data_reading_title.pack(pady=10)

        pressure_readout_frame = ctk.CTkFrame(data_reading_container)
        pressure_readout_frame.pack(fill="x", padx=5, pady=8)

        pressure_readout_label = ctk.CTkLabel(
            pressure_readout_frame,
            text="Pressure Sensor Readouts",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        pressure_readout_label.pack(pady=8)

        pressure_row1 = ctk.CTkFrame(pressure_readout_frame)
        pressure_row1.pack(fill="x", padx=5, pady=5)

        self.pressure_display1 = ctk.CTkLabel(
            pressure_row1,
            text="Turbo Pressure Sensor [ADC CH1]: --- mT",
            font=ctk.CTkFont(size=13),
            anchor="w",
            width=400,
            height=30,
        )
        self.pressure_display1.pack(side="left", padx=8, pady=3)

        pressure_row2 = ctk.CTkFrame(pressure_readout_frame)
        pressure_row2.pack(fill="x", padx=5, pady=5)

        self.pressure_display2 = ctk.CTkLabel(
            pressure_row2,
            text="Fusor Pressure Sensor [ADC CH2]: --- mT",
            font=ctk.CTkFont(size=13),
            anchor="w",
            width=400,
            height=30,
        )
        self.pressure_display2.pack(side="left", padx=8, pady=3)

        pressure_row3 = ctk.CTkFrame(pressure_readout_frame)
        pressure_row3.pack(fill="x", padx=5, pady=5)

        self.pressure_display3 = ctk.CTkLabel(
            pressure_row3,
            text="Foreline Pressure Sensor [ADC CH3]: --- mT",
            font=ctk.CTkFont(size=13),
            anchor="w",
            width=400,
            height=30,
        )
        self.pressure_display3.pack(side="left", padx=8, pady=3)

        self.pressure_label = self.pressure_display1

        adc_readout_frame = ctk.CTkFrame(data_reading_container)
        adc_readout_frame.pack(fill="x", padx=5, pady=8)

        adc_readout_label = ctk.CTkLabel(
            adc_readout_frame,
            text="ADC Channel Readouts",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        adc_readout_label.pack(pady=8)

        adc_row1 = ctk.CTkFrame(adc_readout_frame)
        adc_row1.pack(fill="x", padx=5, pady=5)

        self.adc_ch0_label = ctk.CTkLabel(
            adc_row1,
            text="ADC CH0 [Potentiometer - Testing]: ---",
            font=ctk.CTkFont(size=13),
            anchor="w",
            width=300,
            height=30,
        )
        self.adc_ch0_label.pack(side="left", padx=8, pady=3)

        adc_row2 = ctk.CTkFrame(adc_readout_frame)
        adc_row2.pack(fill="x", padx=5, pady=5)

        self.adc_ch1_label = ctk.CTkLabel(
            adc_row2,
            text="ADC CH1: ---",
            font=ctk.CTkFont(size=13),
            anchor="w",
            width=180,
            height=30,
        )
        self.adc_ch1_label.pack(side="left", padx=8, pady=3)

        self.adc_ch2_label = ctk.CTkLabel(
            adc_row2,
            text="ADC CH2: ---",
            font=ctk.CTkFont(size=13),
            anchor="w",
            width=180,
            height=30,
        )
        self.adc_ch2_label.pack(side="left", padx=8, pady=3)

        self.adc_ch3_label = ctk.CTkLabel(
            adc_row2,
            text="ADC CH3: ---",
            font=ctk.CTkFont(size=13),
            anchor="w",
            width=180,
            height=30,
        )
        self.adc_ch3_label.pack(side="left", padx=8, pady=3)

        adc_row3 = ctk.CTkFrame(adc_readout_frame)
        adc_row3.pack(fill="x", padx=5, pady=5)

        self.adc_ch4_label = ctk.CTkLabel(
            adc_row3,
            text="ADC CH4: ---",
            font=ctk.CTkFont(size=13),
            anchor="w",
            width=180,
            height=30,
        )
        self.adc_ch4_label.pack(side="left", padx=8, pady=3)

        self.adc_ch5_label = ctk.CTkLabel(
            adc_row3,
            text="ADC CH5: ---",
            font=ctk.CTkFont(size=13),
            anchor="w",
            width=180,
            height=30,
        )
        self.adc_ch5_label.pack(side="left", padx=8, pady=3)

        self.adc_ch6_label = ctk.CTkLabel(
            adc_row3,
            text="ADC CH6: ---",
            font=ctk.CTkFont(size=13),
            anchor="w",
            width=180,
            height=30,
        )
        self.adc_ch6_label.pack(side="left", padx=8, pady=3)

        self.adc_ch7_label = ctk.CTkLabel(
            adc_row3,
            text="ADC CH7: ---",
            font=ctk.CTkFont(size=13),
            anchor="w",
            width=180,
            height=30,
        )
        self.adc_ch7_label.pack(side="left", padx=8, pady=3)

        self.adc_label = self.adc_ch0_label

        self.data_reading_window.protocol("WM_DELETE_WINDOW", self._close_data_reading_window)

    def _close_data_reading_window(self):
        if hasattr(self, "data_reading_window") and self.data_reading_window:
            try:
                self.data_reading_window.destroy()
            except:
                pass
            self.data_reading_window = None
            # Keep labels as None so updates don't crash
            self.pressure_display1 = None
            self.pressure_display2 = None
            self.pressure_display3 = None
            self.adc_ch0_label = None
            self.adc_ch1_label = None
            self.adc_ch2_label = None
            self.adc_ch3_label = None
            self.adc_ch4_label = None
            self.adc_ch5_label = None
            self.adc_ch6_label = None
            self.adc_ch7_label = None
            self.pressure_label = None
            self.adc_label = None

    def _clear_data_display(self):
        if self.data_display:
            self.data_display.delete("1.0", "end")

    def _clear_target_logs(self):
        if self.target_logs_display:
            self.target_logs_display.configure(state="normal")
            self.target_logs_display.delete("1.0", "end")
            self.target_logs_display.insert("end", "[Target Logs] Logs cleared.\n")
            self.target_logs_display.configure(state="disabled")

    def _update_target_logs(self, log_message: str):
        if not self.target_logs_display or not self.root:
            return

        def _do_update():
            try:
                if self.target_logs_display:
                    timestamp = time.strftime("%H:%M:%S")
                    self.target_logs_display.configure(state="normal")
                    self.target_logs_display.insert(
                        "end", f"[{timestamp}] {log_message}\n"
                    )
                    self.target_logs_display.see("end")
                    # Limit log size to prevent memory issues (keep last 1000 lines)
                    lines = self.target_logs_display.get("1.0", "end").split("\n")
                    if len(lines) > 1000:
                        self.target_logs_display.delete("1.0", f"{len(lines) - 1000}.0")
                    self.target_logs_display.configure(state="disabled")
            except Exception:
                pass

        self._schedule_gui_update(_do_update)

    def _update_data_display(self, data: str):
        if not self.data_display or not self.root:
            if "ERROR" in data.upper() or "FAILED" in data.upper():
                self._log_terminal_update("ERROR", data)
            return

        def _do_update():
            try:
                if self.data_display:
                    timestamp = time.strftime("%H:%M:%S")
                    self.data_display.insert("end", f"{timestamp} - {data}\n")
                    self.data_display.see("end")
            except Exception:
                pass

        self._schedule_gui_update(_do_update)

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

        def _do_update():
            try:
                if self.status_label:
                    self.status_label.configure(text=message, text_color=color)
            except Exception:
                pass

        self._schedule_gui_update(_do_update)

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
        if hasattr(self, "data_log_window") and self.data_log_window:
            try:
                self.data_log_window.destroy()
            except:
                pass
            self.data_log_window = None
        self._turn_off_led()
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
            self._shutdown_event.set()
            self._turn_off_led()
            self.stop()

    def stop(self):
        self._shutdown_event.set()

        try:
            self._turn_off_led()
        except Exception as e:
            logger.error(f"Error turning off LED in stop: {e}")

        try:
            self.tcp_command_client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting TCP client: {e}")

        try:
            self.udp_data_client.stop()
        except Exception as e:
            logger.error(f"Error stopping UDP data client: {e}")

        try:
            self.udp_status_client.stop()
            self.udp_status_receiver.stop()
        except Exception as e:
            logger.error(f"Error stopping UDP communication: {e}")

        try:
            while not self._gui_update_queue.empty():
                try:
                    self._gui_update_queue.get_nowait()
                except Exception:
                    break
        except Exception as e:
            logger.error(f"Error clearing GUI update queue: {e}")


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
