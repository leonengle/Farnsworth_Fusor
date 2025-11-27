# Host Command Reference

This document describes all commands that can be sent from the Host (laptop/PC) to the Target (Raspberry Pi) via TCP on port 2222.

All commands are sent as plain text strings and responses are returned as strings. Commands are case-insensitive (automatically converted to uppercase).

---

## LED Control

### `LED_ON`
Turns on the LED connected to GPIO pin 26.

**Format:** `LED_ON`

**Response:**
- Success: `LED_ON_SUCCESS`
- Failure: `LED_ON_FAILED: <error_message>`

**Example:**
```
Command: LED_ON
Response: LED_ON_SUCCESS
```

### `LED_OFF`
Turns off the LED connected to GPIO pin 26.

**Format:** `LED_OFF`

**Response:**
- Success: `LED_OFF_SUCCESS`
- Failure: `LED_OFF_FAILED: <error_message>`

**Example:**
```
Command: LED_OFF
Response: LED_OFF_SUCCESS
```

---

## Power Supply Control

### `POWER_SUPPLY_ENABLE`
Enables the power supply.

**Format:** `POWER_SUPPLY_ENABLE` or `POWER_SUPPLY_ENABLE:1` or `POWER_SUPPLY_ENABLE:ON`

**Response:**
- Success: `POWER_SUPPLY_ENABLE_SUCCESS`
- Failure: `POWER_SUPPLY_ENABLE_FAILED`

**Example:**
```
Command: POWER_SUPPLY_ENABLE
Response: POWER_SUPPLY_ENABLE_SUCCESS
```

### `POWER_SUPPLY_DISABLE`
Disables the power supply.

**Format:** `POWER_SUPPLY_DISABLE` or `POWER_SUPPLY_ENABLE:0` or `POWER_SUPPLY_ENABLE:OFF`

**Response:**
- Success: `POWER_SUPPLY_DISABLE_SUCCESS`
- Failure: `POWER_SUPPLY_DISABLE_FAILED`

**Example:**
```
Command: POWER_SUPPLY_DISABLE
Response: POWER_SUPPLY_DISABLE_SUCCESS
```

### `SET_VOLTAGE:<voltage>`
Sets the power supply voltage setpoint.

**Format:** `SET_VOLTAGE:<voltage>`

**Parameters:**
- `<voltage>`: Float value in volts (must be >= 0, typically 0-28000V)

**Response:**
- Success: `SET_VOLTAGE_SUCCESS:<voltage>`
- Failure: `SET_VOLTAGE_FAILED: <error_message>`

**Example:**
```
Command: SET_VOLTAGE:1000
Response: SET_VOLTAGE_SUCCESS:1000
```

**Note:** This command also forwards `ANALOG:POWER_SUPPLY_VOLTAGE_SETPOINT:<voltage>` to the Arduino.

---

## Valve Control

### `SET_VALVE<id>:<position>`
Sets the position of a valve (0-100%).

**Format:** `SET_VALVE<id>:<position>`

**Parameters:**
- `<id>`: Valve ID (1-6)
  - 1: ATM Depressure Valve
  - 2: Foreline Valve
  - 3: Vacuum System Valve
  - 4: Deuterium Supply Valve
  - 5: Reserved Valve 5
  - 6: Reserved Valve 6
- `<position>`: Integer value (0-100) representing percentage open

**Response:**
- Success: `SET_VALVE<id>_SUCCESS:<position>`
- Failure: `SET_VALVE_FAILED: <error_message>`

**Examples:**
```
Command: SET_VALVE1:75
Response: SET_VALVE1_SUCCESS:75

Command: SET_VALVE2:0
Response: SET_VALVE2_SUCCESS:0
```

**Note:** This command controls GPIO PWM and forwards `ANALOG:<VALVE_LABEL>:<position>` to the Arduino.

---

## Pump Control

### `SET_MECHANICAL_PUMP:<power>`
Sets the mechanical (roughing) pump power level.

**Format:** `SET_MECHANICAL_PUMP:<power>`

**Parameters:**
- `<power>`: Integer value (0-100) representing percentage power

**Response:**
- Success: `SET_MECHANICAL_PUMP_SUCCESS:<power>`
- Failure: `SET_MECHANICAL_PUMP_FAILED: <error_message>`

**Example:**
```
Command: SET_MECHANICAL_PUMP:50
Response: SET_MECHANICAL_PUMP_SUCCESS:50
```

