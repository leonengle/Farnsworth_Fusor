# Farnsworth Fusor Control System

Codebase which implements an automated startup & shutdown sequence, data acquisition system, and manual control of a Farnsworth Fusor using TCP/UDP communication with a Finite State Machine (FSM) for automated control sequences.

## **IMPORTANT: Raspberry Pi Only**

**This project is designed exclusively for Raspberry Pi environments.** It includes external libraries that only work within the Raspberry Pi ecosystem:

- **RPi.GPIO**: Raspberry Pi GPIO control
- **Adafruit-MCP3008**: MCP3008 ADC (Analog-to-Digital Converter) interface
- **Adafruit-GPIO**: GPIO abstraction layer for hardware control
- **Hardware-specific dependencies**: ADC, motor control, and sensor interfaces

**This project will NOT run on Windows, macOS, or other Linux distributions** due to these hardware-specific dependencies. However, the host application can run on any system with Python.

## Quick Start (Recommended)

**First, clone and enter the project:**
```
git clone https://github.com/leonengle/Farnsworth_Fusor/
cd Farnsworth_Fusor
```

**Verify setup:**
```
# Check Python version
python --version
# Should be Python 3.7 or higher
```

**Quick Start Commands:**

```
# First time setup (do this once)
pip install -r requirements.txt
pre-commit install  # Optional: for code quality checks

# Run the host application (GUI + FSM)
python src/Host_Codebase/host_main.py

# Run the target application (Raspberry Pi)
python src/Target_Codebase/target_main.py

# Run tests
python src/Test_Cases/target_test_cases/run_all_tests.py

# Check your code before committing
black --check src/ && pylint src/  # Check code quality
```

## Complete Setup Guide

### 1. Clone the Repository
```
git clone https://github.com/leonengle/Farnsworth_Fusor/
cd Farnsworth_Fusor
```

**Verify you're in the right directory:**
```
# You should see the src directory
ls src/

# If you see "src", you're in the right place!
```

### 2. Create Virtual Environment
```
python3 -m venv venv
```

### 3. Activate Virtual Environment
```
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 4. Install Dependencies
```
pip install -r requirements.txt
```

### 5. Set Up Pre-commit Hooks (Optional)
```
pre-commit install
```

This will enable automatic code quality checks before each commit.

### 6. Run the Application
```
# Run the host application (GUI + FSM)
python src/Host_Codebase/host_main.py

