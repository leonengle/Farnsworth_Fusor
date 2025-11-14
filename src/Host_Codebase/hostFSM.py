import customtkinter as ctk
import json
import threading
from enum import Enum, auto
from tcp_command_client import TCPCommandClient
from udp_status_client import UDPStatusReceiver
from tcp_data_client import TCPDataClient


# ============================================================
#  Fusor components
# ============================================================

class FusorComponent:
    def __init__(self, name: str, tcp_client: TCPCommandClient, component_map: dict = None):
        self.name = name
        self.tcp_client = tcp_client
        self.component_map = component_map or {}
    
    def _send_target_command(self, command: str):
        if not self.tcp_client.is_connected():
            if not self.tcp_client.connect():
                print(f"Failed to connect to target for command: {command}")
                return
        response = self.tcp_client.send_command(command)
        if response:
            print(f"Command '{command}' -> Response: {response}")

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
            if position < 0:
                position = 0
            elif position > 100:
                position = 100
            self._send_target_command(f"SET_VALVE{valve_id}:{position}")
        elif component_type == "mechanical_pump":
            power = int(command)
            if power < 0:
                power = 0
            elif power > 100:
                power = 100
            self._send_target_command(f"SET_MECHANICAL_PUMP:{power}")
        elif component_type == "turbo_pump":
            power = int(command)
            if power < 0:
                power = 0
            elif power > 100:
                power = 100
            self._send_target_command(f"SET_TURBO_PUMP:{power}")


# ============================================================
#  FSM: states + events
# ============================================================

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


# ============================================================
#  AutoController: full 12-state FSM implementation
# ============================================================

