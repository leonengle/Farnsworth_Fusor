# Farnsworth Fusor Web Interface

Web-based control interface for the Farnsworth Fusor Control System.

## Setup

1. Install Python dependencies:

```bash
pip install -r ../requirements.txt
```

2. Start the web API server:

```bash
cd ../src/Host_Codebase
python web_api_server.py
```

The server will start on `http://localhost:5000`

3. Open the web interface:

- Open `index.html` in a web browser, or
- Serve it via a web server (e.g., Python's HTTP server):

```bash
python -m http.server 8080
```

Then navigate to `http://localhost:8080`

## Configuration

The API server can be configured via environment variables:

- `TARGET_IP`: Raspberry Pi IP address (default: `192.168.0.2`)
- `TCP_COMMAND_PORT`: TCP command port (default: `2222`)
- `UDP_DATA_PORT`: UDP data port (default: `12345`)
- `UDP_STATUS_PORT`: UDP status port (default: `8888`)

Example:

```bash
export TARGET_IP=192.168.0.3
python web_api_server.py
```

## API Endpoints

- `GET /api/status` - Get connection status
- `GET /api/telemetry` - Get latest telemetry data
- `GET /api/logs` - Get target logs
- `POST /api/voltage/set` - Set voltage (body: `{"voltage": 14000}`)
- `POST /api/pump/mechanical` - Set mechanical pump (body: `{"power": 100}`)
- `POST /api/pump/turbo` - Set turbo pump (body: `{"power": 100}`)
- `POST /api/valve/set` - Set valve (body: `{"valve": "atm_valve", "position": 50}`)
- `POST /api/auto/start` - Start auto sequence
- `POST /api/auto/stop` - Stop auto sequence
- `POST /api/emergency/stop` - Emergency stop
- `GET /api/sensors/read` - Read sensor data

## Features

- **Real-time Updates**: Polling every 1-3 seconds for telemetry and status
- **Manual Control**: Control voltage, pumps, and valves
- **Auto Control**: Start/stop automated sequences
- **Data Monitoring**: View sensor readings and logs
- **Emergency Stop**: Immediately shut down all systems

## Troubleshooting

- If the web interface can't connect, ensure the API server is running on port 5000
- Check browser console for API errors
- Verify the Raspberry Pi target is running and accessible
- Check firewall settings for TCP/UDP ports