**Note:** Forwards `ANALOG:ROUGHING_PUMP_POWER:<power>` to the Arduino.

### `SET_TURBO_PUMP:<power>`
Sets the turbo pump power level.

**Format:** `SET_TURBO_PUMP:<power>`

**Parameters:**
- `<power>`: Integer value (0-100) representing percentage power

**Response:**
- Success: `SET_TURBO_PUMP_SUCCESS:<power>`
- Failure: `SET_TURBO_PUMP_FAILED: <error_message>`

**Example:**
```
Command: SET_TURBO_PUMP:75
Response: SET_TURBO_PUMP_SUCCESS:75
```

**Note:** Forwards `ANALOG:TURBO_PUMP_POWER:<power>` to the Arduino.

### `SET_PUMP_POWER:<power>`
Legacy command for setting mechanical pump power (alias for `SET_MECHANICAL_PUMP`).

**Format:** `SET_PUMP_POWER:<power>`

**Parameters:**
- `<power>`: Integer value (0-100)

**Response:**
- Success: `SET_MECHANICAL_PUMP_SUCCESS:<power>`
- Failure: `SET_PUMP_POWER_FAILED: <error_message>`

---

## Motor Control (Motors 1-4 via Arduino)

### `MOVE_MOTOR:<id>:<steps>[:<direction>]`
Moves a stepper motor by a specified number of steps.

**Format:** `MOVE_MOTOR:<id>:<steps>[:<direction>]`

**Parameters:**
- `<id>`: Motor ID (1-4)
- `<steps>`: Integer value (-10000 to 10000)
- `<direction>`: Optional, "FORWARD", "BACKWARD", or "REVERSE" (default: "FORWARD")

**Response:**
- Success: `MOVE_MOTOR<id>_SUCCESS:<arduino_response>`
- Failure: `MOVE_MOTOR<id>_FAILED` or `MOVE_MOTOR_FAILED: <error_message>`

**Examples:**
```
Command: MOVE_MOTOR:1:100
Response: MOVE_MOTOR1_SUCCESS:<arduino_response>

Command: MOVE_MOTOR:2:50:BACKWARD
Response: MOVE_MOTOR2_SUCCESS:<arduino_response>
```

### `ENABLE_MOTOR:<id>`
Enables a stepper motor.

**Format:** `ENABLE_MOTOR:<id>`

**Parameters:**
- `<id>`: Motor ID (1-4)

**Response:**
- Success: `ENABLE_MOTOR<id>_SUCCESS` or `ENABLE_MOTOR<id>_SUCCESS:<arduino_response>`
- Failure: `ENABLE_MOTOR<id>_FAILED` or `ENABLE_MOTOR_FAILED: <error_message>`

**Example:**
```
Command: ENABLE_MOTOR:1
Response: ENABLE_MOTOR1_SUCCESS
```

### `DISABLE_MOTOR:<id>`
Disables a stepper motor.

**Format:** `DISABLE_MOTOR:<id>`

**Parameters:**
- `<id>`: Motor ID (1-4)

**Response:**
- Success: `DISABLE_MOTOR<id>_SUCCESS` or `DISABLE_MOTOR<id>_SUCCESS:<arduino_response>`
- Failure: `DISABLE_MOTOR<id>_FAILED` or `DISABLE_MOTOR_FAILED: <error_message>`

**Example:**
```
Command: DISABLE_MOTOR:1
Response: DISABLE_MOTOR1_SUCCESS
```

### `SET_MOTOR_SPEED:<id>:<speed>`
Sets the speed of a stepper motor.

**Format:** `SET_MOTOR_SPEED:<id>:<speed>`

**Parameters:**
- `<id>`: Motor ID (1-4)
- `<speed>`: Float value (0.0 to 100.0)

**Response:**
- Success: `SET_MOTOR_SPEED<id>_SUCCESS:<speed>`
- Failure: `SET_MOTOR_SPEED<id>_FAILED` or `SET_MOTOR_SPEED_FAILED: <error_message>`

**Example:**
```
Command: SET_MOTOR_SPEED:1:50
Response: SET_MOTOR_SPEED1_SUCCESS:50
```

### `MOVE_VAR:<steps>`
Legacy command to move Motor 1 (VARIAC control).

**Format:** `MOVE_VAR:<steps>`

**Parameters:**
- `<steps>`: Integer value

