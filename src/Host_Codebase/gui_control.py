# gui_control.py — CustomTkinter GUI for Farnsworth Fusor
# Mode-select menu, Manual Control Panel, and Automatic Control Panel

import customtkinter as ctk
import tkinter.messagebox

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FusorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Fusor Control System")
        self.geometry("1000x700")

        self.mode_select_frame = ModeSelectFrame(self, self.switch_to_manual, self.switch_to_auto)
        self.manual_frame = ManualControlFrame(self)
        self.auto_frame = AutoControlFrame(self)

        self.mode_select_frame.pack(fill="both", expand=True)

    def switch_to_manual(self):
        self.mode_select_frame.pack_forget()
        self.manual_frame.pack(fill="both", expand=True)

    def switch_to_auto(self):
        self.mode_select_frame.pack_forget()
        self.auto_frame.pack(fill="both", expand=True)


class ModeSelectFrame(ctk.CTkFrame):
    def __init__(self, parent, manual_cmd, auto_cmd):
        super().__init__(parent)

        self.label = ctk.CTkLabel(self, text="Fusor Main Panel\n\nChoose Operation Mode", font=("Arial", 24, "bold"))
        self.label.pack(pady=20)

        self.buttons_frame = ctk.CTkFrame(self)
        self.buttons_frame.pack(pady=20)

        self.manual_button = ctk.CTkButton(self.buttons_frame, text="Manual Button", width=200, height=100, command=manual_cmd)
        self.manual_button.grid(row=0, column=0, padx=40)

        self.auto_button = ctk.CTkButton(self.buttons_frame, text="Automatic Button", width=200, height=100, command=auto_cmd)
        self.auto_button.grid(row=0, column=1, padx=40)


class ManualControlFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.label = ctk.CTkLabel(self, text="Fusor Manual Control Panel", font=("Arial", 20, "bold"))
        self.label.pack(pady=10)

        self.power_frame = ctk.CTkFrame(self)
        self.power_frame.pack(pady=5)
        ctk.CTkSwitch(self.power_frame, text="Power Supply Enable").pack(side="left", padx=10)
        ctk.CTkSlider(self.power_frame, from_=0, to=100, orientation="horizontal").pack(side="left", padx=10)

        self.pumps_frame = ctk.CTkFrame(self)
        self.pumps_frame.pack(pady=5)
        ctk.CTkLabel(self.pumps_frame, text="Mechanical Vacuum Pump").pack()
        ctk.CTkSlider(self.pumps_frame, from_=0, to=100).pack()
        ctk.CTkLabel(self.pumps_frame, text="Turbo Vacuum Pump").pack()
        ctk.CTkSlider(self.pumps_frame, from_=0, to=100).pack()

        self.valve_frame = ctk.CTkFrame(self)
        self.valve_frame.pack(pady=5)
        for i in range(1, 7):
            ctk.CTkSlider(self.valve_frame, from_=0, to=100).pack(side="left", padx=5)

        self.readouts_frame = ctk.CTkFrame(self)
        self.readouts_frame.pack(pady=5)
        for label in ["Power Supply Voltage", "Power Supply Current", "Pressure Sensor 1", "Sensor 2", "Sensor 3"]:
            ctk.CTkLabel(self.readouts_frame, text=label, width=140).pack(side="left", padx=5)

        self.camera_frame = ctk.CTkFrame(self, width=300, height=150)
        self.camera_frame.pack(pady=10)
        ctk.CTkLabel(self.camera_frame, text="[ Camera View Placeholder ]").pack()

        self.neutron_frame = ctk.CTkFrame(self, width=300, height=150)
        self.neutron_frame.pack(pady=10)
        ctk.CTkLabel(self.neutron_frame, text="[ Neutron Counts Placeholder ]").pack()


class AutoControlFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.label = ctk.CTkLabel(self, text="Fusor Automatic Control Panel", font=("Arial", 20, "bold"))
        self.label.pack(pady=10)

        self.log = ctk.CTkTextbox(self, height=100)
        self.log.pack(pady=10)
        self.log.insert("end", "[System status log output]\n")

        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.pack(pady=5)
        for name in ["Startup", "Shutdown", "Emergency Shutoff"]:
            ctk.CTkButton(self.control_frame, text=name, width=120).pack(side="left", padx=10)

        self.readouts_frame = ctk.CTkFrame(self)
        self.readouts_frame.pack(pady=5)
        for label in ["Power Supply Voltage", "Power Supply Current", "Pressure Sensor 1", "Sensor 2", "Sensor 3"]:
            ctk.CTkLabel(self.readouts_frame, text=label, width=140).pack(side="left", padx=5)

        self.camera_frame = ctk.CTkFrame(self, width=300, height=150)
        self.camera_frame.pack(pady=10)
        ctk.CTkLabel(self.camera_frame, text="[ Camera View Placeholder ]").pack()

        self.neutron_frame = ctk.CTkFrame(self, width=300, height=150)
        self.neutron_frame.pack(pady=10)
        ctk.CTkLabel(self.neutron_frame, text="[ Neutron Counts Placeholder ]").pack()


if __name__ == "__main__":
    app = FusorApp()
    app.mainloop()
