# Farnsworth Fusor Web Interface

Web-based control interface for the Farnsworth Fusor Control System.

## Developer notes

This directory was initally made to support a production website that runs using local rasperberry pi data. Due to the misconfig between a web production server and a local connection - more work will need to be done to figure out a proper soultion

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

The server will start on `http://localhost:5000` by default.

You can customize the host and port:

```bash
python web_api_server.py --host 0.0.0.0 --port 5000
```

3. Open the web interface:

- Open `index.html` in a web browser, or
- Serve it via a web server (e.g., Python's HTTP server):

```bash
python -m http.server 8080
```

Then navigate to `http://localhost:8080`

## Configuration

### API Server Configuration

The API server can be configured via environment variables or command-line arguments:

**Environment Variables:**

- `TARGET_IP`: Raspberry Pi IP address (default: `192.168.0.2`)
- `TCP_COMMAND_PORT`: TCP command port (default: `2222`)
- `UDP_DATA_PORT`: UDP data port (default: `12345`)
- `UDP_STATUS_PORT`: UDP status port (default: `8888`)

**Command-Line Arguments:**

- `--host`: Host to bind to (default: `0.0.0.0` - allows external connections)
- `--port`: Port to bind to (default: `5000`)
- `--debug`: Enable debug mode

**Examples:**

```bash
# Custom target IP
export TARGET_IP=192.168.0.3
python web_api_server.py

# Custom API server port
python web_api_server.py --port 8080

# Allow connections from other machines on your network
python web_api_server.py --host 0.0.0.0 --port 5000
```

### Web Interface Configuration

The web interface **automatically detects** the API URL based on your environment:

- **Development (localhost)**: Uses `http://localhost:5000/api`
- **Production (same host)**: Uses `http://your-hostname:5000/api`

**Manual Override (if needed):**

If your API server is on a different host/port, edit `index.html` and set:

```html
<script>
  window.API_BASE_URL = "http://localhost:5001/api"; // Example: different port
</script>
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
- Check browser console for API errors (F12 → Console tab)
- Verify the Raspberry Pi target is running and accessible
- Check firewall settings for TCP/UDP ports
- **CORS errors**: Check that API server is running and accessible at `http://localhost:5000`