# Run the target application (Raspberry Pi)
python src/Target_Codebase/target_main.py
```

The control panel should open with all buttons available. If you see connection errors, check the network configuration.

## Dependencies Overview

This project uses several Python libraries for different functionalities. Here's what each dependency does:

### **Hardware Control Libraries** (Raspberry Pi Only)
| Library | Version | Purpose | Required On |
|---------|---------|---------|-------------|
| `RPi.GPIO` | 0.7.1 | Basic GPIO control for Raspberry Pi pins | Raspberry Pi only |
| `Adafruit-GPIO` | 1.0.3 | GPIO abstraction layer for hardware control | Raspberry Pi only |
| `Adafruit-MCP3008` | 1.0.2 | MCP3008 ADC (Analog-to-Digital Converter) interface | Raspberry Pi only |
| `Adafruit-PureIO` | 1.1.11 | Pure Python I/O operations for hardware | Raspberry Pi only |

### **Communication Libraries**
| Library | Version | Purpose | Required On |
|---------|---------|---------|-------------|
| `socket` | Built-in | TCP/UDP communication | All systems |
| `threading` | Built-in | Multithreaded communication | All systems |

### **User Interface** (Host Only)
| Library | Version | Purpose | Required On |
|---------|---------|---------|-------------|
| `tkinter` | Built-in | GUI framework for the control interface | Host systems |
| `customtkinter` | 5.2.0 | Modern tkinter extension | Host systems |

### **Development Tools**
| Library | Version | Purpose | Required On |
|---------|---------|---------|-------------|
| `pylint` | 3.0.3 | Code linting and style checking | Development only |
| `black` | 23.12.1 | Automatic code formatting | Development only |
| `pre-commit` | 3.6.0 | Git hooks for automated code quality checks | Development only |

### **Installation Notes**
- **Raspberry Pi**: Hardware libraries require system packages (`sudo apt install python3-rpi.gpio python3-dev`)
- **Development Tools**: Only needed for code development, not for running the application
- **Communication**: Uses built-in Python socket library for TCP/UDP communication
- **GUI Library**: tkinter is built into Python, no additional installation needed

## Development Commands

**Common development tasks:**

| Task | Command | What it does |
|------|---------|--------------|
| Install dependencies | `pip install -r requirements.txt` | Install Python dependencies |
| Set up pre-commit | `pre-commit install` | Set up pre-commit hooks (optional) |
| Run host application | `python src/Host_Codebase/host_main.py` | Start unified GUI (manual + FSM) |
| Run target application | `python src/Target_Codebase/target_main.py` | Start target system (RPi) |
| Run tests | `python src/Test_Cases/target_test_cases/run_all_tests.py` | Run all test suites |
| Format code | `black src/` | Format code with black |
| Run linting | `pylint src/` | Check code quality |
| Run all checks | `black --check src/ && pylint src/` | Run all checks |
| Quick check | `black src/ && pylint src/` | Quick code check |
| Clean up | `find . -name "*.pyc" -delete && rm -rf logs/` | Clean generated files |

## Daily Development Workflow

```
# Start your day
python src/Host_Codebase/host_main.py  # Run the unified host application

# While developing
black src/ && pylint src/            # Quick code check (format + lint)

# Before committing
black --check src/ && pylint src/  # Full check

