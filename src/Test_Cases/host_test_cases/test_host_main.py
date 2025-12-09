"""
Unit tests for Host Main module
Tests GUI initialization, command handling, and communication
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
import threading
import time

target_codebase_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "Host_Codebase"
)
sys.path.insert(0, target_codebase_path)

def create_mock_widget(*args, **kwargs):
    widget = MagicMock()
    widget.pack = MagicMock()
    widget.configure = MagicMock()
    widget.get = MagicMock(return_value=0)
    widget.set = MagicMock()
    widget.insert = MagicMock()
    widget.delete = MagicMock()
    widget.see = MagicMock()
    widget.winfo_exists = MagicMock(return_value=True)
    widget.lift = MagicMock()
    widget.focus = MagicMock()
    widget.destroy = MagicMock()
    widget.add = MagicMock(return_value=create_mock_widget())
    widget.select = MagicMock()
    widget.deselect = MagicMock()
    widget.after = MagicMock()
    widget.update = MagicMock()
    widget.update_idletasks = MagicMock()
    widget.protocol = MagicMock()
    widget.title = MagicMock()
    widget.geometry = MagicMock()
    widget.mainloop = MagicMock()
    return widget

mock_ctk = MagicMock()
mock_ctk.CTk = lambda *args, **kwargs: create_mock_widget()
mock_ctk.CTkFrame = lambda *args, **kwargs: create_mock_widget()
mock_ctk.CTkLabel = lambda *args, **kwargs: create_mock_widget()
mock_ctk.CTkButton = lambda *args, **kwargs: create_mock_widget()
mock_ctk.CTkSlider = lambda *args, **kwargs: create_mock_widget()
mock_ctk.CTkSwitch = lambda *args, **kwargs: create_mock_widget()
mock_ctk.CTkTabview = lambda *args, **kwargs: create_mock_widget()
mock_ctk.CTkTextbox = lambda *args, **kwargs: create_mock_widget()
mock_ctk.CTkToplevel = lambda *args, **kwargs: create_mock_widget()
mock_ctk.set_appearance_mode = MagicMock()
mock_ctk.set_default_color_theme = MagicMock()
mock_ctk.CTkFont = lambda *args, **kwargs: MagicMock()

sys.modules["customtkinter"] = mock_ctk

from host_main import (
    FusorHostApp,
    AutoController,
    State,
    Event,
    TelemetryToEventMapper,
    _build_actuator_command,
)


class TestBuildActuatorCommand(unittest.TestCase):
    def test_power_supply_command(self):
        result = _build_actuator_command("power supply", 14000)
        self.assertEqual(result, "SET_VOLTAGE:14000")

    def test_valve_commands(self):
        self.assertEqual(_build_actuator_command("atm valve", 50), "SET_VALVE1:50")
        self.assertEqual(_build_actuator_command("foreline valve", 75), "SET_VALVE2:75")
        self.assertEqual(_build_actuator_command("vacuum valve", 25), "SET_VALVE3:25")
        self.assertEqual(_build_actuator_command("deuterium valve", 100), "SET_VALVE4:100")

    def test_pump_commands(self):
        self.assertEqual(_build_actuator_command("mechanical pump", 100), "SET_MECHANICAL_PUMP:100")
        self.assertEqual(_build_actuator_command("roughing pump", 50), "SET_MECHANICAL_PUMP:50")
        self.assertEqual(_build_actuator_command("turbo pump", 100), "SET_TURBO_PUMP:100")

    def test_unknown_actuator(self):
        result = _build_actuator_command("unknown", 50)
        self.assertEqual(result, "")


class TestAutoController(unittest.TestCase):
    def setUp(self):
        self.mock_actuators = {
            "power_supply": MagicMock(),
            "atm_valve": MagicMock(),
            "foreline_valve": MagicMock(),
            "fusor_valve": MagicMock(),
            "deuterium_valve": MagicMock(),
            "mech_pump": MagicMock(),
            "turbo_pump": MagicMock(),
        }
        self.controller = AutoController(
            self.mock_actuators,
            state_callback=MagicMock(),
            log_callback=MagicMock(),
        )

    def test_initial_state(self):
        self.assertEqual(self.controller.currentState, State.ALL_OFF)

    def test_start_event(self):
        self.controller.dispatch_event(Event.STOP_CMD)
        self.assertEqual(self.controller.currentState, State.ALL_OFF)

    def test_enter_all_off(self):
        self.controller._enter_all_off()
        self.mock_actuators["power_supply"].setAnalogValue.assert_called()

    def test_set_voltage_kv(self):
        self.controller._set_voltage_kv(10.0)
        self.mock_actuators["power_supply"].setAnalogValue.assert_called_with(10000.0)

    def test_stop_from_any_state(self):
        self.controller.dispatch_event(Event.START)
        self.controller.dispatch_event(Event.STOP_CMD)
        self.assertEqual(self.controller.currentState, State.ALL_OFF)


class TestTelemetryToEventMapper(unittest.TestCase):
    def setUp(self):
        self.mock_controller = MagicMock()
        self.mock_controller.currentState = State.ALL_OFF
        self.mapper = TelemetryToEventMapper(self.mock_controller)

    def test_foreline_pressure_transition(self):
        self.mock_controller.currentState = State.ROUGH_PUMP_DOWN
        telemetry = {"APS_location": "Foreline", "APS_pressure_mT": 50.0}
        self.mapper.handle_telemetry(telemetry)
        self.mock_controller.dispatch_event.assert_called_with(Event.APS_FORELINE_LT_100MT)

    def test_turbo_pressure_transition(self):
        self.mock_controller.currentState = State.RP_DOWN_TURBO
        telemetry = {"APS_location": "Turbo", "APS_pressure_mT": 50.0}
        self.mapper.handle_telemetry(telemetry)
        self.mock_controller.dispatch_event.assert_called_with(Event.APS_TURBO_LT_100MT)

    def test_voltage_steady_state(self):
        self.mock_controller.currentState = State.SETTLING_10KV
        telemetry = {"voltage_kV": 10.0}
        self.mapper.handle_telemetry(telemetry)
        self.mock_controller.dispatch_event.assert_called_with(Event.STEADY_STATE_VOLTAGE)

    def test_current_steady_state(self):
        self.mock_controller.currentState = State.ADMIT_FUEL_TO_5MA
        telemetry = {"current_mA": 5.0}
        self.mapper.handle_telemetry(telemetry)
        self.mock_controller.dispatch_event.assert_called_with(Event.STEADY_STATE_CURRENT)


class TestFusorHostApp(unittest.TestCase):
    @patch("host_main.TCPCommandClient")
    @patch("host_main.UDPDataClient")
    @patch("host_main.UDPStatusClient")
    @patch("host_main.UDPStatusReceiver")
    @patch.object(FusorHostApp, "_setup_ui")
    def setUp(self, mock_setup_ui, mock_status_receiver, mock_status_client, mock_udp_data, mock_tcp):
        self.mock_tcp_client = MagicMock()
        self.mock_udp_data_client = MagicMock()
        self.mock_udp_status_client = MagicMock()
        self.mock_udp_status_receiver = MagicMock()

        mock_tcp.return_value = self.mock_tcp_client
        mock_udp_data.return_value = self.mock_udp_data_client
        mock_status_client.return_value = self.mock_udp_status_client
        mock_status_receiver.return_value = self.mock_udp_status_receiver

        self.mock_tcp_client.connect.return_value = True
        self.mock_tcp_client.is_connected.return_value = True

        mock_root = create_mock_widget()
        mock_setup_ui.return_value = None

        self.app = FusorHostApp(
            target_ip="127.0.0.1",
            target_tcp_command_port=2222,
            tcp_data_port=12345,
            udp_status_port=8888,
        )
        
        self.app.root = mock_root
        self.app.voltage_scale = create_mock_widget()
        self.app.voltage_value_label = create_mock_widget()
        self.app.voltage_set_button = create_mock_widget()
        self.app.manual_mech_switch = create_mock_widget()
        self.app.turbo_pump_switch = create_mock_widget()
        self.app.status_label = create_mock_widget()
        self.app.auto_state_label = create_mock_widget()
        self.app.auto_log_display = create_mock_widget()
        self.app.data_display = create_mock_widget()
        self.app.target_logs_display = create_mock_widget()
        self.app.valve_sliders = {}
        self.app.valve_value_labels = {}
        self.app.valve_set_buttons = {}

    def test_initialization(self):
        self.assertIsNotNone(self.app)
        self.assertIsNotNone(self.app.command_handler)
        self.assertIsNotNone(self.app.actuators)
        self.assertIn("power_supply", self.app.actuators)

    def test_actuators_initialized(self):
        self.assertIn("power_supply", self.app.actuators)
        self.assertIn("atm_valve", self.app.actuators)
        self.assertIn("foreline_valve", self.app.actuators)
        self.assertIn("fusor_valve", self.app.actuators)
        self.assertIn("deuterium_valve", self.app.actuators)
        self.assertIn("mech_pump", self.app.actuators)
        self.assertIn("turbo_pump", self.app.actuators)

    def test_auto_controller_initialized(self):
        self.assertIsNotNone(self.app.auto_controller)
        self.assertEqual(self.app.auto_controller.currentState, State.ALL_OFF)

    def test_telemetry_mapper_initialized(self):
        self.assertIsNotNone(self.app.telemetry_mapper)

    @patch.object(FusorHostApp, "_send_command")
    def test_set_voltage(self, mock_send):
        self.app.voltage_scale = MagicMock()
        self.app.voltage_scale.get.return_value = 14000
        self.app.command_handler = MagicMock()
        self.app.command_handler.build_set_voltage_command.return_value = "SET_VOLTAGE:14000"

        self.app._set_voltage()
        mock_send.assert_called()

    def test_is_auto_mode_active(self):
        self.app.auto_controller.currentState = State.ALL_OFF
        self.assertFalse(self.app._is_auto_mode_active())

        self.app.auto_controller.currentState = State.ROUGH_PUMP_DOWN
        self.assertTrue(self.app._is_auto_mode_active())

    def test_auto_start(self):
        self.app.auto_controller.currentState = State.ALL_OFF
        self.app._auto_start()
        self.app.auto_controller.dispatch_event.assert_called_with(Event.START)

    def test_auto_stop(self):
        self.app.auto_controller.currentState = State.ROUGH_PUMP_DOWN
        self.app._auto_stop()
        self.app.auto_controller.dispatch_event.assert_called_with(Event.STOP_CMD)

    def test_toggle_mech_pump(self):
        self.app.manual_mech_switch = MagicMock()
        self.app.manual_mech_switch.get.return_value = True
        self.app.auto_controller.currentState = State.ALL_OFF

        with patch.object(self.app, "_send_command") as mock_send:
            self.app._toggle_mech_pump()
            mock_send.assert_called()

    def test_toggle_turbo_pump(self):
        self.app.turbo_pump_switch = MagicMock()
        self.app.turbo_pump_switch.get.return_value = True
        self.app.auto_controller.currentState = State.ALL_OFF

        with patch.object(self.app, "_send_command") as mock_send:
            self.app._toggle_turbo_pump()
            mock_send.assert_called()

    def test_set_valve(self):
        self.app.auto_controller.currentState = State.ALL_OFF
        valve_actuator = self.app.actuators.get("atm_valve")
        if valve_actuator:
            with patch.object(valve_actuator, "setAnalogValue") as mock_set:
                self.app._set_valve("atm_valve", 50.0)
                mock_set.assert_called_with(50.0)

    def test_handle_udp_data(self):
        data = "TIME:12345|ADC_CH0:512|ADC_CH1:256"
        self.app._handle_udp_data(data)
        self.assertIsNotNone(self.app.previous_values)

    def test_handle_udp_status(self):
        message = "STATUS:Test status message"
        self.app._handle_udp_status(message, ("127.0.0.1", 8888))
        self.assertIsNotNone(self.app.previous_values)

    def test_parse_periodic_packet(self):
        payload = "TIME:12345|ADC_CH0:512|ADC_CH1:256"
        result = self.app._parse_periodic_packet(payload)
        self.assertIn("TIME", result)
        self.assertIn("ADC_CH0", result)
        self.assertEqual(result["ADC_CH0"], "512")

    def test_update_status(self):
        self.app._update_status("Test message", "green")
        self.app.status_label.configure.assert_called()

    def test_cleanup_on_closing(self):
        with patch.object(self.app, "stop") as mock_stop:
            self.app._on_closing()
            mock_stop.assert_called()


if __name__ == "__main__":
    unittest.main()