class AutoController:
    def __init__(self, components):
        """
        components: dict with keys:
          "power_supply", "atm_valve", "foreline_valve", "fusor_valve",
          "mech_pump", "turbo_pump", "deuterium_valve"
        """
        self.components = components
        self.currentState = State.ALL_OFF

        # (state, event) -> next_state
        self.FSM = {
            (State.ALL_OFF, Event.START): State.ROUGH_PUMP_DOWN,

            (State.ROUGH_PUMP_DOWN, Event.APS_FORELINE_LT_100MT): State.RP_DOWN_TURBO,

            (State.RP_DOWN_TURBO, Event.APS_TURBO_LT_100MT): State.TURBO_PUMP_DOWN,
            (State.RP_DOWN_TURBO, Event.FAULT_FORELINE_TURBO): State.ALL_OFF,  # fault → safe

            (State.TURBO_PUMP_DOWN, Event.APS_TURBO_LT_0_1MT): State.TP_DOWN_MAIN,

            (State.TP_DOWN_MAIN, Event.APS_MAIN_LT_0_1MT): State.SETTLE_STEADY_PRESSURE,
            (State.TP_DOWN_MAIN, Event.FAULT_MAIN_TURBO): State.ALL_OFF,  # fault → safe

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

        # Start in All Off
        self._enter_state(State.ALL_OFF)

    # ------------ helper: voltage in kV ------------

    def _set_voltage_kv(self, kv: float):
        self.components["power_supply"].setAnalogValue(kv * 1000.0)

    # ------------ public: feed events into FSM ------------

    def dispatch_event(self, event: Event):
        print(f"\nEvent: {event.name} in state {self.currentState.name}")
        key = (self.currentState, event)
        next_state = self.FSM.get(key)
        if next_state is None:
            print(" -> no transition, staying in", self.currentState.name)
            return
        self._enter_state(next_state)

    # ------------ internal: enter state ------------

    def _enter_state(self, new_state: State):
        print(f"\n=== ENTER STATE: {new_state.name} ===")
        self.currentState = new_state
        action = self._state_entry_actions.get(new_state)
        if action:
            action()

    # ------------ 12 state entry actions (matching your spec) ------------

    def _enter_all_off(self):
        """
        1. All Off
        Atm valve: Closed
        Roughing Pump: Off
        APS: Foreline (logical)
        Turbo Pump: Off
        Foreline Valve: Closed
        Turbo Valve: Closed (not modeled)
        Vacuum System Valve (fusor_valve): Closed
        Deuterium Supply Valve: Closed
        PID: Off, Setpoints N/A
        """
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(False)
        c["turbo_pump"].setDigitalValue(False)
        c["foreline_valve"].setDigitalValue(False)
        c["fusor_valve"].setDigitalValue(False)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_rough_pump_down(self):
        """
        2. Rough Pump Down
        Atm valve: Closed
        Roughing Pump: On
        APS: Foreline
        Turbo Pump: Off
        Foreline Valve: Closed
        Vacuum System Valve: Closed
        Deuterium Valve: Closed
        """
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(False)
        c["foreline_valve"].setDigitalValue(False)
        c["fusor_valve"].setDigitalValue(False)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_rp_down_turbo(self):
        """
        3. RP Down Turbo Chamber
        Atm valve: Closed
        Roughing Pump: On
        APS: Turbo
        Turbo Pump: Off
        Foreline Valve: Open
        Vacuum System Valve: Closed
        Deuterium Valve: Closed
        """
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(False)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(False)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_turbo_pump_down(self):
        """
        4. Turbo Pump Down
        Atm valve: Closed
        Roughing Pump: On
        APS: Turbo
        Turbo Pump: On
        Foreline Valve: Open
        Vacuum System Valve: Closed
        Deuterium Valve: Closed
        """
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(False)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_tp_down_main(self):
        """
        5. TP Down Main Chamber
        Atm valve: Closed
        Roughing Pump: On
        APS: Main
        Turbo Pump: On
        Foreline Valve: Open
        Vacuum System Valve: Open
        Deuterium Valve: Closed
        """
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_settle_steady_pressure(self):
        """
        6. Settle to Steady State Pressure
        Atm valve: Closed
        Roughing Pump: On
        APS: Main
        Turbo Pump: On
        Foreline Valve: Open
        Vacuum System Valve: PID Controlled
        Deuterium Valve: PID Controlled
        PID: 1
        Current/Voltage disabled
        Pressure P(s): 0.1 mT
        """
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(True)
        self._set_voltage_kv(0)

    def _enter_settling_10kv(self):
        """
        7. System Settling to 10 kV Setpoint
        PID: 2
        Current e(t)=0
        Voltage: 10 kV
        Pressure disabled
        """
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(True)
        self._set_voltage_kv(10)

    def _enter_admit_fuel_5ma(self):
        """
        8. Admitting Fuel Until I = 5 mA
        PID: 3
        Current: 5 mA
        Voltage: 10 kV
        """
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(True)
        self._set_voltage_kv(10)

    def _enter_nominal_27kv(self):
        """
        9. 27 kV Nominal Operation
        PID: 4
        Current: e(t) = max(0, i(t) - 12mA)
        Voltage: 27 kV
        """
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(True)
        self._set_voltage_kv(27)

    def _enter_deenergizing(self):
        """
        10. Fusor De-energizing
        PID: 4
        Current: e(t) = max(0, i(t) - 12mA)
        Voltage: 0 kV
        """
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_closing_main(self):
        """
        11. Closing off Main Chamber
        Atm valve: Closed
        Roughing Pump: On
        APS: Turbo
        Turbo Pump: On
        Foreline Valve: Open
        Vacuum System Valve: Closed
        Deuterium Valve: Closed
        PID: 1, Pressure error e(t)=0
        """
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(False)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)

    def _enter_venting_foreline(self):
        """
        12. Venting Foreline
        Atm valve: Closed
        Roughing Pump: On
        APS: Foreline
        Turbo Pump: On
        Foreline Valve: Open
        Vacuum System Valve: PID Controlled
        Deuterium Valve: Closed
        PID: 1, Pressure P(s): 50 mTorr
        """
        c = self.components
        c["atm_valve"].setDigitalValue(False)
        c["mech_pump"].setDigitalValue(True)
        c["turbo_pump"].setDigitalValue(True)
        c["foreline_valve"].setDigitalValue(True)
        c["fusor_valve"].setDigitalValue(True)
        c["deuterium_valve"].setDigitalValue(False)
        self._set_voltage_kv(0)


# ============================================================
#  Telemetry → FSM event mapper
# ============================================================

