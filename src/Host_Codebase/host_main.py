import tkinter as tk
from tkinter import messagebox, ttk
import sys
import os

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import power_control as PC
import vacuum_control as VC
import communication as com
from config import config
from logging_setup import setup_logging, get_logger

# Setup logging first
setup_logging()
logger = get_logger("FusorMain")

# Initialize communication and components
try:
    comm_config = config.get_communication_config()
    power_config = config.get_power_supply_config()
    vacuum_config = config.get_vacuum_pump_config()
    
    RPi_3b = com.SSHClient(
        comm_config["host"], 
        comm_config["port"], 
        comm_config["username"], 
        comm_config["password"], 
        comm_config["command_template"]
    )
    
    turboPump = VC.TurboPump(vacuum_config["name"])
    supply27kV = PC.PowerSupply(
        power_config["name"], 
        maxVoltage=power_config["max_voltage"], 
        maxCurrent=power_config["max_current"], 
        communication_client=RPi_3b
    )
    
    logger.info("Components initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize components: {e}")
    messagebox.showerror("Initialization Error", f"Failed to initialize components: {e}")
    sys.exit(1)

def create_gui():
    """Create and configure the main GUI."""
    root = tk.Tk()
    root.title("Fusor Control Panel")
    root.geometry("600x400")
    root.default_font = ("Arial", 10)
    
    # Create main frame with padding
    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    # Configure grid weights
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)
    
    # Power Control Section
    power_frame = ttk.LabelFrame(main_frame, text="Power Control", padding="10")
    power_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
    power_frame.columnconfigure(1, weight=1)
    
    powerControlLabel = ttk.Label(power_frame, text="Desired Fusor Supply Voltage (V):")
    powerControlLabel.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
    
    powerControlScale = ttk.Scale(power_frame, from_=0, to=supply27kV.max_voltage, 
                                 orient="horizontal", length=300)
    powerControlScale.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
    
    voltage_var = tk.StringVar()
    voltage_label = ttk.Label(power_frame, textvariable=voltage_var)
    voltage_label.grid(row=2, column=0, sticky=tk.W)
    
    def update_voltage_display(*args):
        voltage_var.set(f"Voltage: {powerControlScale.get():.0f} V")
    
    powerControlScale.configure(command=update_voltage_display)
    update_voltage_display()
    
    def set_voltage():
        try:
            voltage = int(powerControlScale.get())
            current = supply27kV.get_current()
            pressure = turboPump.get_pressure()
            
            # Validate safety limits
            is_safe, safety_msg = config.validate_safety_limits(voltage, current, pressure)
            if not is_safe:
                logger.warning(f"Safety validation failed: {safety_msg}")
                if messagebox.askyesno("Safety Warning", 
                                     f"{safety_msg}\n\nDo you want to proceed anyway?"):
                    pass  # User confirmed, proceed
                else:
                    return  # User cancelled
            
            success = supply27kV.set_voltage(voltage)
            if success:
                messagebox.showinfo("Success", f"Voltage set to {voltage}V")
                logger.info(f"Voltage set to {voltage}V")
            else:
                messagebox.showerror("Error", "Failed to set voltage")
                logger.error("Failed to set voltage")
        except Exception as e:
            logger.error(f"Error setting voltage: {e}")
            messagebox.showerror("Error", f"Failed to set voltage: {e}")
    
    powerControlButton = ttk.Button(power_frame, text="Set Voltage", command=set_voltage)
    powerControlButton.grid(row=3, column=0, pady=(5, 0))
    
    # Vacuum Control Section
    vacuum_frame = ttk.LabelFrame(main_frame, text="Vacuum Control", padding="10")
    vacuum_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
    vacuum_frame.columnconfigure(1, weight=1)
    
    vacuum_label = ttk.Label(vacuum_frame, text="Pump Power (%):")
    vacuum_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
    
    vacuum_scale = ttk.Scale(vacuum_frame, from_=0, to=100, orient="horizontal", length=300)
    vacuum_scale.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
    
    power_var = tk.StringVar()
    power_display = ttk.Label(vacuum_frame, textvariable=power_var)
    power_display.grid(row=2, column=0, sticky=tk.W)
    
    def update_power_display(*args):
        power_var.set(f"Power: {vacuum_scale.get():.0f}%")
    
    vacuum_scale.configure(command=update_power_display)
    update_power_display()
    
    def set_pump_power():
        try:
            power = float(vacuum_scale.get())
            success = turboPump.set_power(power)
            if success:
                messagebox.showinfo("Success", f"Pump power set to {power}%")
            else:
                messagebox.showerror("Error", "Failed to set pump power")
        except Exception as e:
            logger.error(f"Error setting pump power: {e}")
            messagebox.showerror("Error", f"Failed to set pump power: {e}")
    
    vacuum_button = ttk.Button(vacuum_frame, text="Set Power", command=set_pump_power)
    vacuum_button.grid(row=3, column=0, pady=(5, 0))
    
    # Status Section
    status_frame = ttk.LabelFrame(main_frame, text="System Status", padding="10")
    status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
    
    status_text = tk.Text(status_frame, height=6, width=50)
    status_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
    
    def update_status():
        status_text.delete(1.0, tk.END)
        status_text.insert(tk.END, f"Power Supply Status:\n")
        status_text.insert(tk.END, f"  Voltage: {supply27kV.get_voltage():.2f} V\n")
        status_text.insert(tk.END, f"  Current: {supply27kV.get_current():.3f} A\n")
        status_text.insert(tk.END, f"  Output Enabled: {supply27kV.is_output_enabled()}\n")
        status_text.insert(tk.END, f"Vacuum Pump Status:\n")
        status_text.insert(tk.END, f"  Running: {turboPump.is_running()}\n")
        status_text.insert(tk.END, f"  Pressure: {turboPump.get_pressure():.2e} Torr\n")
    
    update_status()
    
    # Update status every 2 seconds
    def periodic_update():
        update_status()
        root.after(2000, periodic_update)
    
    root.after(2000, periodic_update)
    
    # Emergency stop button
    def emergency_stop():
        if messagebox.askyesno("Emergency Stop", "Are you sure you want to perform an emergency stop?"):
            try:
                supply27kV.disable_output()
                turboPump.stop_pump()
                messagebox.showinfo("Emergency Stop", "Emergency stop executed successfully")
                logger.warning("Emergency stop executed")
            except Exception as e:
                logger.error(f"Error during emergency stop: {e}")
                messagebox.showerror("Error", f"Emergency stop failed: {e}")
    
    emergency_button = ttk.Button(main_frame, text="EMERGENCY STOP", 
                                 command=emergency_stop, style="Emergency.TButton")
    emergency_button.grid(row=3, column=0, columnspan=2, pady=(10, 0))
    
    # Configure emergency button style
    style = ttk.Style()
    style.configure("Emergency.TButton", foreground="white", background="red")
    
    return root

if __name__ == "__main__":
    try:
        root = create_gui()
        root.mainloop()
    except Exception as e:
        logger.error(f"GUI error: {e}")
        messagebox.showerror("GUI Error", f"Failed to create GUI: {e}")
    finally:
        logger.info("Application shutting down")