# End of day
find . -name "*.pyc" -delete && rm -rf logs/  # Clean up temporary files
```

**Pro tip:** Run `black --check src/ && pylint src/` before committing to catch issues early!

## Project Structure

```
Farnsworth_Fusor/
├── src/
│   ├── Host_Codebase/          # Main control application
│   │   ├── hostFSM.py          # Legacy standalone FSM UI (logic merged into host_main.py)
│   │   ├── tcp_command_client.py  # TCP command client
│   │   ├── tcp_data_client.py     # TCP data client
│   │   ├── udp_status_client.py   # UDP status/heartbeat client
│   │   ├── base_classes.py        # Abstract base classes
│   │   └── command_handler.py     # Command handling utilities
│   ├── Target_Codebase/         # Raspberry Pi code
│   │   ├── target_main.py       # Main target application
│   │   ├── tcp_command_server.py  # TCP command server
│   │   ├── tcp_data_server.py     # TCP data server
│   │   ├── udp_status_server.py   # UDP status/heartbeat server
│   │   ├── gpio_handler.py        # GPIO operations (LED, valves, pumps, power supply)
│   │   ├── command_processor.py   # Command parsing and execution
│   │   ├── adc.py                 # ADC operations (MCP3008)
│   │   ├── base_classes.py        # Abstract base classes
│   │   └── logging_setup.py        # Logging system
│   └── Test_Cases/               # Test suites
│       ├── target_test_cases/    # Target codebase tests
│       │   ├── test_gpio_handler.py
│       │   ├── test_command_processor.py
│       │   ├── test_adc.py
│       │   ├── test_tcp_communication.py
│       │   ├── test_udp_communication.py
│       │   └── run_all_tests.py
│       └── host_test_cases/      # Host codebase tests
├── requirements.txt              # Dependencies
├── .pre-commit-config.yaml      # Pre-commit hooks
└── pylintrc                     # Linting configuration
```

## Features

### **Finite State Machine (FSM) Control**
- 12-state automated control sequence for fusor operation
- States include: All Off, Rough Pump Down, Turbo Pump Down, Main Chamber Pump Down, Settling, 10kV Operation, Fuel Admission, 27kV Nominal Operation, De-energizing, Shutdown sequences
- Event-driven state transitions based on sensor readings and user commands
- Automatic progression through startup and shutdown sequences

### **Hardware Control**
- **Power Supply Control**: Enable/disable and voltage setting (0-27kV)
- **Valve Control**: 6 valves with PWM-based proportional control (0-100%)
- **Pump Control**: Mechanical pump and turbo pump with PWM-based power control (0-100%)
- **Sensor Reading**: Pressure sensors, voltage/current monitoring, neutron counting
- **Distributed Motor/Actuator Control**: Arduino Nano (Stepper Controllers 1-4) receives labeled analog commands over USB, while the Raspberry Pi drives Stepper Controller 5 directly via GPIO for the docking-station architecture
- **Labeled Analog Datalink**: Every analog command is forwarded to the Arduino as `ANALOG:<FUSOR_COMPONENT>:<value>` so each actuator (valves, pumps, power supply, etc.) carries its destination label across the Pi↔Arduino link
- **Emergency Shutdown**: Immediate shutdown of all systems

### **Professional GUI**
- Modern customtkinter interface with real-time status updates
- Unified `host_main.py` window featuring both manual controls and the 12-state FSM workflow (selectable via tabs)
- Live data display with safety indicators
- FSM state visualization and control

### **Communication**
- **TCP Command Communication**: Host sends commands to target on port 2222
- **TCP Data Communication**: Target sends sensor data to host on port 12345
- **UDP Status/Heartbeat**: Bidirectional status messages on ports 8888/8889
- Robust error handling and connection management
- Real-time command execution and response handling
- Automatic reconnection capabilities

### **Network Configuration**
- **Host IP**: 192.168.0.1 (default)
- **Target IP**: 192.168.0.2 (default)
- **Subnet**: 255.255.255.0
- **TCP Command Port**: 2222
- **TCP Data Port**: 12345
- **UDP Status Ports**: 8888 (host receive), 8889 (target receive)

### **GPIO Pin Assignments**
- **LED Pin**: GPIO 26
- **Input Pin**: GPIO 6
- **Power Supply**: GPIO 5
- **Valves**: GPIO 17, 4, 22, 23, 24, 25 (PWM capable)
- **Mechanical Pump**: GPIO 27 (PWM)
- **Turbo Pump**: GPIO 16 (PWM)

### **Logging & Monitoring**
- Multi-level logging (console, file, error-specific)
- Log rotation with size limits
- Session-based logging for debugging
- Structured logging format with timestamps

### **Testing & Validation**
- **Automated Testing**: Built-in test suite for environment validation
- **Unit Tests**: GPIO handler, command processor, ADC interface
- **Datalink Coverage**: `test_command_processor.py` verifies analog commands are labeled and forwarded to the Arduino USB interface
- **Integration Tests**: TCP/UDP communication
- **Mock Support**: Tests can run without Raspberry Pi hardware
- **Error Detection**: Early detection of configuration issues

## System Architecture Overview

The system is organized in four layers so the host laptop treats the Raspberry Pi as a “docking station” that aggregates every hardware interface.  
1. **Communication Layer** – Three dedicated channels keep traffic separated: the TCP Command Server listens on `192.168.0.2:2222`, the TCP Data Stream pushes structured telemetry on `:12345`, and bidirectional UDP status links operate on host `8888` / target `8889` for lightweight heartbeats.  
2. **Processing Layer** – `CommandProcessor` parses every host command, validates arguments, and routes work to the correct subsystem. It now tags analog actuators (valves 1‑6, power supply, pumps) with semantic labels before handing them to the Arduino.  
3. **Hardware Abstraction Layer** – GPIO, ADC (MCP3008 over SPI), and the Arduino USB interface each expose clean Python APIs. The Arduino Nano handles Stepper Controllers 1‑4 plus two generic interfaces, while Stepper Controller 5 stays on direct GPIO for redundancy.  
4. **Hardware Layer** – SPI wiring to the MCP3008, PWM GPIO for valves/pumps, the fiber/USB harness to the Arduino carriers, and the actual motors, valves, and sensors.

**Arduino Datalink:** Every analog command that originates on the Pi is mirrored to the Arduino as `ANALOG:<FUSOR_COMPONENT>:<value>`. Example labels include `POWER_SUPPLY_VOLTAGE_SETPOINT`, `ATM_DEPRESSURE_VALVE`, `VACUUM_SYSTEM_VALVE`, `ROUGHING_PUMP_POWER`, and `TURBO_PUMP_POWER`. This guarantees the distributed controllers receive unambiguous instructions even when multiple actuators share the same electrical characteristics.

### Arduino Analog Datalink

| Trigger on Host | Pi CommandProcessor Action | USB Payload → Arduino | Target Hardware |
|-----------------|---------------------------|------------------------|-----------------|
| `SET_VOLTAGE:X` | Update GPIO + label (`POWER_SUPPLY_VOLTAGE_SETPOINT`) | `ANALOG:POWER_SUPPLY_VOLTAGE_SETPOINT:X` | High-voltage supply variac |
| `SET_VALVE<i>:Y` | Drive PWM on GPIO | `ANALOG:<VALVE_LABEL_i>:Y` | Valve actuators routed through Nano controllers 1‑4 |
| `SET_MECHANICAL_PUMP:Y` / legacy pump commands | Set PWM + label | `ANALOG:ROUGHING_PUMP_POWER:Y` | Roughing pump driver |
| `SET_TURBO_PUMP:Y` | Set PWM + label | `ANALOG:TURBO_PUMP_POWER:Y` | Turbo pump driver |

- **Message format:** `ANALOG:<FUSOR_COMPONENT>:<value>` with `value` normalized to two decimal places for floats.  
- **Label registry:** Defined in `command_processor.py` so every actuator has a fixed string (e.g., `ATM_DEPRESSURE_VALVE`, `FORELINE_VALVE`, `VACUUM_SYSTEM_VALVE`, `DEUTERIUM_SUPPLY_VALVE`, plus placeholders for future channels).  
- **Flow:** Host GUI → TCP command → CommandProcessor → GPIO action on Pi → labeled USB packet → Arduino Nano (Stepper Controllers 1‑4 + generic analog sinks).  
- **Resilience:** If the Arduino interface is disconnected, the Pi continues to service GPIO locally and automatically resumes mirroring once the USB link reconnects. The systemd service logs any missed forwards to aid troubleshooting.

## Code Quality Tools

This project uses several tools to maintain code quality:

- **Black**: Automatic code formatting (88 character line length)
- **Pylint**: Static code analysis and style checking
- **Pre-commit**: Automated checks before each commit

Pre-commit hooks will automatically run when you commit changes. If any checks fail, fix the issues and commit again.

## Troubleshooting

### **Check Everything First**
```
# Verify Python version
python --version

