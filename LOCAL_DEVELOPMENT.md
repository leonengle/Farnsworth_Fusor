# Local Development Guide

Quick guide to run the Farnsworth Fusor web interface and API server locally on your machine.

## Quick Start

### Option 1: Use the Startup Scripts (Easiest)

**Terminal 1 - Start API Server:**

```powershell
.\start-api-server.ps1
```

**Terminal 2 - Start Web Interface:**

```powershell
.\start-web-interface.ps1
```

That's it! The web interface will open in your browser automatically.

### Option 2: Manual Commands

**Terminal 1 - Start API Server:**

```powershell
cd src\Host_Codebase
python web_api_server.py
```

**Terminal 2 - Start Web Interface:**

```powershell
cd website
python -m http.server 8080
```

Then open your browser to: `http://localhost:8080`

## What's Running Where

```
┌─────────────────────────────────────────────────────────────┐
│  Your Local Machine                                         │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │   Browser    │  HTTP   │  Python API  │                │
│  │ localhost:8080│────────▶│ localhost:5000│                │
│  └──────────────┘         └──────┬───────┘                │
│                                   │ TCP/UDP                 │
└───────────────────────────────────┼─────────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │  Raspberry Pi   │
                          │   192.168.0.2   │
                          │  (Target)       │
                          └─────────────────┘
```

**Ports:**

- **8080**: Web interface (HTML/CSS/JavaScript)
- **5000**: Python API server (Flask)
- **2222**: TCP commands to Raspberry Pi (from API server)
- **12345**: UDP data from Raspberry Pi (to API server)
- **8888/8889**: UDP status communication

## Prerequisites

1. **Python 3.7+** installed

   ```powershell
   python --version
   ```

2. **Dependencies installed**

   ```powershell
   pip install -r requirements.txt
   ```

3. **Virtual Environment (Recommended)**
   ```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

## Connecting to Raspberry Pi

If you have a Raspberry Pi, the API server will try to connect automatically. Make sure:

1. **Raspberry Pi is running** the target application:

   ```bash
   python src/Target_Codebase/target_main.py
   ```

2. **Network connectivity** - The Pi should be accessible at `192.168.0.2` (default)

3. **Configure target IP** if different:
   ```powershell
   # Set environment variable before starting
   $env:TARGET_IP = "192.168.1.100"
   .\start-api-server.ps1
   ```

## Troubleshooting

### Port Already in Use

**Error:** `Port 5000 is already in use`

**Solution:**

- Check if API server is already running
- Close other applications using port 5000
- Use a different port: `python web_api_server.py --port 5001`

### Can't Connect to API

**Error:** Browser shows connection errors

**Solution:**

1. Verify API server is running: Check Terminal 1
2. Test API directly: Open `http://localhost:5000/api/status` in browser
3. Check browser console for errors (F12 → Console tab)

### Can't Connect to Raspberry Pi

**Error:** API server shows "Failed to connect to target"

**Solution:**

1. **Check Pi is running:** SSH into Pi and verify `target_main.py` is running
2. **Check IP address:** Ping the Pi: `ping 192.168.0.2`
3. **Check firewall:** Ensure ports 2222, 12345, 8888, 8889 are open
4. **Verify network:** Ensure your computer and Pi are on same network

### Python Not Found

**Error:** `Python is not installed or not in PATH`

**Solution:**

1. Install Python from [python.org](https://www.python.org/downloads/)
2. During installation, check "Add Python to PATH"
3. Or manually add Python to PATH environment variable

### Module Not Found Errors

**Error:** `ModuleNotFoundError: No module named 'flask'`

**Solution:**

```powershell
# Install dependencies
pip install -r requirements.txt

# Or if using venv, make sure it's activated
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Development Workflow

1. **Start API server** (Terminal 1)

   - Runs on port 5000
   - Connects to Raspberry Pi
   - Handles all commands and telemetry

2. **Start web interface** (Terminal 2)

   - Serves static files on port 8080
   - Auto-connects to API on localhost:5000
   - Opens browser automatically

3. **Make changes:**
   - Edit HTML/CSS/JS in `website/` folder → Refresh browser
   - Edit Python API in `src/Host_Codebase/` → Restart API server

## Configuration

### Change API Port

Edit `start-api-server.ps1` or run:

```powershell
python web_api_server.py --port 5001
```

Then update `website/index.html`:

```html
<script>
  window.API_BASE_URL = "http://localhost:5001/api";
</script>
```

### Change Web Interface Port

Edit `start-web-interface.ps1` or run:

```powershell
cd website
python -m http.server 3000
```

Then open `http://localhost:3000` manually.

### Change Raspberry Pi IP

Set environment variable:

```powershell
$env:TARGET_IP = "192.168.1.100"
.\start-api-server.ps1
```

Or edit `src/Host_Codebase/web_api_server.py`:

```python
TARGET_IP = os.getenv("TARGET_IP", "192.168.1.100")  # Your Pi IP
```

## Testing Without Raspberry Pi

The web interface will still work without the Raspberry Pi:

- UI will load and display
- Controls will be visible
- Commands will fail with connection errors (expected)
- You can test the interface layout and functionality

To test with mock data, you would need to modify the API server (advanced).

## Next Steps

Once local development is working:

- See `README.md` for full system documentation
- See `website/README.md` for web interface details
