# TikFlow

TikFlow is a Termux-friendly TikTok scroll automation script for Android. It runs on the same Android device, connects to ADB over localhost wireless debugging, watches a small screenshot region, and swipes up when that region stops changing.

## Requirements

- Android 11 or newer
- Termux installed from F-Droid
- Wireless Debugging enabled in Android Developer Options
- No root required

## Setup

1. Install Termux from F-Droid.
2. Install Python and ADB:

   ```sh
   pkg install python adb
   ```

3. Install Python dependencies:

   ```sh
   pip install pillow numpy
   ```

4. Enable Wireless Debugging in Android Developer Options.
5. Connect ADB over localhost:

   ```sh
   adb connect localhost:5555
   ```

6. Run TikFlow:

   ```sh
   python tikflow.py
   ```

Stop the script with `Ctrl+C`.

## How It Works

- Connects to ADB with `adb connect localhost:5555`.
- Captures a screenshot every `0.5` seconds with `adb exec-out screencap -p`.
- Crops the top-left `200x200` pixel region.
- Compares consecutive cropped frames with Pillow and numpy.
- If the average pixel difference is below the threshold for `2` consecutive checks, it runs:

  ```sh
  adb shell input swipe 540 1200 540 300 300
  ```

- Waits a random `1.5` to `3.0` seconds after each swipe.
- Logs actions with timestamps until stopped.

## Tuning

You can adjust these constants in `tikflow.py`:

- `DIFF_THRESHOLD`
- `STABLE_CHECKS_BEFORE_SWIPE`
- `CHECK_INTERVAL_SECONDS`
- `CROP_BOX`
