import random
import subprocess
import time
from datetime import datetime


ADB_TARGET = "192.168.0.21:39293"
SWIPE_INTERVAL = 20
SWIPE_COMMAND = ["adb", "shell", "input", "swipe", "540", "1800", "540", "400", "300"]


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def run_adb_command(command):
    return subprocess.run(command, capture_output=True, check=True)


def connect_adb():
    log(f"Connecting to ADB at {ADB_TARGET}")
    result = run_adb_command(["adb", "connect", ADB_TARGET])
    output = result.stdout.decode(errors="replace").strip()
    if output:
        log(output)


def swipe_next_video():
    run_adb_command(SWIPE_COMMAND)
    log("Swiped up")


def main():
    connect_adb()
    log(f"TikFlow started. Swiping every {SWIPE_INTERVAL}s. Press Ctrl+C to stop.")

    while True:
        time.sleep(SWIPE_INTERVAL)
        try:
            swipe_next_video()
        except subprocess.CalledProcessError as error:
            stderr = error.stderr.decode(errors="replace").strip()
            log(f"Swipe failed: {stderr or error}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("TikFlow stopped.")