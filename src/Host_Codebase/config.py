# config.py
"""
Configuration settings for the SSH/TCP hybrid communication system.
Centralizes network settings and connection parameters.
"""

# Target (Raspberry Pi) Configuration
TARGET_HOST = "192.168.1.101"  # Raspberry Pi IP address
TARGET_SSH_PORT = 2222         # SSH server port on target
TARGET_USERNAME = "mdali"      # SSH username (updated from "pi")
TARGET_PASSWORD = "raspberry"  # SSH password

# Host (Control Machine) Configuration
HOST_TCP_PORT = 8888           # TCP server port on host for data reception
HOST_IP = "192.168.1.100"     # Host machine IP address

# GPIO Configuration
LED_PIN = 26                   # GPIO pin for LED control
INPUT_PIN = 6                  # GPIO pin for input reading

# Communication Settings
DATA_SEND_INTERVAL = 1.0       # Seconds between data transmissions
SSH_TIMEOUT = 10               # SSH connection timeout in seconds
TCP_TIMEOUT = 1.0              # TCP socket timeout in seconds

# Logging Configuration
LOG_LEVEL = "INFO"             # Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_FILE_HOST = "host_control.log"
LOG_FILE_TCP = "tcp_data_receiver.log"
LOG_FILE_TARGET = "target_system.log"

# Data Formats
GPIO_DATA_FORMAT = "GPIO_INPUT:{value}"
ADC_DATA_FORMAT = "ADC_DATA:{value}"

# Commands
LED_ON_COMMAND = "LED_ON"
LED_OFF_COMMAND = "LED_OFF"
MOVE_VAR_COMMAND = "MOVE_VAR:{steps}"

# Responses
LED_ON_SUCCESS = "LED_ON_SUCCESS"
LED_OFF_SUCCESS = "LED_OFF_SUCCESS"
UNKNOWN_COMMAND = "UNKNOWN_COMMAND"
