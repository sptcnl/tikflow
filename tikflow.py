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


def is_enabled_value(value):
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return value is not False


def parse_adb_devices(value):
    raw_devices = []
    if value is None:
        raw_devices = [{"name": "", "target": target, "enabled": True} for target in DEFAULT_ADB_TARGETS]
    elif isinstance(value, str):
        raw_devices = [{"name": "", "target": line, "enabled": True} for line in value.splitlines()]
    else:
        for item in value:
            if isinstance(item, dict):
                raw_devices.append({
                    "name": str(item.get("name", "")).strip(),
                    "target": str(item.get("target", "")).strip(),
                    "enabled": is_enabled_value(item.get("enabled", True)),
                })
            else:
                raw_devices.extend({"name": "", "target": line, "enabled": True} for line in str(item).splitlines())

    devices = []
    seen = set()
    for raw_device in raw_devices:
        name = raw_device.get("name", "").strip()
        target = raw_device.get("target", "").strip().rstrip(",")
        enabled = is_enabled_value(raw_device.get("enabled", True))
        if not target:
            continue

        if "=" in target:
            name, target = target.split("=", 1)
        elif "|" in target:
            name, target = target.split("|", 1)

        name = name.strip()
        target = target.strip()
        if not target or target in seen:
            continue

        seen.add(target)
        devices.append({"name": name, "target": target, "enabled": enabled})
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

    def _active_adb_devices(self):
        return [dict(device) for device in self.adb_devices if is_enabled_value(device.get("enabled", True))]
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
        active_devices = [device for device in devices if is_enabled_value(device.get("enabled", True))]
        if not active_devices:
            raise ValueError("At least one enabled ADB target is required.")

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                self.adb_devices = devices
                self.swipe_interval = swipe_interval
                self._save_config()
                labels = ", ".join(device_label(device) for device in active_devices)
                self.log(f"Start updated while running. Targets: {labels}, interval: {self.swipe_interval}s.")
                self._connect_adb_devices(active_devices)
                return False

            self.adb_devices = devices
            self.swipe_interval = swipe_interval
            self._save_config()
            self._stop_event.clear()
            labels = ", ".join(device_label(device) for device in active_devices)
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
        active_devices = [device for device in devices if is_enabled_value(device.get("enabled", True))]
        if not active_devices:
            raise ValueError("At least one enabled ADB target is required.")

        with self._lock:
            self.adb_devices = devices
            self._save_config()

        self._connect_adb_devices(active_devices)

    def connect_device(self, device, adb_targets=None):
        devices = parse_adb_devices(adb_targets) if adb_targets is not None else []
        selected = parse_adb_devices([device])
        if not selected:
            raise ValueError("ADB target is required.")

        with self._lock:
            if devices:
                self.adb_devices = devices
                self._save_config()

        self._connect_adb_device(selected[0])

    def start_device(self, adb_targets, index=None, target=None, swipe_interval=DEFAULT_SWIPE_INTERVAL):
        devices = parse_adb_devices(adb_targets)
        if not devices:
            raise ValueError("At least one ADB target is required.")

        selected = None
        if index is not None and 0 <= index < len(devices):
            devices[index]["enabled"] = True
            selected = devices[index]
        elif target:
            for device in devices:
                if device.get("target") == target:
                    device["enabled"] = True
                    selected = device
                    break

        if selected is None:
            raise ValueError("Device not found.")

        with self._lock:
            running = self.is_running()
            self.adb_devices = devices
            self._save_config()

        if running:
            self._connect_adb_device(selected)
            self.log(f"{device_label(selected)} started.")
            return False

        self.start(adb_targets=devices, swipe_interval=swipe_interval)
        return True
    def set_device_enabled(self, adb_targets, index=None, target=None, enabled=True):
        devices = parse_adb_devices(adb_targets)
        if not devices:
            raise ValueError("At least one ADB target is required.")

        changed = False
        changed_label = target or "Device"
        if index is not None and 0 <= index < len(devices):
            devices[index]["enabled"] = bool(enabled)
            changed_label = device_label(devices[index])
            changed = True
        elif target:
            for device in devices:
                if device.get("target") == target:
                    device["enabled"] = bool(enabled)
                    changed_label = device_label(device)
                    changed = True
                    break

        if not changed:
            raise ValueError("Device not found.")

        with self._lock:
            self.adb_devices = devices
            self._save_config()
        self.log(f"{changed_label} {'enabled' if enabled else 'stopped'}.")
        if not enabled and not self._active_adb_devices() and self.is_running():
            self.stop()

    def set_all_devices_enabled(self, adb_targets, enabled=True):
        devices = parse_adb_devices(adb_targets)
        if not devices:
            raise ValueError("At least one ADB target is required.")

        for device in devices:
            device["enabled"] = bool(enabled)

        with self._lock:
            self.adb_devices = devices
            self._save_config()
        self.log(f"All targets {'enabled' if enabled else 'stopped'}.")
        if not enabled and self.is_running():
            self.stop()
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

    def _connect_adb_devices(self, devices=None):
        failures = []
        if devices is None:
            with self._lock:
                devices = self._active_adb_devices()
        else:
            devices = [dict(device) for device in devices]

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
            devices = self._active_adb_devices()

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
            self.log(f"TikFlow started. Swiping {len(self._active_adb_devices())} target(s) every {self.swipe_interval}s.")

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

