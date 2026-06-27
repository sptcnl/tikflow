import io
import random
import subprocess
import time
from datetime import datetime

import numpy as np
from PIL import Image


ADB_TARGET = "192.168.0.21:39293"
CHECK_INTERVAL_SECONDS = 0.5
CROP_BOX = (30, 260, 120, 360)  # 코인 아이콘 영역
DIFF_THRESHOLD = 3.0
STABLE_CHECKS_BEFORE_SWIPE = 2
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


def capture_crop():
    result = run_adb_command(["adb", "exec-out", "screencap", "-p"])
    image = Image.open(io.BytesIO(result.stdout)).convert("RGB")
    return image.crop(CROP_BOX)


def frame_difference(previous_frame, current_frame):
    previous = np.asarray(previous_frame, dtype=np.int16)
    current = np.asarray(current_frame, dtype=np.int16)
    return float(np.mean(np.abs(current - previous)))


def swipe_next_video():
    run_adb_command(SWIPE_COMMAND)
    delay = random.uniform(1.5, 3.0)
    log(f"Swiped up; sleeping {delay:.2f}s")
    time.sleep(delay)


def main():
    previous_frame = None
    stable_checks = 0

    connect_adb()
    log("TikFlow started. Press Ctrl+C to stop.")

    while True:
        try:
            current_frame = capture_crop()
        except subprocess.CalledProcessError as error:
            stderr = error.stderr.decode(errors="replace").strip()
            log(f"ADB command failed: {stderr or error}")
            time.sleep(1)
            continue
        except Exception as error:
            log(f"Screenshot capture failed: {error}")
            time.sleep(1)
            continue

        if previous_frame is not None:
            diff = frame_difference(previous_frame, current_frame)

            if diff < DIFF_THRESHOLD:
                stable_checks += 1
                log(f"Region unchanged: diff={diff:.2f}, stable_checks={stable_checks}")
            else:
                if stable_checks:
                    log(f"Region changed: diff={diff:.2f}; resetting stable checks")
                stable_checks = 0

            if stable_checks >= STABLE_CHECKS_BEFORE_SWIPE:
                try:
                    log("Content appears paused or ended; swiping to next video")
                    swipe_next_video()
                except subprocess.CalledProcessError as error:
                    stderr = error.stderr.decode(errors="replace").strip()
                    log(f"Swipe failed: {stderr or error}")

                previous_frame = None
                stable_checks = 0
                continue

        previous_frame = current_frame
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("TikFlow stopped.")