class TelemetryToEventMapper:
    def __init__(self, controller: AutoController):
        self.controller = controller

    def handle_telemetry(self, telemetry: dict):
        """
        Expected telemetry format from Pi (edit as needed):
        {
          "APS_location": "Foreline" | "Turbo" | "Main",
          "APS_pressure_mT": float,
          "voltage_kV": float,
          "current_mA": float,
          "APS_atm_flag": bool
        }
        """
        aps_loc = telemetry.get("APS_location")
        aps_p = telemetry.get("APS_pressure_mT")
        v_kv = telemetry.get("voltage_kV")
        i_mA = telemetry.get("current_mA")
        aps_atm_flag = telemetry.get("APS_atm_flag", False)

        s = self.controller.currentState

        # Pressure-based transitions
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

        # Voltage-based
        if s == State.SETTLING_10KV and v_kv is not None:
            if 9.8 <= v_kv <= 10.2:
                self.controller.dispatch_event(Event.STEADY_STATE_VOLTAGE)

        # Current-based
        if s == State.ADMIT_FUEL_TO_5MA and i_mA is not None:
            if 4.8 <= i_mA <= 5.2:
                self.controller.dispatch_event(Event.STEADY_STATE_CURRENT)

        # De-energize to 0kV
        if s == State.DEENERGIZING and v_kv is not None:
            if abs(v_kv) < 0.1:
                self.controller.dispatch_event(Event.ZERO_KV_STEADY)

        # Vent complete: APS = 1 atm
        if s == State.VENTING_FORELINE and aps_atm_flag:
            self.controller.dispatch_event(Event.APS_EQ_1_ATM)


# ============================================================
#  CustomTkinter UI: Manual, Auto, Mode Select
# ============================================================

class ManualControlFrame(ctk.CTkFrame):
    def __init__(self, master, fusorComponents, **kwargs):
        super().__init__(master, **kwargs)
        self.fusorComponents = fusorComponents  # dict
        self._build_ui()

    def _build_ui(self):
        self.label = ctk.CTkLabel(self, text="Manual Control", font=("Helvetica", 18, "bold"))
        self.label.pack(pady=10)

        # Example: Mech Pump analog control (if used)
        self.mech_slider = ctk.CTkSlider(
            self, from_=0.0, to=100.0, command=self.on_mech_slider_change
        )
        self.mech_slider.pack(pady=10)
        self.mech_slider_label = ctk.CTkLabel(self, text="Mech Vacuum Control (%)")
        self.mech_slider_label.pack()

        # Pressure display
        self.pressure_label = ctk.CTkLabel(self, text="Pressure Sensor 1: --- mT")
        self.pressure_label.pack(pady=20)

    def on_mech_slider_change(self, value):
        # Example mapping: slider → mech pump analog value (0–100)
        mech = self.fusorComponents["mech_pump"]
        mech.setAnalogValue(value)

    # used by UDP_Client
    def update_pressure_display(self, value):
        self.pressure_label.configure(text=f"Pressure Sensor 1: {value} mT")


class AutoControlFrame(ctk.CTkFrame):
    def __init__(self, master, controller: AutoController, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        self.label = ctk.CTkLabel(self, text="Auto Control", font=("Helvetica", 18, "bold"))
        self.label.pack(pady=10)

        self.start_button = ctk.CTkButton(self, text="Start Auto", command=self.on_start)
        self.start_button.pack(pady=5)

        self.stop_button = ctk.CTkButton(self, text="Stop Auto", command=self.on_stop)
        self.stop_button.pack(pady=5)

        self.state_label = ctk.CTkLabel(self, text="State: ALL_OFF")
        self.state_label.pack(pady=20)

    def on_start(self):
        self.controller.dispatch_event(Event.START)
        self._update_state_label()

    def on_stop(self):
        self.controller.dispatch_event(Event.STOP_CMD)
        self._update_state_label()

    def _update_state_label(self):
        self.state_label.configure(text=f"State: {self.controller.currentState.name}")


class ModeSelectFrame(ctk.CTkFrame):
    def __init__(self, master, manual_frame, auto_frame, **kwargs):
        super().__init__(master, **kwargs)
        self.manual_frame = manual_frame
        self.auto_frame = auto_frame
        self._build_ui()

    def _build_ui(self):
        self.label = ctk.CTkLabel(self, text="Mode Select", font=("Helvetica", 16, "bold"))
        self.label.pack(pady=5)

        self.manual_button = ctk.CTkButton(self, text="Manual", command=self.show_manual)
        self.manual_button.pack(pady=5)

        self.auto_button = ctk.CTkButton(self, text="Auto", command=self.show_auto)
        self.auto_button.pack(pady=5)

    def show_manual(self):
        self.auto_frame.pack_forget()
        self.manual_frame.pack(fill="both", expand=True)

    def show_auto(self):
        self.manual_frame.pack_forget()
        self.auto_frame.pack(fill="both", expand=True)


# ============================================================
#  UDP Status Handler: Wrapper for UDPStatusReceiver
# ============================================================

class UDPStatusHandler:
    def __init__(self, manual_frame, telemetry_callback, listen_port=8888):
        self.manual_frame = manual_frame
        self.telemetry_callback = telemetry_callback
        self.udp_receiver = UDPStatusReceiver(
            listen_port=listen_port,
            callback=self._handle_message
        )
    
    def _handle_message(self, message: str, address: tuple):
        try:
            msg = json.loads(message)
            identifier = msg.get("id")
            value = msg.get("value")
            if identifier == "Pressure Sensor 1" and value is not None:
                if hasattr(self.manual_frame, 'update_pressure_display'):
                    self.manual_frame.update_pressure_display(value)
            
            telemetry = msg.get("telemetry")
            if telemetry and self.telemetry_callback:
                self.telemetry_callback(telemetry)
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"UDP Status Handler error: {e}")
    
    def startDisplayingRealTimeData(self):
        self.udp_receiver.start()
    
    def stopDisplayingRealTimeData(self):
        self.udp_receiver.stop()