**Response:**
- Success: `MOVE_VAR_SUCCESS:<steps>` or `MOVE_VAR_SUCCESS:<arduino_response>`
- Failure: `MOVE_VAR_FAILED: <error_message>`

**Note:** This is equivalent to `MOVE_MOTOR:1:<steps>:FORWARD`.

---

## Sensor Reading

### `READ_POWER_SUPPLY_VOLTAGE`
Reads the power supply voltage from ADC channel 0.

**Format:** `READ_POWER_SUPPLY_VOLTAGE`

**Response:**
- Success: `POWER_SUPPLY_VOLTAGE:<voltage>`
- Failure: `READ_POWER_SUPPLY_VOLTAGE_FAILED: <error_message>`

**Example:**
```
Command: READ_POWER_SUPPLY_VOLTAGE
Response: POWER_SUPPLY_VOLTAGE:1000.50
```

### `READ_POWER_SUPPLY_CURRENT`
Reads the power supply current from ADC channel 1.

**Format:** `READ_POWER_SUPPLY_CURRENT`

**Response:**
- Success: `POWER_SUPPLY_CURRENT:<current>`
- Failure: `READ_POWER_SUPPLY_CURRENT_FAILED: <error_message>`

**Example:**
```
Command: READ_POWER_SUPPLY_CURRENT
Response: POWER_SUPPLY_CURRENT:5.250
```

### `READ_PRESSURE_SENSOR:<sensor_id>`
Reads a pressure sensor value.

**Format:** `READ_PRESSURE_SENSOR:<sensor_id>`

**Parameters:**
- `<sensor_id>`: Sensor ID (1-3)
  - 1: Turbo Pressure Sensor (P01, ADC Channel 0)
  - 2: Fusor Pressure Sensor (P02, ADC Channel 1)
  - 3: Foreline Pressure Sensor (P03, ADC Channel 2)

**Response:**
- Success: `PRESSURE_SENSOR_<id>_VALUE:<pressure>|<label>|<name>`
- Failure: `READ_PRESSURE_SENSOR_FAILED: <error_message>`

**Example:**
```
Command: READ_PRESSURE_SENSOR:1
Response: PRESSURE_SENSOR_1_VALUE:50.25|P01|Turbo Pressure Sensor
```

### `READ_PRESSURE_BY_NAME:<name>`
Reads a pressure sensor by name or label.

**Format:** `READ_PRESSURE_BY_NAME:<name>`

**Parameters:**
- `<name>`: Sensor name or label (case-insensitive)
  - "Turbo" or "P01" → Sensor 1
  - "Fusor" or "P02" → Sensor 2
  - "Foreline" or "P03" → Sensor 3

**Response:**
- Success: Same as `READ_PRESSURE_SENSOR:<id>`
- Failure: `READ_PRESSURE_BY_NAME_FAILED: <error_message>`

**Examples:**
```
Command: READ_PRESSURE_BY_NAME:Turbo
Response: PRESSURE_SENSOR_1_VALUE:50.25|P01|Turbo Pressure Sensor

Command: READ_PRESSURE_BY_NAME:P02
Response: PRESSURE_SENSOR_2_VALUE:25.50|P02|Fusor Pressure Sensor
```

### `READ_NODE_VOLTAGE:<node_id>`
Reads voltage from a node (ADC channels 5-7).

**Format:** `READ_NODE_VOLTAGE:<node_id>`

**Parameters:**
- `<node_id>`: Node ID (1-3), maps to ADC channels 5-7

**Response:**
- Success: `NODE_<id>_VOLTAGE:<voltage>`
- Failure: `READ_NODE_VOLTAGE_FAILED: <error_message>`

**Example:**
```
Command: READ_NODE_VOLTAGE:1
Response: NODE_1_VOLTAGE:12.50
```

### `READ_NODE_CURRENT:<node_id>`
Reads current from a node (ADC channels 5-7).

**Format:** `READ_NODE_CURRENT:<node_id>`

**Parameters:**
- `<node_id>`: Node ID (1-3), maps to ADC channels 5-7

**Response:**
- Success: `NODE_<id>_CURRENT:<current>`
- Failure: `READ_NODE_CURRENT_FAILED: <error_message>`

**Example:**
```
Command: READ_NODE_CURRENT:1
Response: NODE_1_CURRENT:2.500
```

### `READ_ADC`
Reads all 8 ADC channels.

**Format:** `READ_ADC`

**Response:**
- Success: `ADC_DATA:<ch0>,<ch1>,<ch2>,<ch3>,<ch4>,<ch5>,<ch6>,<ch7>`
- Failure: `READ_ADC_FAILED: <error_message>`

