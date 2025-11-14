# Fusor Control Panel UI - Command Mapping

This document maps the UI elements from the Fusor Control Panel to the target codebase commands.

## Fusor Main Panel

### Mode Selection
- **Manual Button** → Host-side mode selection (no target command needed)
- **Automatic Button** → Host-side mode selection (no target command needed)

## Fusor Manual Control Panel

### Left Section - Controls

#### Power Supply Control
- **Power Supply Enable Switch** (Toggle)
  - ON → `POWER_SUPPLY_ENABLE` or `POWER_SUPPLY_ENABLE:1` or `POWER_SUPPLY_ENABLE:ON`
  - OFF → `POWER_SUPPLY_DISABLE` or `POWER_SUPPLY_ENABLE:0` or `POWER_SUPPLY_ENABLE:OFF`
  - Response: `POWER_SUPPLY_ENABLE_SUCCESS` / `POWER_SUPPLY_DISABLE_SUCCESS`

- **Voltage Output Slider** (0-100% or 0-Vmax)
  - Command: `SET_VOLTAGE:<value>`
  - Example: `SET_VOLTAGE:50.5`
  - Response: `SET_VOLTAGE_SUCCESS:<value>`
  - Note: Currently accepts float values, actual hardware implementation pending

#### Vacuum Pump Controls
- **Mechanical Vacuum Pump Slider** (0-100%)
  - Command: `SET_MECHANICAL_PUMP:<value>`
  - Example: `SET_MECHANICAL_PUMP:75`
  - Response: `SET_MECHANICAL_PUMP_SUCCESS:<value>`
  - Implementation: Uses PWM for proportional control (0-100% duty cycle)

- **Turbo Vacuum Pump Slider** (0-100%)
  - Command: `SET_TURBO_PUMP:<value>`
  - Example: `SET_TURBO_PUMP:50`
  - Response: `SET_TURBO_PUMP_SUCCESS:<value>`
  - Implementation: Uses PWM for proportional control (0-100% duty cycle)

#### Valve Controls
- **Valve1 Slider** (0-100%)
  - Command: `SET_VALVE1:<value>`
  - Example: `SET_VALVE1:25`
  - Response: `SET_VALVE1_SUCCESS:<value>`

- **Valve2 Slider** (0-100%)
  - Command: `SET_VALVE2:<value>`
  - Example: `SET_VALVE2:50`
  - Response: `SET_VALVE2_SUCCESS:<value>`

- **Valve3 Slider** (0-100%)
  - Command: `SET_VALVE3:<value>`
  - Example: `SET_VALVE3:75`
  - Response: `SET_VALVE3_SUCCESS:<value>`

- **Valve4 Slider** (0-100%)
  - Command: `SET_VALVE4:<value>`
  - Example: `SET_VALVE4:100`
  - Response: `SET_VALVE4_SUCCESS:<value>`

- **Valve5 Slider** (0-100%)
  - Command: `SET_VALVE5:<value>`
  - Example: `SET_VALVE5:0`
  - Response: `SET_VALVE5_SUCCESS:<value>`

- **Valve6 Slider** (0-100%)
  - Command: `SET_VALVE6:<value>`
  - Example: `SET_VALVE6:60`
  - Response: `SET_VALVE6_SUCCESS:<value>`

- **Implementation**: All valves use PWM for proportional control (0-100% duty cycle)

### Right Section - Displays/Readouts

#### Power Supply Readouts
- **Power Supply Voltage** (Display Field)
  - Command: `READ_POWER_SUPPLY_VOLTAGE`
  - Response: `POWER_SUPPLY_VOLTAGE:<value>`
  - Example: `POWER_SUPPLY_VOLTAGE:12.34`
  - Source: ADC Channel 0

- **Power Supply Current** (Display Field)
  - Command: `READ_POWER_SUPPLY_CURRENT`
  - Response: `POWER_SUPPLY_CURRENT:<value>`
  - Example: `POWER_SUPPLY_CURRENT:2.456`
  - Source: ADC Channel 1

#### Pressure Sensor Readouts
- **Pressure Sensor 1 Value** (Display Field)
  - Command: `READ_PRESSURE_SENSOR:1`
  - Response: `PRESSURE_SENSOR_1_VALUE:<value>`
  - Example: `PRESSURE_SENSOR_1_VALUE:45.67`
  - Source: ADC Channel 2

- **Pressure Sensor 2 Value** (Display Field)
  - Command: `READ_PRESSURE_SENSOR:2`
  - Response: `PRESSURE_SENSOR_2_VALUE:<value>`
  - Example: `PRESSURE_SENSOR_2_VALUE:32.10`
  - Source: ADC Channel 3

- **Pressure Sensor 3 Value** (Display Field)
  - Command: `READ_PRESSURE_SENSOR:3`
  - Response: `PRESSURE_SENSOR_3_VALUE:<value>`
  - Example: `PRESSURE_SENSOR_3_VALUE:15.89`
  - Source: ADC Channel 4

#### Neutron Counts
- **Neutron counts** (Display Field - Placeholder)
  - Command: `READ_NEUTRON_COUNTS`
  - Response: `NEUTRON_COUNTS:0`
  - Note: Placeholder implementation, actual neutron counter integration pending

#### Camera View
- **Camera View** (Placeholder Field)
  - Note: Not implemented, placeholder for future semester

## Fusor Automatic Control Panel

### Left Section - Controls & Status

