# 🚀 Farnsworth Fusor Control System

Codebase which implements an automated startup & shutdown sequence, data acquisition, and manual control of a Farnsworth Fusor.

## ⚠️ **IMPORTANT: Raspberry Pi Only**

**This project is designed exclusively for Raspberry Pi environments.** It includes external libraries that only work within the Raspberry Pi ecosystem:

- **RPi.GPIO**: Raspberry Pi GPIO control
- **pigpio**: Advanced Raspberry Pi GPIO operations
- **spidev**: Raspberry Pi SPI communication
- **Hardware-specific dependencies**: ADC, motor control, and sensor interfaces

**This project will NOT run on Windows, macOS, or other Linux distributions** due to these hardware-specific dependencies.

## 🎯 Quick Start (Recommended)

**First, clone and enter the project:**
```
git clone https://github.com/leonengle/Farnsworth_Fusor/
cd Farnsworth_Fusor
```

**Test if everything works:**
```
# Test your environment
make test-env
```

**Then use the Makefile for everything!** It's much easier than remembering complex commands:

```
# First time setup (do this once)
make dev

# Run the application
make run

# Check your code before committing
make check

# Clean up when done
make clean
```

**⚠️ Important:** You must be inside the `Farnsworth_Fusor` directory to use `make` commands!

## 📋 Complete Setup Guide

### 1. Clone the Repository
```
git clone https://github.com/leonengle/Farnsworth_Fusor/
cd Farnsworth_Fusor
```

**🔍 Verify you're in the right directory:**
```
# You should see the Makefile
ls Makefile

# If you see "Makefile", you're in the right place!
```

### 2. Create Virtual Environment
```
python3 -m venv venv
```

### 3. Activate Virtual Environment
```
source venv/bin/activate
```

### 4. Complete Development Setup
```
make dev
```

This single command:
- Installs all dependencies
- Sets up pre-commit hooks
- Configures development tools
- Runs initial checks

### 5. Test Everything Works
```
# Test your environment
make test-env

# Run the application
make run
```

**Expected test results:**
- ✅ **Before setup**: Some commands may fail (missing dependencies)
- ✅ **After setup**: All commands should work perfectly
- ✅ **File structure**: All required files should be present

## 📦 Dependencies Overview

This project uses several Python libraries for different functionalities. Here's what each dependency does:

### **🔧 Hardware Control Libraries**
| Library | Version | Purpose | Required On |
|---------|---------|---------|-------------|
| `RPi.GPIO` | 0.7.1 | Basic GPIO control for Raspberry Pi pins | Raspberry Pi only |
| `pigpio` | 1.78 | Advanced GPIO control with hardware PWM, servo control, I2C/SPI | Raspberry Pi only |
| `spidev` | 3.8 | SPI communication for ADC and other SPI devices | Raspberry Pi only |
| `Adafruit-GPIO` | 1.0.3 | GPIO abstraction layer for hardware control | Raspberry Pi only |
| `Adafruit-MCP3008` | 1.0.2 | MCP3008 ADC (Analog-to-Digital Converter) interface | Raspberry Pi only |
| `Adafruit-PureIO` | 1.1.11 | Pure Python I/O operations for hardware | Raspberry Pi only |

### **📡 Communication & Security**
| Library | Version | Purpose | Required On |
|---------|---------|---------|-------------|
| `paramiko` | 3.1.0 | SSH client for secure communication with Raspberry Pi | All systems |
| `cryptography` | 46.0.1 | Cryptographic operations and secure connections | All systems |
| `bcrypt` | 4.3.0 | Password hashing and security | All systems |
| `PyNaCl` | 1.6.0 | Cryptographic library for secure communications | All systems |
| `cffi` | 2.0.0 | C Foreign Function Interface for cryptographic libraries | All systems |
| `pycparser` | 2.23 | C parser for cffi | All systems |

### **🎛️ User Interface**
| Library | Version | Purpose | Required On |
|---------|---------|---------|-------------|
| `PySimpleGUI` | 5.0.8.3 | GUI framework for the control interface | All systems |

### **🛠️ Development Tools**
| Library | Version | Purpose | Required On |
|---------|---------|---------|-------------|
| `pylint` | 3.0.3 | Code linting and style checking | Development only |
| `black` | 23.12.1 | Automatic code formatting | Development only |
| `pre-commit` | 3.6.0 | Git hooks for automated code quality checks | Development only |

### **📋 Installation Notes**
- **Raspberry Pi**: Hardware libraries require system packages (`sudo apt install python3-pigpio python3-rpi.gpio python3-spidev`)
- **Development Tools**: Only needed for code development, not for running the application
- **Security Libraries**: Required for secure SSH communication between host and target systems
- **GUI Library**: PySimpleGUI provides the main user interface for fusor control

## 🛠️ Development Commands

**Instead of complex commands, just use `make`:**

| Task | Command | What it does |
|------|---------|--------------|
| Install dependencies | `pip install -r requirements.txt` | `make install` |
| Set up development | `python setup_dev.py` | `make dev` |
| Run the app | `python src/Host_Codebase/host_main.py` | `make run` |
| Run target server | `python src/Target_Codebase/target_ssh_server.py` | `make run-target` |
| Test target codebase | `python src/Target_Codebase/target_test.py` | `make test-target` |
| Format code | `black src/` | `make format` |
| Run linting | `pylint src/` | `make lint` |
| Test environment | `python testEnv.py` | `make test-env` |
| Run all checks | `black --check src/ && pylint src/ && python testEnv.py` | `make check` |
| Quick check | `black src/ && pylint src/` | `make quick-check` |
| Clean up | `find . -name "*.pyc" -delete && rm -rf logs/` | `make clean` |

