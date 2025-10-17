# CustomTkinter GUI wired to SSH (commands) + TCP (telemetry)
# Run: python gui_control.py

import os
import customtkinter as ctk
import tkinter.messagebox as mbox
import threading
from queue import Queue, Empty

# Import host control objects
from host_control import start_embedded_ssh_server, HostConfig, SSHController, TelemetryTCPServer

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FusorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        start_embedded_ssh_server(bind_host="0.0.0.0", port=2222)
        self.title("Fusor Control System")
        self.geometry("1100x750")

        # --- Backend wiring ---
        self.cfg = HostConfig()  # uses placeholders/env
        self.ssh = SSHController(self.cfg)
        self.telemetry_queue: Queue[str] = Queue()
        self.telemetry_server = TelemetryTCPServer(
            self.cfg.telemetry_bind_host,
            self.cfg.telemetry_bind_port,
            on_line=self.telemetry_queue.put
        )

        # --- Frames ---
        self.mode_select_frame = ModeSelectFrame(self, self.switch_to_manual, self.switch_to_auto, self.connect_ssh, self.start_telem)
        self.manual_frame = ManualControlFrame(self, self.send_cmd)
        self.auto_frame = AutoControlFrame(self, self.send_cmd)

        self.mode_select_frame.pack(fill="both", expand=True)

        # Periodic GUI polling to process telemetry lines
        self.after(200, self._drain_telem_queue)

    # ----- Backend actions -----

    def connect_ssh(self):
        # Attempt connection using current config; notify user
        connected = self.ssh.connect()
        if connected:
            mbox.showinfo("SSH", f"Connected to {self.cfg.target_host}:{self.cfg.target_ssh_port}")
        else:
            mbox.showerror("SSH", "Failed to connect. Check IP/user/password placeholders or environment variables.")

    def start_telem(self):
        try:
            self.telemetry_server.start()
            mbox.showinfo("Telemetry", f"Listening on {self.cfg.telemetry_bind_host}:{self.cfg.telemetry_bind_port}")
        except Exception as e:
            mbox.showerror("Telemetry", f"Failed to start telemetry server:\n{e}")

    def send_cmd(self, cmd: str):
        try:
            if not self.ssh.is_connected():
                raise RuntimeError("SSH is not connected.")
            resp = self.ssh.send_command(cmd)
            # route to auto log + status
            self.auto_frame.append_log(f"$ {cmd}\n{resp}\n")
        except Exception as e:
            mbox.showerror("Command Error", str(e))

    def _drain_telem_queue(self):
        """
        Pull lines from telemetry queue, parse simple key=value pairs,
        and update readouts in both Manual and Auto panels.
        Accepts arbitrary lines; unparseable lines go to auto log.
        """
        parsed_any = False
        try:
            while True:
                line = self.telemetry_queue.get_nowait()
                # Expected example: "V=12.3,I=0.42,P1=3.1,P2=3.2,P3=3.3"
                kv = {}
                for chunk in line.split(","):
                    if "=" in chunk:
                        k, v = chunk.split("=", 1)
                        kv[k.strip().upper()] = v.strip()
                if kv:
                    parsed_any = True
                    self.manual_frame.update_readouts(kv)
                    self.auto_frame.update_readouts(kv)
                else:
                    self.auto_frame.append_log(f"[TELEM] {line}\n")
        except Empty:
            pass

        # Re-schedule
        self.after(200 if parsed_any else 400, self._drain_telem_queue)

    # ----- Navigation -----

    def switch_to_manual(self):
        self._show_only(self.manual_frame)

    def switch_to_auto(self):
        self._show_only(self.auto_frame)

    def _show_only(self, frame):
        for f in (self.mode_select_frame, self.manual_frame, self.auto_frame):
            f.pack_forget()
        frame.pack(fill="both", expand=True)

# ---------- Frames ----------

class ModeSelectFrame(ctk.CTkFrame):
    def __init__(self, parent, manual_cmd, auto_cmd, connect_cmd, start_telem_cmd):
        super().__init__(parent)

        title = ctk.CTkLabel(self, text="Fusor Main Panel\n\nChoose Operation Mode", font=("Arial", 24, "bold"))
        title.pack(pady=20)

        # Connection controls
        conn = ctk.CTkFrame(self)
        conn.pack(pady=10)
        ctk.CTkLabel(conn, text="Tip: set env vars FUSOR_TARGET_HOST / USERNAME / PASSWORD, etc.").pack(padx=10, pady=6)
        btns = ctk.CTkFrame(self)
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="Connect SSH", width=160, height=40, command=connect_cmd).grid(row=0, column=0, padx=8)
        ctk.CTkButton(btns, text="Start Telemetry Server", width=200, height=40, command=start_telem_cmd).grid(row=0, column=1, padx=8)

        nav = ctk.CTkFrame(self)
        nav.pack(pady=20)
        ctk.CTkButton(nav, text="Manual Mode", width=200, height=80, command=manual_cmd).grid(row=0, column=0, padx=20)
        ctk.CTkButton(nav, text="Automatic Mode", width=200, height=80, command=auto_cmd).grid(row=0, column=1, padx=20)

