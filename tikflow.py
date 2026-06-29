import json
import re
import shutil
import subprocess
import threading
from collections import deque
from datetime import datetime
from pathlib import Path


DEFAULT_ADB_TARGET = "192.168.0.20:35473"
DEFAULT_ADB_TARGETS = [DEFAULT_ADB_TARGET]
DEFAULT_SWIPE_INTERVAL = 20
MIN_SWIPE_INTERVAL = 5
MAX_SWIPE_INTERVAL = 60
ADB_COMMAND_TIMEOUT = 15
CONFIG_PATH = Path(__file__).with_name("tikflow-config.json")
LOCAL_ADB = Path(__file__).with_name("platform-tools") / "adb.exe"
ADB_COMMAND = str(LOCAL_ADB) if LOCAL_ADB.exists() else (shutil.which("adb") or "adb")
SWIPE_ARGS = ["shell", "input", "swipe", "540", "1800", "540", "400", "300"]


def parse_adb_devices(value):
    if value is None:
        lines = list(DEFAULT_ADB_TARGETS)
    elif isinstance(value, str):
        lines = value.splitlines()
    else:
        lines = []
        for item in value:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                target = str(item.get("target", "")).strip()
                lines.append(f"{name}={target}" if name else target)
            else:
                lines.extend(str(item).splitlines())

    devices = []
    seen = set()
    for line in lines:
        line = line.strip().rstrip(",")
        if not line:
            continue

        name = ""
        target = line
        if "=" in line:
            name, target = line.split("=", 1)
        elif "|" in line:
            name, target = line.split("|", 1)

        name = name.strip()
        target = target.strip()
        if not target or target in seen:
            continue

        seen.add(target)
        devices.append({"name": name, "target": target})
    return devices


def parse_adb_targets(value):
    return [device["target"] for device in parse_adb_devices(value)]


def format_adb_devices(devices):
    lines = []
    for device in devices:
        name = device.get("name", "").strip()
        target = device.get("target", "").strip()
        if not target:
            continue
        lines.append(f"{name}={target}" if name else target)
    return "\n".join(lines)


def device_label(device):
    name = device.get("name", "").strip()
    target = device.get("target", "").strip()
    return f"{name} ({target})" if name else target


