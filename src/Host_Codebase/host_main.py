import tkinter as tk

import power_control as PC
import vacuum_control as VC
import communication as com

RPi_3b = com.SSHClient("RPi_1_IP", 22, "username", "password", "command_to_send {}")
turboPump = VC.TurboPump("name")
supply27kV = PC.PowerSupply("Fusor Supply", maxVoltage=27000, maxCurrent=0.040)

root = tk.Tk()
root.title("Fusor Control Panel")
root.geometry("400x300")
root.default_font = ("Times New Roman", 8)

powerControlLabel = tk.Label(root, text="Desired Fusor Supply Voltage", font=root.default_font)
powerControlLabel.grid(row=0, column=0, padx=10, pady=10)

powerControlScale = tk.Scale(root, from_=0, to=supply27kV.maxVoltage, orient="horizontal")
powerControlScale.grid(row=1,column=0, padx=10, pady=10)

powerControlButton = tk.Button(root, text="Set", command=lambda: supply27kV.set_voltage(voltageSetting=int(powerControlScale.get())))
powerControlButton.grid(row=1,column=1, padx=10, pady=10)
root.mainloop()