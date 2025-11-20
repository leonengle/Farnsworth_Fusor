#!/usr/bin/env python3
import serial.tools.list_ports

print("Available Serial Ports:")
print("-" * 80)

ports = serial.tools.list_ports.comports()

if not ports:
    print("No serial ports found!")
else:
    for i, port_info in enumerate(ports, 1):
        print(f"\nPort {i}:")
        print(f"  Device: {port_info.device}")
        print(f"  Description: {port_info.description}")
        print(f"  Hardware ID: {port_info.hwid}")
        if port_info.vid and port_info.pid:
            print(f"  VID:PID = {port_info.vid:04X}:{port_info.pid:04X}")
        print(f"  Manufacturer: {port_info.manufacturer}")
        print(f"  Product: {port_info.product}")
        print(f"  Serial Number: {port_info.serial_number}")

print("\n" + "-" * 80)
print("To use a specific port, run target_main.py with:")
print("  --arduino-port /dev/ttyUSB0  (or /dev/ttyACM0, etc.)")