**See all available commands:**
```
make help
```

## 🔄 Daily Development Workflow

```
# Start your day
make test-env            # Test environment
make run                 # Run the application

# While developing
make quick-check         # Quick code check (format + lint)

# Before committing
make check           # Full check (format + lint + test)

# End of day
make clean               # Clean up temporary files
```

**Pro tip:** Run `make test-env` first to catch any issues early!

## 🏗️ Project Structure

```
Farnsworth_Fusor/
├── src/
│   ├── Host_Codebase/          # Main control application
│   │   ├── host_main.py        # Main GUI application
│   │   ├── base_classes.py     # Abstract base classes
│   │   ├── communication.py    # SSH communication
│   │   ├── power_control.py    # Power supply control
│   │   ├── vacuum_control.py   # Vacuum pump control
│   │   ├── config.py           # Configuration management
│   │   └── logging_setup.py    # Logging system
│   └── Target_Codebase/        # Raspberry Pi code
│       ├── adc.py              # ADC operations
│       ├── moveVARIAC.py        # Motor control
│       └── base_classes.py     # Abstract base classes
├── Makefile                    # Development automation
├── requirements.txt            # Dependencies
├── testEnv.py                  # Environment testing
├── test_makefile.py            # Makefile testing
├── setup_dev.py                # Development setup
├── .pre-commit-config.yaml     # Pre-commit hooks
└── pylintrc                    # Linting configuration
```

## 🎛️ Features

### **Safety Systems**
- Comprehensive safety validation for voltage, current, and pressure
- Emergency stop functionality with immediate shutdown
- Configurable safety limits with runtime updates
- Real-time monitoring with automatic alerts

### **Professional GUI**
- Modern tkinter interface with real-time status updates
- Intuitive controls for power supply and vacuum pump
- Live data display with safety indicators
- Emergency stop button prominently displayed

### **Communication**
- Secure SSH communication with Raspberry Pi
- Robust error handling and connection management
- Real-time command execution and response handling
- Automatic reconnection capabilities

### **Logging & Monitoring**
- Multi-level logging (console, file, error-specific)
- Log rotation with size limits
- Session-based logging for debugging
- Structured logging format with timestamps

### **Configuration Management**
- JSON-based configuration with defaults
- Runtime configuration updates
- Safety limit configuration
- Centralized settings management

### **Testing & Validation**
- **Automated Testing**: Built-in test suite for environment validation
- **Environment Validation**: Comprehensive environment setup verification
- **Cross-platform Support**: Raspberry Pi compatibility
- **Error Detection**: Early detection of configuration issues

## 🔧 Code Quality Tools

This project uses several tools to maintain code quality:

- **Black**: Automatic code formatting (88 character line length)
- **Pylint**: Static code analysis and style checking
- **Pre-commit**: Automated checks before each commit

Pre-commit hooks will automatically run when you commit changes. If any checks fail, fix the issues and commit again.

## 🚨 Troubleshooting

### **Test Everything First**
```
# Test your environment
make test-env

# Clean and reinstall if needed
make clean
make dev
```

**Expected test results:**
- ✅ **Before setup**: Some commands may fail (normal - missing dependencies)
- ✅ **After setup**: All commands should work perfectly
- ❌ **File missing**: Check if you're in the right directory

### **Common Errors while implementing your virtual environment**

#### **1) PySimpleGUI Installation Issues**
**NOTE: PySimpleGUI is hosted on a private PyPI server. If you're using the old version, it is recommended to get the private version of the library since it is more up-to-date and maintained. The user is required to run these commands to uninstall any existing versions for this project:**
```
python -m pip uninstall PySimpleGUI
python -m pip cache purge
```

#### **2) Raspberry Pi Installation Issues**
**⚠️ CRITICAL: This project ONLY works on Raspberry Pi!**

**NOTE: To install any library on RPi, don't use pip because you will get the following:**

<img width="438" height="175" alt="image" src="https://github.com/user-attachments/assets/6fb0b4df-e1db-43d6-99c5-16a5e9ce0754" />

**Use "sudo apt install..." to install any external libraries.**

For hardware libraries:
```
sudo apt update
sudo apt install python3-pigpio python3-rpi.gpio python3-spidev python3-dev
```

**If you're trying to run this on Windows/macOS/Linux (non-RPi):**
- The project will fail with import errors for RPi.GPIO, pigpio, and spidev
- These libraries are Raspberry Pi-specific and cannot be installed on other systems
- You must use a Raspberry Pi to run this project

#### **3) Dependency Issues**
```
# Clean install
make clean
make dev

# Or manual install
pip install -r requirements.txt
```

#### **4) Pre-commit Issues**
```
# Run pre-commit manually
make pre-commit-all

# Or fix specific issues
make format    # Fix formatting
make lint      # Check linting issues
```

## 📝 Development Notes

- **Virtual Environment**: Always work within the virtual environment
- **Code Style**: Black formatting with 88-character line length
- **Testing**: Run `make test-env` before committing
- **Logging**: Comprehensive logging for debugging and monitoring

---

**🚀 Ready to start? Run `make test-env` to verify everything works!**
