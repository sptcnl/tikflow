import subprocess
import threading
from collections import deque
from datetime import datetime


DEFAULT_ADB_TARGET = "192.168.0.21:39293"
DEFAULT_SWIPE_INTERVAL = 20
MIN_SWIPE_INTERVAL = 5
MAX_SWIPE_INTERVAL = 60
SWIPE_COMMAND = ["adb", "shell", "input", "swipe", "540", "1800", "540", "400", "300"]


class TikFlow:
    def __init__(self):
        self._logs = deque(maxlen=100)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self.adb_target = DEFAULT_ADB_TARGET
        self.swipe_interval = DEFAULT_SWIPE_INTERVAL

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

    def start(self, adb_target=DEFAULT_ADB_TARGET, swipe_interval=DEFAULT_SWIPE_INTERVAL):
        swipe_interval = int(swipe_interval)
        if swipe_interval < MIN_SWIPE_INTERVAL or swipe_interval > MAX_SWIPE_INTERVAL:
            raise ValueError(f"Interval must be between {MIN_SWIPE_INTERVAL} and {MAX_SWIPE_INTERVAL} seconds.")

        adb_target = (adb_target or DEFAULT_ADB_TARGET).strip()
        if not adb_target:
            raise ValueError("ADB target is required.")

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False

            self.adb_target = adb_target
            self.swipe_interval = swipe_interval
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, name="tikflow-worker", daemon=True)
            self._thread.start()
            return True

    def stop(self):
        with self._lock:
            thread = self._thread
            if thread is None or not thread.is_alive():
                return False
            self._stop_event.set()

        thread.join(timeout=3)
        if not thread.is_alive():
            with self._lock:
                self._thread = None
        return True

    def status(self):
        return {
            "running": self.is_running(),
            "adb_target": self.adb_target,
            "interval": self.swipe_interval,
            "logs": self.get_logs(),
        }

    def _run_adb_command(self, command):
        return subprocess.run(command, capture_output=True, check=True)

    def _connect_adb(self):
        self.log(f"Connecting to ADB at {self.adb_target}")
        result = self._run_adb_command(["adb", "connect", self.adb_target])
        output = result.stdout.decode(errors="replace").strip()
        if output:
            self.log(output)

    def _swipe_next_video(self):
        self._run_adb_command(SWIPE_COMMAND)
        self.log("Swiped up")

    def _run(self):
        try:
            self._connect_adb()
            self.log(f"TikFlow started. Swiping every {self.swipe_interval}s.")

            while not self._stop_event.wait(self.swipe_interval):
                try:
                    self._swipe_next_video()
                except subprocess.CalledProcessError as error:
                    stderr = error.stderr.decode(errors="replace").strip() if error.stderr else ""
                    self.log(f"Swipe failed: {stderr or error}")
        except FileNotFoundError:
            self.log("ADB command not found. Make sure adb is installed and available in PATH.")
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