# ============================================================
#  Main Application
# ============================================================

class FusorApp(ctk.CTk):
    def __init__(self, target_ip: str = "192.168.0.2", target_tcp_port: int = 2222):
        super().__init__()
        self.title("Fusor Control GUI")
        self.geometry("800x600")
        
        self.target_ip = target_ip
        self.target_tcp_port = target_tcp_port
        
        self.tcp_command_client = TCPCommandClient(
            target_ip=target_ip,
            target_port=target_tcp_port
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

        self.powerSupply = FusorComponent("Main Supply", self.tcp_command_client, component_map)
        self.atmValve = FusorComponent("Atm Depressure Valve", self.tcp_command_client, component_map)
        self.forelineValve = FusorComponent("Foreline Valve", self.tcp_command_client, component_map)
        self.fusorValve = FusorComponent("Vacuum System Valve", self.tcp_command_client, component_map)
        self.mechPump = FusorComponent("Roughing Pump", self.tcp_command_client, component_map)
        self.turboPump = FusorComponent("Turbo Pump", self.tcp_command_client, component_map)
        self.deuteriumValve = FusorComponent("Deuterium Supply Valve", self.tcp_command_client, component_map)

        self.components = {
            "power_supply": self.powerSupply,
            "atm_valve": self.atmValve,
            "foreline_valve": self.forelineValve,
            "fusor_valve": self.fusorValve,
            "mech_pump": self.mechPump,
            "turbo_pump": self.turboPump,
            "deuterium_valve": self.deuteriumValve,
        }

        self.auto_controller = AutoController(self.components)

        self.telemetry_mapper = TelemetryToEventMapper(self.auto_controller)

        self.manual_frame = ManualControlFrame(self, self.components)
        self.auto_frame = AutoControlFrame(self, self.auto_controller)

        self.mode_frame = ModeSelectFrame(self, self.manual_frame, self.auto_frame)
        self.mode_frame.pack(side="top", fill="x")

        self.manual_frame.pack(fill="both", expand=True)

        self.udp_status_handler = UDPStatusHandler(
            manual_frame=self.manual_frame,
            telemetry_callback=self.telemetry_mapper.handle_telemetry,
            listen_port=8888
        )
        self.udp_status_handler.startDisplayingRealTimeData()
        
        self.tcp_data_client = TCPDataClient(
            target_ip=target_ip,
            target_port=12345,
            data_callback=self._handle_data_message
        )
        self.tcp_data_client.start()
    
    def _handle_data_message(self, data: str):
        try:
            if hasattr(self, 'manual_frame') and hasattr(self.manual_frame, 'update_data_display'):
                self.manual_frame.update_data_display(data)
        except Exception as e:
            print(f"Error handling data message: {e}")


# ============================================================
#  Run app
# ============================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = FusorApp()
    app.mainloop()
