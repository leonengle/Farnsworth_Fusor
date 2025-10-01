# 🚀 Farnsworth Fusor Control System

A professional-grade control system for Farnsworth Fusor operations with comprehensive safety features, real-time monitoring, and modern development tools.

## 🎯 Quick Start (Recommended)

**First, clone and enter the project:**
```bash
git clone https://github.com/leonengle/Farnsworth_Fusor/
cd Farnsworth_Fusor
```

**Test if everything works:**
```bash
# Test all make commands
python test_makefile.py
```

**Then use the Makefile for everything!** It's much easier than remembering complex commands:

```bash
# First time setup (do this once)
make dev-setup

# Run the application
make run

# Check your code before committing
make check-all

# Clean up when done
make clean
```

**⚠️ Important:** You must be inside the `Farnsworth_Fusor` directory to use `make` commands!

## 📋 Complete Setup Guide

### 1. Clone the Repository
```bash
git clone https://github.com/leonengle/Farnsworth_Fusor/
cd Farnsworth_Fusor
```

**🔍 Verify you're in the right directory:**
```bash
# You should see the Makefile
ls Makefile

# If you see "Makefile", you're in the right place!
```

### 2. Create Virtual Environment
```bash
python -m venv venv
```

### 3. Activate Virtual Environment

**Windows (Command Prompt):**
```bash
venv\Scripts\activate
```

**Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 4. Complete Development Setup
```bash
# One command does everything!
make dev-setup
```

This automatically:
- Installs all dependencies
- Sets up pre-commit hooks
- Configures development tools
- Runs initial checks

### 5. Test Everything Works
```bash
# Test all make commands (recommended first step)
python test_makefile.py

# Test your environment
make test-env

# Run the application
make run
```

**Expected test results:**
- ✅ **Before setup**: Some commands may fail (missing dependencies)
- ✅ **After setup**: All commands should work perfectly
- ✅ **File structure**: All required files should be present

## 🛠️ Development Commands

**Instead of complex commands, just use `make`:**

| What you want to do | Instead of this | Use this |
|---------------------|-----------------|----------|
| Install dependencies | `pip install -r requirements.txt` | `make install` |
| Set up development | `python setup_dev.py` | `make dev-setup` |
| Run the app | `python src/Host_Codebase/fusor_main.py` | `make run` |
| Format code | `black src/` | `make format` |
| Check formatting | `black --check src/` | `make format-check` |
| Run linting | `pylint src/` | `make lint` |
| Test environment | `python testEnv.py` | `make test-env` |
| Test make commands | `python test_makefile.py` | `make test-commands` |
| Run all checks | `black --check src/ && pylint src/ && python testEnv.py` | `make check-all` |
| Quick check | `black src/ && pylint src/` | `make quick-check` |
| Clean up | `find . -name "*.pyc" -delete && rm -rf logs/` | `make clean` |

**See all available commands:**
```bash
make help
```

## 🔄 Daily Development Workflow

```bash
# Start your day
python test_makefile.py  # Test if everything works
make run                 # Run the application

# While developing
make quick-check         # Quick code check (format + lint)

# Before committing
make check-all           # Full check (format + lint + test)

# End of day
make clean               # Clean up temporary files
```

**Pro tip:** Run `python test_makefile.py` first to catch any issues early!

## 🏗️ Project Structure

```
Farnsworth_Fusor/
├── src/
│   ├── Host_Codebase/          # Main control application
│   │   ├── fusor_main.py       # Main GUI application
│   │   ├── base_classes.py     # Abstract base classes
│   │   ├── communication.py    # SSH communication
│   │   ├── power_control.py    # Power supply control
│   │   ├── vacuum_control.py   # Vacuum pump control
│   │   ├── config.py           # Configuration management
│   │   └── logging_setup.py    # Logging system
│   └── Target_Codebase/        # Raspberry Pi code
│       ├── base_classes.py     # Hardware interfaces
│       ├── adc.py              # ADC operations
│       └── moveVARIAC.py       # Motor control
├── logs/                       # Application logs
├── Makefile                    # Development commands
├── requirements.txt            # Dependencies
├── .pre-commit-config.yaml     # Pre-commit hooks
└── testEnv.py                  # Environment testing
```

## 🎛️ Features

### **Safety Systems**
- Configurable safety limits for voltage, current, and pressure
- Real-time validation before operations
- Emergency stop functionality
- User confirmation dialogs for unsafe operations

### **Professional GUI**
- Modern ttk interface with labeled sections
- Real-time status monitoring
- Responsive layout with proper grid management
- Emergency stop button with confirmation

### **Communication**
- SSH-based communication with Raspberry Pi
- Robust error handling and connection management
- Command validation and response handling

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
- **Automated Testing**: Built-in test suite for all make commands (`python test_makefile.py`)
- **Environment Validation**: Comprehensive environment setup verification
- **Cross-platform Support**: Windows and Unix compatibility
- **Error Detection**: Early detection of configuration issues

## 🔧 Code Quality Tools

This project uses several tools to maintain code quality:

- **Black**: Automatic code formatting (88 character line length)
- **Pylint**: Static code analysis and style checking
- **Pre-commit**: Automated checks before each commit

Pre-commit hooks will automatically run when you commit changes. If any checks fail, fix the issues and commit again.

## 🚨 Troubleshooting

### **Test Everything First**
```bash
# Test if all make commands work
python test_makefile.py

# Test your environment
make test-env

# Clean and reinstall if needed
make clean
make dev-setup
```

**Expected test results:**
- ✅ **Before setup**: Some commands may fail (normal - missing dependencies)
- ✅ **After setup**: All commands should work perfectly
- ❌ **File missing**: Check if you're in the right directory

### **Permission Errors (Windows)**
If you get permission errors when activating the virtual environment:
- Open PowerShell as Administrator
- Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Then try: `venv\Scripts\Activate.ps1`

### **Dependency Issues**
```bash
# Clean install
make clean
make install

# Or reinstall everything
make dev-setup
```

### **Pre-commit Issues**
```bash
# Reinstall hooks
make pre-commit-install

# Run manually
make pre-commit-all
```

## 📝 Development Notes

- **Virtual Environment**: Always activate before working
- **Pre-commit**: Hooks run automatically on commits
- **Logging**: Check `logs/` directory for application logs
- **Configuration**: Modify `fusor_config.json` for settings
- **Safety**: All operations include safety validation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `make check-all` before committing
5. Commit your changes (pre-commit hooks will run)
6. Push and create a pull request

## 📄 License

This project is part of a senior capstone project for fusor control systems.