# Clean and reinstall if needed
find . -name "*.pyc" -delete && rm -rf logs/
pip install -r requirements.txt

# Check code quality
black --check src/ && pylint src/
```

**Expected results:**
- **Python version**: Should be 3.7 or higher
- **Dependencies**: All required packages installed
- **Code quality**: No formatting or linting errors

### **Common Errors**

#### **1) Raspberry Pi Installation Issues**
**CRITICAL: This project ONLY works on Raspberry Pi for the target application!**

**NOTE: To install any library on RPi, don't use pip because you will get errors.**

**Use "sudo apt install..." to install any external libraries.**

For hardware libraries:
```
sudo apt update
sudo apt install python3-rpi.gpio python3-dev
```

**If you're trying to run this on Windows/macOS/Linux (non-RPi):**
- The target application will fail with import errors for RPi.GPIO and Adafruit libraries
- These libraries are Raspberry Pi-specific and cannot be installed on other systems
- You must use a Raspberry Pi to run the target application
- The host application can run on any system

#### **2) Network Connection Issues**

**Basic Connectivity:**
- Verify IP addresses: Host (192.168.0.1) and Target (192.168.0.2)
- Check network configuration: Subnet mask 255.255.255.0
- Ensure firewall allows TCP ports 2222, 12345 and UDP ports 8888, 8889
- Test connectivity: `ping` from host to target and vice versa

**Windows Host Firewall:**
If ping fails on Windows, run this command in PowerShell (as Administrator):
```powershell
netsh advfirewall firewall add rule name="Allow ICMPv4-In" protocol=icmpv4:any,any dir=in action=allow
```

**Network Interface Configuration on Windows:**
- Ensure Ethernet adapter is named "Ethernet" (adjust commands if different)
- Verify IP forwarding is enabled:
```powershell
Set-NetIPInterface -InterfaceAlias "Ethernet" -Forwarding Enabled
Set-NetIPInterface -InterfaceAlias "Wi-Fi" -Forwarding Enabled
```

**NAT Configuration (Windows Host):**
If RPi needs internet access through host, set up NAT:
```powershell
if (-not (Get-NetNat | Where-Object Name -eq "PiNat")) {
    New-NetNat -Name "PiNat" -InternalIPInterfaceAddressPrefix 192.168.0.0/24
}
Get-NetNat
```

**Raspberry Pi Network Configuration:**
- Ensure NetworkManager is installed: `sudo apt install network-manager`
- Verify network interface name (may be "eth0" or "enp1s0" instead of "Wired connection 1"):
```bash
nmcli con show
```
- Set static IP (adjust interface name if different):
```bash
sudo nmcli con mod "Wired connection 1" ipv4.address 192.168.0.2/24
sudo nmcli con mod "Wired connection 1" ipv4.gateway ""
sudo nmcli con mod "Wired connection 1" ipv4.dns ""
sudo nmcli con up "Wired connection 1"
```

**IP Address Conflicts:**
- Ensure no other devices on the network use 192.168.0.1 or 192.168.0.2
- Check for duplicate IP addresses: `ipconfig` (Windows) or `ip addr` (Linux)
- Verify both machines are on the same physical network segment

**Port Blocking:**
- Windows Firewall may block TCP/UDP ports - add exceptions for ports 2222, 12345, 8888, 8889
- Check if antivirus software is blocking connections
- Verify router/firewall settings if using additional network hardware

#### **3) Dependency Issues**
```
# Clean install
find . -name "*.pyc" -delete && rm -rf logs/
pip install -r requirements.txt