#### System Status Log
- **System status log** (Display Area)
  - Source: UDP status messages from target
  - Format: Status updates sent via UDP on port 8888
  - Content: System state, errors, warnings, operational status

#### Operation Buttons
- **Startup Button**
  - Command: `STARTUP`
  - Response: `STARTUP_SUCCESS`
  - Note: Startup sequence implementation pending (currently placeholder)

- **Shutdown Button**
  - Command: `SHUTDOWN`
  - Response: `SHUTDOWN_SUCCESS`
  - Implementation: Gracefully disables power supply, closes all valves (0%), stops all pumps (0%)

- **Emergency Shutoff Button**
  - Command: `EMERGENCY_SHUTOFF`
  - Response: `EMERGENCY_SHUTOFF_SUCCESS`
  - Implementation: Immediately disables power supply, closes all valves, stops all pumps via emergency_shutdown()

### Right Section - Displays/Readouts

#### Multi-Node Power Supply Readouts
- **Power Supply Node 1 Voltage** (Display Field)
  - Command: `READ_NODE_VOLTAGE:1`
  - Response: `NODE_1_VOLTAGE:<value>`
  - Example: `NODE_1_VOLTAGE:10.50`
  - Source: ADC Channel 5

- **Power Supply Node 2 Voltage** (Display Field)
  - Command: `READ_NODE_VOLTAGE:2`
  - Response: `NODE_2_VOLTAGE:<value>`
  - Example: `NODE_2_VOLTAGE:11.25`
  - Source: ADC Channel 6

- **Power Supply Node 3 Voltage** (Display Field)
  - Command: `READ_NODE_VOLTAGE:3`
  - Response: `NODE_3_VOLTAGE:<value>`
  - Example: `NODE_3_VOLTAGE:9.75`
  - Source: ADC Channel 7

- **Power Supply Node 1 Current** (Display Field)
  - Command: `READ_NODE_CURRENT:1`
  - Response: `NODE_1_CURRENT:<value>`
  - Example: `NODE_1_CURRENT:1.234`
  - Source: ADC Channel 5 (same as voltage, may differ in hardware)

- **Power Supply Node 2 Current** (Display Field)
  - Command: `READ_NODE_CURRENT:2`
  - Response: `NODE_2_CURRENT:<value>`
  - Example: `NODE_2_CURRENT:2.567`
  - Source: ADC Channel 6

- **Power Supply Node 3 Current** (Display Field)
  - Command: `READ_NODE_CURRENT:3`
  - Response: `NODE_3_CURRENT:<value>`
  - Example: `NODE_3_CURRENT:0.890`
  - Source: ADC Channel 7

#### Pressure Sensor Readouts
- **Pressure Sensor 1 Value** (Display Field)
  - Command: `READ_PRESSURE_SENSOR:1`
  - Response: `PRESSURE_SENSOR_1_VALUE:<value>`
  - Source: ADC Channel 2

- **Pressure Sensor 2 Value** (Display Field)
  - Command: `READ_PRESSURE_SENSOR:2`
  - Response: `PRESSURE_SENSOR_2_VALUE:<value>`
  - Source: ADC Channel 3

- **Pressure Sensor 3 Value** (Display Field)
  - Command: `READ_PRESSURE_SENSOR:3`
  - Response: `PRESSURE_SENSOR_3_VALUE:<value>`
  - Source: ADC Channel 4

#### Camera View & Schematic
- **Camera View** (Placeholder Field)
  - Note: Not implemented, placeholder for future semester

- **Image (Schematic showing node locations)** (Display Field)
  - Note: Static image, no target command needed

## ADC Channel Mapping

| ADC Channel | Purpose |
|------------|---------|
| 0 | Power Supply Voltage |
| 1 | Power Supply Current |
| 2 | Pressure Sensor 1 |
| 3 | Pressure Sensor 2 |
| 4 | Pressure Sensor 3 |
| 5 | Node 1 Voltage/Current |
| 6 | Node 2 Voltage/Current |
| 7 | Node 3 Voltage/Current |

## GPIO Pin Assignments

| Component | GPIO Pin | Physical Pin | Function |
|-----------|----------|--------------|----------|
| LED | 26 | 37 | Status indicator |
| Input | 6 | 31 | Digital input |
| Power Supply | 5 | 29 | Enable/Disable |
| Valve 1 | 17 | 11 | PWM control |
| Valve 2 | 4 | 7 | PWM control |
| Valve 3 | 22 | 15 | PWM control |
| Valve 4 | 23 | 16 | PWM control |
| Valve 5 | 24 | 18 | PWM control |
| Valve 6 | 25 | 22 | PWM control |
| Mechanical Pump | 27 | 13 | PWM control |
| Turbo Pump | 16 | 36 | PWM control |

## Communication Protocol

- **TCP Command Server**: Port 2222 - Receives commands from host
- **TCP Data Server**: Port 12345 - Sends periodic data to host
- **UDP Status Sender**: Port 8888 - Sends status updates to host
- **UDP Status Receiver**: Port 8889 - Receives status from host

## Notes

1. All slider-based controls (valves, pumps) use PWM for proportional control (0-100% duty cycle)
2. Power supply is simple on/off control (not PWM)
3. Voltage setting accepts float values but hardware implementation is pending
4. Startup sequence is placeholder and needs implementation
5. Neutron counter reading is placeholder and needs implementation
6. Camera views are placeholders for future implementation

