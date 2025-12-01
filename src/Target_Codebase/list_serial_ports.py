#!/usr/bin/env python3
from arduino_interface import ArduinoInterface

print("Available Serial Ports (Arduino IDE style):")
print("=" * 80)

ports_info = ArduinoInterface.list_available_ports()

if not ports_info:
    print("No serial ports found!")
else:
    arduino_ports = [p for p in ports_info if p["is_arduino"]]
    other_ports = [p for p in ports_info if not p["is_arduino"]]
    
    if arduino_ports:
        print(f"\n✓ Arduino Boards Detected ({len(arduino_ports)}):")
        print("-" * 80)
        for i, port in enumerate(arduino_ports, 1):
            print(f"\n  [{i}] {port['device']}")
            print(f"      Description: {port['description']}")
            print(f"      VID:PID = {port['vid']}:{port['pid']}")
            if port['manufacturer'] != "N/A":
                print(f"      Manufacturer: {port['manufacturer']}")
            if port['product'] != "N/A":
                print(f"      Product: {port['product']}")
            if port['serial_number'] != "N/A":
                print(f"      Serial: {port['serial_number']}")
            print(f"      Hardware ID: {port['hwid']}")
    
    if other_ports:
        print(f"\nOther Serial Ports ({len(other_ports)}):")
        print("-" * 80)
        for i, port in enumerate(other_ports, 1):
            print(f"\n  [{i}] {port['device']}")
            print(f"      Description: {port['description']}")
            print(f"      VID:PID = {port['vid']}:{port['pid']}")
            if port['manufacturer'] != "N/A":
                print(f"      Manufacturer: {port['manufacturer']}")
            if port['product'] != "N/A":
                print(f"      Product: {port['product']}")
            if port['serial_number'] != "N/A":
                print(f"      Serial: {port['serial_number']}")
            print(f"      Hardware ID: {port['hwid']}")

print("\n" + "=" * 80)
if arduino_ports:
    print(f"Auto-detection will use: {arduino_ports[0]['device']}")
    print("\nTo use a specific port, run target_main.py with:")
    print(f"  --arduino-port {arduino_ports[0]['device']}")
else:
    print("No Arduino boards detected automatically.")
    print("To use a specific port, run target_main.py with:")
    print("  --arduino-port /dev/ttyUSB0  (or /dev/ttyACM0, etc.)")