class ManualControlFrame(ctk.CTkFrame):
    def __init__(self, parent, send_cmd_cb):
        super().__init__(parent)
        self.send = send_cmd_cb

        ctk.CTkLabel(self, text="Fusor Manual Control Panel", font=("Arial", 20, "bold")).pack(pady=10)

        # Power Supply
        pf = ctk.CTkFrame(self)
        pf.pack(pady=5)
        self.psu_switch = ctk.CTkSwitch(pf, text="Power Supply Enable")
        self.psu_switch.pack(side="left", padx=10)
        ctk.CTkButton(pf, text="Apply", command=self._apply_psu).pack(side="left", padx=10)

        # Motion example
        mf = ctk.CTkFrame(self)
        mf.pack(pady=5)
        ctk.CTkLabel(mf, text="Move Steps:").pack(side="left", padx=6)
        self.move_entry = ctk.CTkEntry(mf, width=120)
        self.move_entry.insert(0, "100")
        self.move_entry.pack(side="left", padx=6)
        ctk.CTkButton(mf, text="Move", command=self._move_steps).pack(side="left", padx=6)

        # Readouts
        self.readouts = {}
        rf = ctk.CTkFrame(self)
        rf.pack(pady=10)
        for label in ["V", "I", "P1", "P2", "P3"]:
            frame = ctk.CTkFrame(rf)
            frame.pack(side="left", padx=8)
            ctk.CTkLabel(frame, text=label, width=120).pack()
            var = ctk.StringVar(value="—")
            ctk.CTkLabel(frame, textvariable=var, width=120, font=("Arial", 16, "bold")).pack()
            self.readouts[label] = var

    def _apply_psu(self):
        self.send("LED_ON" if self.psu_switch.get() else "LED_OFF")

    def _move_steps(self):
        try:
            steps = int(self.move_entry.get())
        except ValueError:
            mbox.showerror("Input", "Steps must be an integer")
            return
        self.send(f"MOVE_VAR:{steps}")

    def update_readouts(self, kv):
        for k, var in self.readouts.items():
            if k in kv:
                var.set(kv[k])

class AutoControlFrame(ctk.CTkFrame):
    def __init__(self, parent, send_cmd_cb):
        super().__init__(parent)
        self.send = send_cmd_cb

        ctk.CTkLabel(self, text="Fusor Automatic Control Panel", font=("Arial", 20, "bold")).pack(pady=10)

        # Log textbox
        self.log = ctk.CTkTextbox(self, height=160)
        self.log.pack(pady=10)
        self.append_log("[System status log output]\n")

        # Control buttons wired to SSH
        cf = ctk.CTkFrame(self)
        cf.pack(pady=5)
        ctk.CTkButton(cf, text="Startup", width=140, command=lambda: self.send("STARTUP_SEQUENCE")).pack(side="left", padx=10)
        ctk.CTkButton(cf, text="Shutdown", width=140, command=lambda: self.send("SHUTDOWN_SEQUENCE")).pack(side="left", padx=10)
        ctk.CTkButton(cf, text="Emergency Shutoff", width=180, command=lambda: self.send("EMERGENCY_OFF")).pack(side="left", padx=10)

        # Readouts
        self.readouts = {}
        rf = ctk.CTkFrame(self)
        rf.pack(pady=10)
        for label in ["V", "I", "P1", "P2", "P3"]:
            frame = ctk.CTkFrame(rf)
            frame.pack(side="left", padx=8)
            ctk.CTkLabel(frame, text=label, width=120).pack()
            var = ctk.StringVar(value="—")
            ctk.CTkLabel(frame, textvariable=var, width=120, font=("Arial", 16, "bold")).pack()
            self.readouts[label] = var

    def append_log(self, text: str):
        self.log.insert("end", text)
        self.log.see("end")

    def update_readouts(self, kv):
        for k, var in self.readouts.items():
            if k in kv:
                var.set(kv[k])

if __name__ == "__main__":
    app = FusorApp()
    app.mainloop()
