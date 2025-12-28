"""
Flask Web API Server for Farnsworth Fusor Control System
Bridges the web interface to the existing TCP/UDP communication system
"""

import sys
import os
import json
import logging
import threading
import time
from typing import Optional, Dict, Any
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

# Add parent directory to path to import Host_Codebase modules
sys.path.insert(0, os.path.dirname(__file__))

from tcp_command_client import TCPCommandClient
from udp_data_client import UDPDataClient
from udp_status_client import UDPStatusClient, UDPStatusReceiver
from command_handler import CommandHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WebAPIServer")

app = Flask(__name__)

# CORS Configuration
# Allow localhost origins for local development
# Can be customized via CORS_ORIGINS environment variable
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8080,http://localhost:3000,http://localhost:5000"
).split(",")

CORS(app, resources={
    r"/api/*": {
        "origins": CORS_ORIGINS,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

logger.info(f"CORS enabled for origins: {CORS_ORIGINS}")

# Configuration
TARGET_IP = os.getenv("TARGET_IP", "192.168.0.2")
TCP_COMMAND_PORT = int(os.getenv("TCP_COMMAND_PORT", "2222"))
UDP_DATA_PORT = int(os.getenv("UDP_DATA_PORT", "12345"))
UDP_STATUS_PORT = int(os.getenv("UDP_STATUS_PORT", "8888"))

# Global clients
tcp_client: Optional[TCPCommandClient] = None
udp_data_client: Optional[UDPDataClient] = None
udp_status_client: Optional[UDPStatusClient] = None
udp_status_receiver: Optional[UDPStatusReceiver] = None
command_handler = CommandHandler()

# Global state
app_state = {
    "connected": False,
    "auto_state": "ALL_OFF",
    "auto_mode_active": False,
    "telemetry": {},
    "status_messages": [],
    "target_logs": [],
    "last_update": None
}

# Lock for thread-safe operations
_state_lock = threading.Lock()


def init_clients():
    """Initialize TCP/UDP clients"""
    global tcp_client, udp_data_client, udp_status_client, udp_status_receiver
    
    logger.info("Initializing TCP/UDP clients...")
    
    tcp_client = TCPCommandClient(TARGET_IP, TCP_COMMAND_PORT)
    
    udp_data_client = UDPDataClient(
        target_ip=TARGET_IP,
        target_port=UDP_DATA_PORT,
        data_callback=handle_udp_data
    )
    
    udp_status_client = UDPStatusClient(TARGET_IP, 8889)
    udp_status_client.start()
    
    udp_status_receiver = UDPStatusReceiver(
        listen_port=UDP_STATUS_PORT,
        callback=handle_udp_status
    )
    
    # Start UDP receivers
    udp_data_client.start()
    udp_status_receiver.start()
    
    # Try to connect TCP
    if tcp_client.connect():
        with _state_lock:
            app_state["connected"] = True
        logger.info("TCP connection established")
    else:
        logger.warning("TCP connection failed on startup - will retry on first command")
    
    logger.info("Clients initialized")


def handle_udp_data(data: str):
    """Handle incoming UDP data telemetry"""
    try:
        # Parse telemetry data
        telemetry = {}
        parts = data.split("|")
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                key = key.strip()
                value = value.strip()
                telemetry[key] = value
        
        with _state_lock:
            app_state["telemetry"].update(telemetry)
            app_state["last_update"] = datetime.now().isoformat()
        
        logger.debug(f"Received telemetry: {telemetry}")
    except Exception as e:
        logger.error(f"Error handling UDP data: {e}")


def handle_udp_status(message: str, address: tuple):
    """Handle incoming UDP status messages"""
    try:
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}"
        
        with _state_lock:
            app_state["target_logs"].append(log_entry)
            # Keep only last 1000 log entries
            if len(app_state["target_logs"]) > 1000:
                app_state["target_logs"] = app_state["target_logs"][-1000:]
        
        logger.debug(f"Received status from {address}: {message}")
    except Exception as e:
        logger.error(f"Error handling UDP status: {e}")


def send_command(command: str) -> Dict[str, Any]:
    """Send command to target and return response"""
    global tcp_client
    
    if not tcp_client:
        return {"success": False, "error": "TCP client not initialized"}
    
    try:
        # Ensure connection
        if not tcp_client.is_connected():
            with _state_lock:
                app_state["connected"] = False
            
            if not tcp_client.connect():
                return {
                    "success": False,
                    "error": f"Failed to connect to {TARGET_IP}:{TCP_COMMAND_PORT}"
                }
            
            with _state_lock:
                app_state["connected"] = True
        
        # Send command
        response = tcp_client.send_command(command)
        
        return {
            "success": True,
            "command": command,
            "response": response or "No response"
        }
    except Exception as e:
        logger.error(f"Error sending command {command}: {e}")
        with _state_lock:
            app_state["connected"] = False
        return {"success": False, "error": str(e)}


# Valve name to ID mapping
VALVE_MAPPING = {
    "atm_valve": 1,
    "foreline_valve": 2,
    "fusor_valve": 3,
    "deuterium_valve": 4
}


# API Endpoints

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get connection status and system state"""
    with _state_lock:
        return jsonify({
            "connected": app_state["connected"],
            "auto_state": app_state["auto_state"],
            "auto_mode_active": app_state["auto_mode_active"],
            "target_ip": TARGET_IP,
            "tcp_port": TCP_COMMAND_PORT,
            "last_update": app_state["last_update"]
        })


@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    """Get latest telemetry data"""
    with _state_lock:
        return jsonify({
            "telemetry": app_state["telemetry"],
            "last_update": app_state["last_update"]
        })


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get target logs"""
    limit = request.args.get('limit', 100, type=int)
    with _state_lock:
        logs = app_state["target_logs"][-limit:] if limit > 0 else app_state["target_logs"]
        return jsonify({"logs": logs, "count": len(logs)})


@app.route('/api/command/send', methods=['POST'])
def send_command_endpoint():
    """Send a raw command to the target"""
    data = request.get_json()
    command = data.get('command')
    
    if not command:
        return jsonify({"success": False, "error": "No command provided"}), 400
    
    result = send_command(command)
    return jsonify(result)


@app.route('/api/voltage/set', methods=['POST'])
def set_voltage():
    """Set voltage output"""
    data = request.get_json()
    voltage = data.get('voltage')
    
    if voltage is None:
        return jsonify({"success": False, "error": "No voltage provided"}), 400
    
    try:
        voltage = int(voltage)
        if voltage < 0 or voltage > 28000:
            return jsonify({"success": False, "error": "Voltage out of range (0-28000)"}), 400
        
        command = command_handler.build_set_voltage_command(voltage)
        if not command:
            return jsonify({"success": False, "error": "Failed to build command"}), 500
        
        # Enable/disable power supply based on voltage
        if voltage > 0:
            enable_result = send_command("POWER_SUPPLY_ENABLE")
            if not enable_result["success"]:
                return jsonify(enable_result), 500
        
        result = send_command(command)
        return jsonify(result)
    except ValueError:
        return jsonify({"success": False, "error": "Invalid voltage value"}), 400


@app.route('/api/pump/mechanical', methods=['POST'])
def set_mechanical_pump():
    """Set mechanical pump power"""
    data = request.get_json()
    power = data.get('power')
    
    if power is None:
        return jsonify({"success": False, "error": "No power provided"}), 400
    
    try:
        power = int(power)
        if power < 0 or power > 100:
            return jsonify({"success": False, "error": "Power out of range (0-100)"}), 400
        
        command = command_handler.build_set_mechanical_pump_command(power)
        if not command:
            return jsonify({"success": False, "error": "Failed to build command"}), 500
        
        result = send_command(command)
        return jsonify(result)
    except ValueError:
        return jsonify({"success": False, "error": "Invalid power value"}), 400


@app.route('/api/pump/turbo', methods=['POST'])
def set_turbo_pump():
    """Set turbo pump power"""
    data = request.get_json()
    power = data.get('power')
    
    if power is None:
        return jsonify({"success": False, "error": "No power provided"}), 400
    
    try:
        power = int(power)
        if power < 0 or power > 100:
            return jsonify({"success": False, "error": "Power out of range (0-100)"}), 400
        
        command = command_handler.build_set_turbo_pump_command(power)
        if not command:
            return jsonify({"success": False, "error": "Failed to build command"}), 500
        
        result = send_command(command)
        return jsonify(result)
    except ValueError:
        return jsonify({"success": False, "error": "Invalid power value"}), 400


@app.route('/api/valve/set', methods=['POST'])
def set_valve():
    """Set valve position"""
    data = request.get_json()
    valve_name = data.get('valve')
    position = data.get('position')
    
    if not valve_name or position is None:
        return jsonify({"success": False, "error": "Missing valve name or position"}), 400
    
    try:
        position = int(position)
        if position < 0 or position > 100:
            return jsonify({"success": False, "error": "Position out of range (0-100)"}), 400
        
        # Map valve name to ID
        valve_id = VALVE_MAPPING.get(valve_name)
        if not valve_id:
            return jsonify({"success": False, "error": f"Unknown valve: {valve_name}"}), 400
        
        command = command_handler.build_set_valve_command(valve_id, position)
        if not command:
            return jsonify({"success": False, "error": "Failed to build command"}), 500
        
        result = send_command(command)
        return jsonify(result)
    except ValueError:
        return jsonify({"success": False, "error": "Invalid position value"}), 400


@app.route('/api/auto/start', methods=['POST'])
def auto_start():
    """Start auto sequence"""
    with _state_lock:
        if app_state["auto_mode_active"]:
            return jsonify({"success": False, "error": "Auto sequence already running"}), 400
        
        app_state["auto_mode_active"] = True
        app_state["auto_state"] = "ROUGH_PUMP_DOWN"
    
    return jsonify({"success": True, "message": "Auto sequence started", "state": "ROUGH_PUMP_DOWN"})


@app.route('/api/auto/stop', methods=['POST'])
def auto_stop():
    """Stop auto sequence"""
    with _state_lock:
        app_state["auto_mode_active"] = False
        app_state["auto_state"] = "ALL_OFF"
    
    return jsonify({"success": True, "message": "Auto sequence stopped", "state": "ALL_OFF"})


@app.route('/api/auto/state', methods=['GET'])
def get_auto_state():
    """Get current auto state"""
    with _state_lock:
        return jsonify({
            "state": app_state["auto_state"],
            "active": app_state["auto_mode_active"]
        })


@app.route('/api/auto/state', methods=['POST'])
def set_auto_state():
    """Update auto state (for state machine transitions)"""
    data = request.get_json()
    state = data.get('state')
    
    if not state:
        return jsonify({"success": False, "error": "No state provided"}), 400
    
    with _state_lock:
        app_state["auto_state"] = state
    
    return jsonify({"success": True, "state": state})


@app.route('/api/emergency/stop', methods=['POST'])
def emergency_stop():
    """Emergency stop - shut down all systems"""
    results = []
    
    # Turn off all valves
    for valve_name in VALVE_MAPPING.keys():
        valve_id = VALVE_MAPPING.get(valve_name)
        if valve_id:
            command = command_handler.build_set_valve_command(valve_id, 0)
            if command:
                results.append(send_command(command))
    
    # Turn off pumps
    mech_cmd = command_handler.build_set_mechanical_pump_command(0)
    if mech_cmd:
        results.append(send_command(mech_cmd))
    
    turbo_cmd = command_handler.build_set_turbo_pump_command(0)
    if turbo_cmd:
        results.append(send_command(turbo_cmd))
    
    # Disable power supply
    results.append(send_command("POWER_SUPPLY_DISABLE"))
    voltage_cmd = command_handler.build_set_voltage_command(0)
    if voltage_cmd:
        results.append(send_command(voltage_cmd))
    
    # Stop auto mode
    with _state_lock:
        app_state["auto_mode_active"] = False
        app_state["auto_state"] = "ALL_OFF"
    
    return jsonify({
        "success": True,
        "message": "Emergency stop activated",
        "results": results
    })


@app.route('/api/sensors/read', methods=['GET'])
def read_sensors():
    """Read sensor data (ADC, voltage, current, pressure)"""
    commands = [
        "READ_ACTIVE_ADC_CHANNELS",
        "READ_NODE_VOLTAGE:1",  # Rectifier
        "READ_NODE_VOLTAGE:2",  # Transformer
        "READ_NODE_VOLTAGE:3",  # V-Multiplier
        "READ_NODE_CURRENT:1",  # Rectifier
        "READ_NODE_CURRENT:3",  # V-Multiplier
    ]
    
    results = {}
    for cmd in commands:
        result = send_command(cmd)
        if result["success"]:
            results[cmd] = result["response"]
    
    return jsonify({"success": True, "sensors": results})


# Initialize clients on startup
init_clients()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Farnsworth Fusor Web API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    logger.info("Starting Web API Server...")
    logger.info(f"API Server: http://{args.host}:{args.port}")
    logger.info(f"Target IP: {TARGET_IP}, TCP Port: {TCP_COMMAND_PORT}")
    logger.info(f"UDP Data Port: {UDP_DATA_PORT}, UDP Status Port: {UDP_STATUS_PORT}")
    
    # Run Flask app
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