# Or manual install
pip install -r requirements.txt
```

#### **4) Service Management Issues (Raspberry Pi)**

**Service Not Starting:**
- Verify service name matches your installation (may be `fusor-target` or `farnsworth-fusor.service`)
- Check service status:
```bash
sudo systemctl status fusor-target
# or
sudo systemctl status farnsworth-fusor.service
```
- View service logs:
```bash
sudo journalctl -u fusor-target -f
# or
sudo journalctl -u farnsworth-fusor.service -f
```

**Updating Target Codebase:**
If you need to update the code on RPi:
```bash
# Stop the service
sudo systemctl stop fusor-target

# Update the repository
cd ~/Farnsworth_Fusor
git fetch
git pull

# Restart the service
sudo systemctl start fusor-target
sudo systemctl status fusor-target
```

**Service Permissions:**
- Ensure service user has access to GPIO (usually requires `pi` user or `gpio` group)
- Check file permissions: `ls -l /home/pi/Farnsworth_Fusor/src/Target_Codebase/`
- Verify Python path in service file matches installed location

**Service Not Auto-Starting:**
- Verify service is enabled: `sudo systemctl enable fusor-target`
- Check if service is masked: `sudo systemctl unmask fusor-target`
- Ensure service file paths are absolute and correct

#### **5) Pre-commit Issues**
```
# Run pre-commit manually
pre-commit run --all-files