**Example:**
```
Command: READ_ADC
Response: ADC_DATA:512,256,128,64,32,16,8,4
```

### `READ_INPUT`
Reads the digital input pin (GPIO 6).

**Format:** `READ_INPUT`

**Response:**
- Success: `INPUT_VALUE:<value>` (0 or 1)
- Failure: `READ_INPUT_FAILED`

**Example:**
```
Command: READ_INPUT
Response: INPUT_VALUE:1
```

### `READ_NEUTRON_COUNTS`
Reads neutron counts (placeholder, not yet implemented).

**Format:** `READ_NEUTRON_COUNTS`

**Response:**
- Always: `NEUTRON_COUNTS:0`

---

## System Commands

### `STARTUP`
Initiates system startup sequence (placeholder).

**Format:** `STARTUP`

**Response:**
- Success: `STARTUP_SUCCESS`

**Example:**
```
Command: STARTUP
Response: STARTUP_SUCCESS
```

### `SHUTDOWN`
Initiates system shutdown sequence. Turns off power supply, closes all valves (sets to 0), and stops all pumps.

**Format:** `SHUTDOWN`

**Response:**
- Success: `SHUTDOWN_SUCCESS`

**Note:** This command:
- Disables power supply
- Sets all valves (1-6) to position 0
- Sets mechanical pump to 0%
- Sets turbo pump to 0%
- Forwards analog commands to Arduino for all components

**Example:**
```
Command: SHUTDOWN
Response: SHUTDOWN_SUCCESS
```

### `EMERGENCY_SHUTOFF`
Immediate emergency shutdown of all systems.

**Format:** `EMERGENCY_SHUTOFF`

**Response:**
- Success: `EMERGENCY_SHUTOFF_SUCCESS` or `EMERGENCY_SHUTOFF_SUCCESS (via Arduino)`

**Note:** Performs emergency shutdown via GPIO handler and forwards shutdown commands to Arduino.

---

## Direct Arduino Commands

### `ARDUINO:<command>`
Forwards a raw command directly to the Arduino Nano without processing.

**Format:** `ARDUINO:<command>`

**Parameters:**
- `<command>`: Any command string to send to Arduino

**Response:**
- Success: `ARDUINO_RESPONSE:<arduino_response>` or `ARDUINO_COMMAND_SENT`
- Failure: `ARDUINO_COMMAND_FAILED: <error_message>`

**Example:**
```
Command: ARDUINO:CUSTOM_COMMAND:PARAM1:PARAM2
Response: ARDUINO_RESPONSE:<arduino_response>
```

**Note:** Use with caution - this bypasses all validation and command processing on the RPi.

---

## Command Format Summary

### General Rules:
- All commands are case-insensitive (automatically converted to uppercase)
- Commands use colon (`:`) as parameter separator
- Responses use underscore (`_`) to separate words
- Success responses typically include `_SUCCESS` suffix
- Failure responses include `_FAILED` suffix with error details

### Response Format:
- **Success:** `<COMMAND>_SUCCESS[:<additional_info>]`
- **Failure:** `<COMMAND>_FAILED: <error_message>`

### Component Labels Forwarded to Arduino:
When analog commands are sent, the following labels are forwarded to Arduino:
- `POWER_SUPPLY_VOLTAGE_SETPOINT` - Power supply voltage
- `ATM_DEPRESSURE_VALVE` - Valve 1
- `FORELINE_VALVE` - Valve 2
- `VACUUM_SYSTEM_VALVE` - Valve 3
- `DEUTERIUM_SUPPLY_VALVE` - Valve 4
- `RESERVED_VALVE_5` - Valve 5
- `RESERVED_VALVE_6` - Valve 6
- `ROUGHING_PUMP_POWER` - Mechanical pump
- `TURBO_PUMP_POWER` - Turbo pump
- `LEGACY_PUMP_POWER` - Legacy pump

---

## Error Handling

All commands may return error responses in the following formats:
- `ERROR: Empty command` - No command provided
- `ERROR: Unknown command '<command>'` - Command not recognized
- `ERROR: <exception_message>` - General processing error
- `<COMMAND>_FAILED: <specific_error>` - Command-specific error

Common error conditions:
- Hardware not available (GPIO, ADC, Arduino not initialized)
- Invalid parameter ranges
- Invalid command format
- Hardware communication errors

