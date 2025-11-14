import customtkinter as ctk
import socket
import json
import threading
from enum import Enum, auto

# ============================================================
#  Networking: RPi command connection (UDP or TCP)
# ============================================================

class RPiConnection:
    def __init__(self, host="192.168.1.50", port=5005, use_udp=True):
        """
        host / port: address of Raspberry Pi command listener
        use_udp: True for UDP, False for TCP
        """
        self.host = host
        self.port = port
        self.use_udp = use_udp

        if not use_udp:
            # TCP
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
        else:
            # UDP
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_command(self, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        if self.use_udp:
            self.sock.sendto(data, (self.host, self.port))
        else:
            self.sock.sendall(data)


# Global-ish RPi command connection (edit host/port as needed)
rpi_conn = RPiConnection(host="192.168.1.50", port=5005, use_udp=True)


def TCP_send(name, command):
    """
    name: component name (string)
    command: arbitrary dict payload
    """
    payload = {
        "component": name,
        "command": command,
    }
    rpi_conn.send_command(payload)


# ============================================================
#  Fusor components
# ============================================================

class FusorComponent:
    def __init__(self, name: str):
        self.name = name

    def setDigitalValue(self, command: bool):
        TCP_send(self.name, {"type": "digital", "value": bool(command)})

    def setAnalogValue(self, command: float):
        # For HV: 27 => 27kV -> 27000
        TCP_send(self.name, {"type": "analog", "value": float(command)})


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
#  UDP_Client: Telemetry receiver → UI + TelemetryToEventMapper
# ============================================================

class UDP_Client:
    def __init__(self, manual_frame: ManualControlFrame,
                 telemetry_callback,
                 listen_host="0.0.0.0", listen_port=5006):
        """
        telemetry_callback: function(telemetry_dict)
        """
        self.manual_frame = manual_frame
        self.telemetry_callback = telemetry_callback
        self.listen_host = listen_host
        self.listen_port = listen_port
        self._stop_flag = threading.Event()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.listen_host, self.listen_port))

    def startDisplayingRealTimeData(self):
        t = threading.Thread(target=self._listen_loop, daemon=True)
        t.start()

    def stopDisplayingRealTimeData(self):
        self._stop_flag.set()

    def _listen_loop(self):
        while not self._stop_flag.is_set():
            try:
                data, addr = self.sock.recvfrom(4096)
                msg = json.loads(data.decode("utf-8"))

                # EXPECTED FORMAT (edit to match your Pi):
                # {
                #    "id": "Pressure Sensor 1",
                #    "value": 123.4,
                #    "telemetry": {... see TelemetryToEventMapper ...}
                # }

                identifier = msg.get("id")
                value = msg.get("value")
                if identifier == "Pressure Sensor 1" and value is not None:
                    # NOTE: technically UI updates from background threads are unsafe,
                    # but often work. For strict safety use an event queue + root.after.
                    self.manual_frame.update_pressure_display(value)

                telemetry = msg.get("telemetry")
                if telemetry and self.telemetry_callback:
                    self.telemetry_callback(telemetry)

            except Exception as e:
                print("UDP_Client error:", e)


# ============================================================
#  Main Application
# ============================================================

class FusorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Fusor Control GUI")
        self.geometry("800x600")

        # Create hardware abstraction
        self.powerSupply = FusorComponent("Main Supply")
        self.atmValve = FusorComponent("Atm Depressure Valve")
        self.forelineValve = FusorComponent("Foreline Valve")
        self.fusorValve = FusorComponent("Vacuum System Valve")
        self.mechPump = FusorComponent("Roughing Pump")
        self.turboPump = FusorComponent("Turbo Pump")
        self.deuteriumValve = FusorComponent("Deuterium Supply Valve")

        self.components = {
            "power_supply": self.powerSupply,
            "atm_valve": self.atmValve,
            "foreline_valve": self.forelineValve,
            "fusor_valve": self.fusorValve,
            "mech_pump": self.mechPump,
            "turbo_pump": self.turboPump,
            "deuterium_valve": self.deuteriumValve,
        }

        # FSM controller
        self.auto_controller = AutoController(self.components)

        # Telemetry → FSM mapper
        self.telemetry_mapper = TelemetryToEventMapper(self.auto_controller)

        # Frames
        self.manual_frame = ManualControlFrame(self, self.components)
        self.auto_frame = AutoControlFrame(self, self.auto_controller)

        # Mode select frame at top
        self.mode_frame = ModeSelectFrame(self, self.manual_frame, self.auto_frame)
        self.mode_frame.pack(side="top", fill="x")

        # Start with Manual visible
        self.manual_frame.pack(fill="both", expand=True)

        # UDP telemetry client
        self.udp_client = UDP_Client(
            manual_frame=self.manual_frame,
            telemetry_callback=self.telemetry_mapper.handle_telemetry,
            listen_host="0.0.0.0",
            listen_port=5006,  # edit as needed
        )
        self.udp_client.startDisplayingRealTimeData()


# ============================================================
#  Run app
# ============================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = FusorApp()
    app.mainloop()