# Or fix specific issues
black src/    # Fix formatting
pylint src/   # Check linting issues
```

#### **6) Git and Internet Access Issues (Raspberry Pi)**

**RPi Needs Internet Access:**
If RPi needs internet access for git/pip commands while connected to host:
- Ensure Windows host has IP forwarding enabled (see Network Connection Issues above)
- Verify NAT is configured correctly (see Network Connection Issues above)
- Test internet access from RPi: `ping 8.8.8.8`

**Network Interface Names:**
- Windows: Network interface may be named differently (e.g., "Ethernet 2", "Local Area Connection")
  - Check actual name: `Get-NetAdapter | Select-Object Name, InterfaceAlias`
  - Adjust PowerShell commands accordingly
- Linux/RPi: Interface may be "eth0", "enp1s0", "enx..." instead of "Wired connection 1"
  - Check actual name: `ip addr` or `nmcli con show`
  - Adjust nmcli commands accordingly

## Running the Application

### **Host Application** (Control Computer - Your Laptop)
```bash
python src/Host_Codebase/host_main.py
```

Or with custom IP addresses:
```bash
python src/Host_Codebase/host_main.py
# IP addresses can be configured in the GUI or via command-line arguments
```

### **Target Application** (Raspberry Pi)

**For Development/Testing:**
```bash
python3 src/Target_Codebase/target_main.py
```

Or with custom settings:
```bash
python3 src/Target_Codebase/target_main.py --host 192.168.0.1 --tcp-command-port 2222 --use-adc
```

**For Automatic Startup on Boot (Production):**

The RPi should run `target_main.py` automatically at boot. You have two options:

**Option 1: Systemd Service (Recommended)**

**Quick Setup (Automated):**
```bash
# Run the setup script (automatically installs and configures the service)
sudo bash setup_service.sh
```

**Manual Setup:**
```bash
# Copy the service file
sudo cp farnsworth-fusor.service /etc/systemd/system/

# Edit the service file to match your RPi paths (if needed)
sudo nano /etc/systemd/system/farnsworth-fusor.service

# Reload systemd
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable farnsworth-fusor.service
sudo systemctl start farnsworth-fusor.service

# Check status
sudo systemctl status farnsworth-fusor.service
```

**Service Management:**
```bash
# View logs (real-time)
sudo journalctl -u farnsworth-fusor.service -f

# Restart service
sudo systemctl restart farnsworth-fusor.service

# Stop service
sudo systemctl stop farnsworth-fusor.service

# Disable auto-start
sudo systemctl disable farnsworth-fusor.service
```

**Option 2: Add to rc.local**
```bash
# Edit rc.local
sudo nano /etc/rc.local

# Add before "exit 0":
cd /home/pi/Farnsworth_Fusor/src/Target_Codebase
python3 target_main.py &

exit 0
```

**Note:** The RPi doesn't need a Makefile - it just needs `target_main.py` to run automatically at boot.

### **Running Tests**
```bash
# Run all target tests
python src/Test_Cases/target_test_cases/run_all_tests.py

# Run individual test files
python src/Test_Cases/target_test_cases/test_gpio_handler.py
python src/Test_Cases/target_test_cases/test_command_processor.py
python src/Test_Cases/target_test_cases/test_adc.py
```

## Development Notes

- **Virtual Environment**: Always work within the virtual environment
- **Code Style**: Black formatting with 88-character line length
- **Testing**: Run `black --check src/ && pylint src/` before committing
- **Logging**: Comprehensive logging for debugging and monitoring
- **Communication**: TCP/UDP protocol - no SSH dependencies required
- **FSM Control**: The host application uses a Finite State Machine for automated control sequences
- **PWM Control**: Valves and pumps use PWM for proportional control (0-100%)

---

**Ready to start? Run `python src/Host_Codebase/host_main.py` to open the control panel!**
