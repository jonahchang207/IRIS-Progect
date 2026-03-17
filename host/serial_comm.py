"""
IRIS — Teensy Serial Communication
Auto-detects Teensy 4.1 USB serial port, sends commands, parses responses.
"""

import serial
import serial.tools.list_ports
import threading
import queue
import time
import logging
from typing import Optional

log = logging.getLogger(__name__)


def find_teensy_port() -> Optional[str]:
    """Auto-detect Teensy 4.1 by USB VID:PID (16C0:0483)."""
    for p in serial.tools.list_ports.comports():
        if p.vid == 0x16C0 and p.pid == 0x0483:
            log.info(f"Found Teensy at {p.device}")
            return p.device
    # Fallback: look for any ACM/usbmodem device
    for p in serial.tools.list_ports.comports():
        name = p.device.lower()
        if "acm" in name or "usbmodem" in name or "usbserial" in name:
            log.warning(f"Teensy not found by VID:PID, trying {p.device}")
            return p.device
    return None


class IRISSerial:
    """
    Thread-safe serial interface to the IRIS Teensy firmware.

    Spawns a reader thread that continuously reads responses
    and places them in a queue.
    """

    def __init__(self, port: str = "auto", baud: int = 115200, timeout: float = 5.0):
        self._port    = port
        self._baud    = baud
        self._timeout = timeout
        self._ser: Optional[serial.Serial] = None
        self._rx_queue: queue.Queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False

    # ---- connection ----------------------------------------

    def connect(self) -> bool:
        port = find_teensy_port() if self._port == "auto" else self._port
        if port is None:
            log.error("No Teensy found — check USB connection")
            return False
        try:
            self._ser = serial.Serial(port, self._baud, timeout=0.1)
            time.sleep(0.1)          # let Teensy reset
            self._ser.reset_input_buffer()
            self._running = True
            self._reader_thread = threading.Thread(
                target=self._reader_loop, daemon=True, name="iris-serial-rx")
            self._reader_thread.start()
            log.info(f"Connected to {port} @ {self._baud}")
            return True
        except serial.SerialException as e:
            log.error(f"Serial connect failed: {e}")
            return False

    def disconnect(self):
        self._running = False
        if self._reader_thread:
            self._reader_thread.join(timeout=1.0)
        if self._ser and self._ser.is_open:
            self._ser.close()
        log.info("Disconnected")

    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    # ---- reader thread -------------------------------------

    def _reader_loop(self):
        while self._running and self._ser and self._ser.is_open:
            try:
                line = self._ser.readline().decode("ascii", errors="ignore").strip()
                if line:
                    log.debug(f"<< {line}")
                    self._rx_queue.put(line)
            except serial.SerialException:
                break

    # ---- send / receive ------------------------------------

    def send(self, cmd: str):
        """Send a command string (newline appended automatically)."""
        if not self.is_connected():
            raise RuntimeError("Not connected")
        line = (cmd.strip() + "\n").encode("ascii")
        log.debug(f">> {cmd.strip()}")
        self._ser.write(line)

    def recv(self, timeout: Optional[float] = None) -> Optional[str]:
        """Block until a response line is received, or until timeout."""
        t = timeout if timeout is not None else self._timeout
        try:
            return self._rx_queue.get(timeout=t)
        except queue.Empty:
            return None

    def recv_all_pending(self) -> list:
        """Return all currently queued responses (non-blocking)."""
        lines = []
        while True:
            try:
                lines.append(self._rx_queue.get_nowait())
            except queue.Empty:
                break
        return lines

    # ---- high-level commands -------------------------------

    def move_absolute(self, angles_deg: list) -> bool:
        """
        Send MOVEA command and wait for OK.
        angles_deg: list of 6 floats.
        Returns True if firmware accepted the command.
        """
        cmd = "MOVEA " + " ".join(f"{a:.3f}" for a in angles_deg)
        self.send(cmd)
        resp = self.recv()
        return resp == "OK" if resp else False

    def wait_done(self, timeout: float = 30.0) -> bool:
        """
        Block until DONE is received (all joints at target).
        Returns False on timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = self.recv(timeout=0.5)
            if resp == "DONE":
                return True
            if resp and resp.startswith("ERR"):
                log.error(f"Firmware error: {resp}")
                return False
        log.warning("wait_done timed out")
        return False

    def get_position(self) -> Optional[list]:
        """
        Query and return current joint angles (degrees).
        Returns list of 6 floats or None on failure.
        """
        self.send("POS")
        resp = self.recv()
        if resp and resp.startswith("POS "):
            try:
                return [float(x) for x in resp[4:].split()]
            except ValueError:
                pass
        return None

    def get_status(self) -> Optional[str]:
        """Returns 'IDLE', 'MOVING', 'HOMING', or 'ESTOP'."""
        self.send("STATUS")
        resp = self.recv()
        if resp and resp.startswith("STATUS "):
            return resp[7:]
        return None

    def home(self, joint: Optional[int] = None) -> bool:
        """Home all joints, or a single joint (1-indexed)."""
        cmd = "HOME" if joint is None else f"HOME {joint}"
        self.send(cmd)
        resp = self.recv()
        return resp == "OK" if resp else False

    def estop(self):
        """Immediate stop all axes."""
        self.send("ESTOP")

    def enable(self):
        self.send("ENABLE")
        self.recv()

    def disable(self):
        self.send("DISABLE")
        self.recv()

    # ---- context manager -----------------------------------

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()
