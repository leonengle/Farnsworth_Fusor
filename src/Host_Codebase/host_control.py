"""
Host-side controller for Farnsworth Fusor

Changes:
- Keeps a persistent SSH connection open for multiple commands
- Adds a lightweight TCP telemetry server the TARGET can connect to
  (hybrid SSH/TCP: SSH -> commands; TCP -> streaming data)
- Replaces stdin-based "telemetry_listener" with a proper TCP listener
- Removes hardcoded credentials; uses placeholders + env overrides
"""

import os
import socket
import threading
import logging
import paramiko
from dataclasses import dataclass
from typing import Callable, Optional

# ---------- Config ----------

@dataclass
class HostConfig:
    # Use placeholders (replace at deploy time or override via env)
    target_host: str = os.getenv("FUSOR_TARGET_HOST", "<<192.168.1.100>>")
    target_ssh_port: int = int(os.getenv("FUSOR_TARGET_SSH_PORT", "2222"))
    target_username: str = os.getenv("FUSOR_TARGET_USERNAME", "<<PI_USERNAME>>")
    target_password: str = os.getenv("FUSOR_TARGET_PASSWORD", "<<PI_PASSWORD>>")

    # Telemetry: host runs a TCP server; target connects and streams lines
    telemetry_bind_host: str = os.getenv("FUSOR_TELEM_BIND_HOST", "0.0.0.0")
    telemetry_bind_port: int = int(os.getenv("FUSOR_TELEM_BIND_PORT", "5001"))

# ---------- Logging ----------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("host_control.log", mode="a")]
)
log = logging.getLogger("host")

# ---------- SSH Controller ----------

class SSHController:
    def __init__(self, cfg: HostConfig):
        self.cfg = cfg
        self.client: Optional[paramiko.SSHClient] = None
        self._lock = threading.Lock()

    def connect(self) -> bool:
        with self._lock:
            if self.client:
                return True
            try:
                c = paramiko.SSHClient()
                c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                c.connect(
                    hostname=self.cfg.target_host,
                    port=self.cfg.target_ssh_port,
                    username=self.cfg.target_username,
                    password=self.cfg.target_password,
                    timeout=10
                )
                self.client = c
                log.info(f"SSH connected to {self.cfg.target_host}:{self.cfg.target_ssh_port}")
                return True
            except Exception as e:
                log.error(f"SSH connect failed: {e}")
                self.client = None
                return False

    def is_connected(self) -> bool:
        with self._lock:
            if not self.client:
                return False
            t = self.client.get_transport()
            return t is not None and t.is_active()

    def send_command(self, command: str, timeout: float = 10.0) -> str:
        """
        Sends a command over the existing SSH connection.
        Keeps the SSH connection alive (no channel teardown of the transport).
        Returns combined stdout/stderr text (best-effort).
        """
        with self._lock:
            if not self.is_connected():
                raise RuntimeError("SSH not connected")
            try:
                # Use exec_command which opens a short-lived channel but keeps the transport alive
                stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
                out = stdout.read().decode(errors="ignore")
                err = stderr.read().decode(errors="ignore")
                text = (out + err).strip()
                log.info(f"SSH cmd '{command}' -> {text!r}")
                return text
            except Exception as e:
                log.error(f"SSH send_command error: {e}")
                raise

    def close(self):
        with self._lock:
            if self.client:
                try:
                    self.client.close()
                except Exception:
                    pass
                self.client = None
                log.info("SSH disconnected")

# ---------- Telemetry TCP Server (Host) ----------

class TelemetryTCPServer:
    """
    Simple line-oriented TCP server.
    Target connects and sends newline-delimited telemetry frames (e.g. 'V=12.3,I=0.42,P1=3.1').
    We invoke a callback(data: str) for each line.
    """
    def __init__(self, bind_host: str, bind_port: int, on_line: Callable[[str], None]):
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.on_line = on_line
        self._srv_sock: Optional[socket.socket] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()

    def start(self):
        if self._accept_thread and self._accept_thread.is_alive():
            return
        self._stop_evt.clear()
        self._srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv_sock.bind((self.bind_host, self.bind_port))
        self._srv_sock.listen(1)
        log.info(f"Telemetry server listening on {self.bind_host}:{self.bind_port}")

        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def _accept_loop(self):
        while not self._stop_evt.is_set():
            try:
                self._srv_sock.settimeout(1.0)
                try:
                    conn, addr = self._srv_sock.accept()
                except socket.timeout:
                    continue
                log.info(f"Telemetry client connected from {addr}")
                self._handle_client(conn, addr)
            except Exception as e:
                log.error(f"Telemetry accept loop error: {e}")

    def _handle_client(self, conn: socket.socket, addr):
        with conn:
            buf = b""
            while not self._stop_evt.is_set():
                try:
                    chunk = conn.recv(4096)
                    if not chunk:
                        log.info(f"Telemetry client {addr} disconnected")
                        break
                    buf += chunk
                    # process lines
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        text = line.decode(errors="ignore").strip()
                        if text:
                            self.on_line(text)
                except Exception as e:
                    log.error(f"Telemetry client error: {e}")
                    break

    def stop(self):
        self._stop_evt.set()
        try:
            if self._srv_sock:
                self._srv_sock.close()
        except Exception:
            pass
        log.info("Telemetry server stopped")

# ---------- Simple CLI entry (optional) ----------

def _print_help():
    print("Commands: on | off | move:<steps> | exit")

def main():
    cfg = HostConfig()
    ssh = SSHController(cfg)
    if not ssh.connect():
        print("SSH connection failed. Check config/placeholders.")
        return

    # Start telemetry server that just logs incoming lines
    def log_line(s: str):
        log.info(f"[TELEM] {s}")
        with open("telemetry.log", "a") as f:
            f.write(s + "\n")

    telem = TelemetryTCPServer(cfg.telemetry_bind_host, cfg.telemetry_bind_port, log_line)
    telem.start()

    try:
        _print_help()
        while True:
            cmd = input("> ").strip()
            if cmd == "exit":
                break
            elif cmd == "on":
                print(ssh.send_command("LED_ON"))
            elif cmd == "off":
                print(ssh.send_command("LED_OFF"))
            elif cmd.startswith("move:"):
                _, _, steps = cmd.partition(":")
                print(ssh.send_command(f"MOVE_VAR:{int(steps)}"))
            else:
                _print_help()
    except KeyboardInterrupt:
        pass
    finally:
        telem.stop()
        ssh.close()

if __name__ == "__main__":
    main()