class TikFlow:
    def __init__(self):
        self._logs = deque(maxlen=100)
        self._lock = threading.RLock()
        self._adb_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self.adb_devices = parse_adb_devices(DEFAULT_ADB_TARGETS)
        self.swipe_interval = DEFAULT_SWIPE_INTERVAL
        self._load_config()

    @property
    def adb_targets(self):
        return [device["target"] for device in self.adb_devices]

    @property
    def adb_target(self):
        return format_adb_devices(self.adb_devices)

    def _load_config(self):
        if not CONFIG_PATH.exists():
            return

        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            self.log(f"Unable to load config: {error}")
            return

        devices = data.get("adb_devices")
        if devices is None:
            devices = data.get("adb_targets")
        parsed_devices = parse_adb_devices(devices)
        if parsed_devices:
            self.adb_devices = parsed_devices

        try:
            interval = int(data.get("interval", self.swipe_interval))
        except (TypeError, ValueError):
            interval = self.swipe_interval
        if MIN_SWIPE_INTERVAL <= interval <= MAX_SWIPE_INTERVAL:
            self.swipe_interval = interval

    def _save_config(self):
        with self._lock:
            data = {
                "adb_devices": [dict(device) for device in self.adb_devices],
                "interval": self.swipe_interval,
            }
        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        with self._lock:
            self._logs.append(line)
        print(line, flush=True)

    def get_logs(self):
        with self._lock:
            return list(self._logs)

    def is_running(self):
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self, adb_target=DEFAULT_ADB_TARGET, adb_targets=None, swipe_interval=DEFAULT_SWIPE_INTERVAL):
        swipe_interval = int(swipe_interval)
        if swipe_interval < MIN_SWIPE_INTERVAL or swipe_interval > MAX_SWIPE_INTERVAL:
            raise ValueError(f"Interval must be between {MIN_SWIPE_INTERVAL} and {MAX_SWIPE_INTERVAL} seconds.")

        devices = parse_adb_devices(adb_targets if adb_targets is not None else adb_target)
        if not devices:
            raise ValueError("At least one ADB target is required.")

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                self.log("Start ignored because TikFlow is already running.")
                return False

            self.adb_devices = devices
            self.swipe_interval = swipe_interval
            self._save_config()
            self._stop_event.clear()
            labels = ", ".join(device_label(device) for device in self.adb_devices)
            self.log(f"Start requested. Targets: {labels}, interval: {self.swipe_interval}s.")
            self._thread = threading.Thread(target=self._run, name="tikflow-worker", daemon=True)
            self._thread.start()
            return True

    def stop(self):
        with self._lock:
            thread = self._thread
            if thread is None or not thread.is_alive():
                self.log("Stop ignored because TikFlow is already stopped.")
                return False
            self.log("Stop requested.")
            self._stop_event.set()

        thread.join(timeout=3)
        if not thread.is_alive():
            with self._lock:
                self._thread = None
        return True

    def status(self):
        with self._lock:
            devices = [dict(device) for device in self.adb_devices]
        return {
            "running": self.is_running(),
            "adb_target": format_adb_devices(devices),
            "adb_targets": [device["target"] for device in devices],
            "adb_devices": devices,
            "interval": self.swipe_interval,
            "logs": self.get_logs(),
        }

    def connect(self, adb_target=None, adb_targets=None):
        devices = parse_adb_devices(adb_targets if adb_targets is not None else adb_target)
        if not devices:
            raise ValueError("At least one ADB target is required.")

        with self._lock:
            self.adb_devices = devices
            self._save_config()

        self._connect_adb_devices()

    def _run_adb_command(self, command):
        with self._adb_lock:
            return subprocess.run(command, capture_output=True, check=True, timeout=ADB_COMMAND_TIMEOUT)

    def _connect_adb_device(self, device):
        target = device["target"]
        label = device_label(device)
        self.log(f"Connecting to ADB at {label}")
        result = self._run_adb_command([ADB_COMMAND, "connect", target])
        output = result.stdout.decode(errors="replace").strip()
        if output:
            self.log(f"{label}: {output}")

    def _connect_adb_devices(self):
        failures = []
        with self._lock:
            devices = [dict(device) for device in self.adb_devices]

        for device in devices:
            label = device_label(device)
            try:
                self._connect_adb_device(device)
            except subprocess.CalledProcessError as error:
                stderr = error.stderr.decode(errors="replace").strip() if error.stderr else ""
                failures.append(f"{label}: {stderr or error}")
                self.log(f"ADB connect failed for {label}: {stderr or error}")

        if failures and len(failures) == len(devices):
            raise RuntimeError("All ADB connections failed: " + "; ".join(failures))

    def _swipe_next_video(self, device):
        target = device["target"]
        self._run_adb_command([ADB_COMMAND, "-s", target, *SWIPE_ARGS])
        self.log(f"Swiped up on {device_label(device)}")

    def _swipe_all_targets(self):
        with self._lock:
            devices = [dict(device) for device in self.adb_devices]

        for device in devices:
            label = device_label(device)
            try:
                self._swipe_next_video(device)
            except subprocess.CalledProcessError as error:
                stderr = error.stderr.decode(errors="replace").strip() if error.stderr else ""
                self.log(f"Swipe failed for {label}: {stderr or error}")

    def _run(self):
        try:
            self._connect_adb_devices()
            self.log(f"TikFlow started. Swiping {len(self.adb_devices)} target(s) every {self.swipe_interval}s.")

            while not self._stop_event.wait(self.swipe_interval):
                self._swipe_all_targets()
        except FileNotFoundError:
            self.log("ADB command not found. Install Android platform-tools, add adb.exe to PATH, or place it in platform-tools\\adb.exe.")
        except subprocess.TimeoutExpired:
            self.log(f"ADB command timed out after {ADB_COMMAND_TIMEOUT}s.")
        except subprocess.CalledProcessError as error:
            stderr = error.stderr.decode(errors="replace").strip() if error.stderr else ""
            self.log(f"ADB command failed: {stderr or error}")
        except Exception as error:
            self.log(f"TikFlow error: {error}")
        finally:
            self._stop_event.clear()
            with self._lock:
                self._thread = None
            self.log("TikFlow stopped.")


def main():
    runner = TikFlow()
    runner.start()
    try:
        while runner.is_running():
            threading.Event().wait(0.5)
    except KeyboardInterrupt:
        runner.stop()


if __name__ == "__main__":
    main()

