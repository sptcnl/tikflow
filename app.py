from flask import Flask, jsonify, render_template_string, request

from tikflow import DEFAULT_ADB_TARGET, DEFAULT_SWIPE_INTERVAL, TikFlow


app = Flask(__name__)
runner = TikFlow()


PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TikFlow</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101216;
      --panel: #191d24;
      --panel-2: #202632;
      --text: #eef2f7;
      --muted: #99a3b3;
      --border: #313847;
      --accent: #22c55e;
      --danger: #ef4444;
      --warning: #f59e0b;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--text);
    }

    main {
      width: min(960px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 20px;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      line-height: 1.1;
      letter-spacing: 0;
    }

    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-width: 116px;
      justify-content: center;
      padding: 9px 12px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel);
      color: var(--muted);
      font-weight: 700;
    }

    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--danger);
      box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.14);
    }

    .status.running { color: var(--text); }
    .status.running .dot {
      background: var(--accent);
      box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.16);
    }

    section {
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel);
      padding: 18px;
      margin-bottom: 16px;
    }

    .controls {
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
      align-items: end;
    }

    label {
      display: block;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }

    input[type="text"], input[type="number"] {
      width: 100%;
      min-height: 42px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel-2);
      color: var(--text);
      padding: 0 12px;
      font-size: 15px;
      outline: none;
    }

    input:focus { border-color: #5b6474; }

    .device-panel {
      display: grid;
      gap: 10px;
    }

    .device-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .device-header label { margin-bottom: 0; }

    .device-tools {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .device-row.stopped input[type="text"] { opacity: 0.62; }
    .device-action { padding: 0 10px; }
    .device-list {
      display: grid;
      gap: 10px;
    }

    .device-row {
      display: grid;
      grid-template-columns: minmax(110px, 0.4fr) minmax(170px, 1fr) 72px 72px 42px;
      gap: 10px;
      align-items: center;
    }


    .interval-row {
      display: grid;
      grid-template-columns: 1fr 88px;
      gap: 12px;
      align-items: center;
    }

    input[type="range"] { width: 100%; }


    button {
      min-height: 42px;
      border: 0;
      border-radius: 8px;
      color: #08110c;
      font-weight: 800;
      cursor: pointer;
      font-size: 15px;
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.5;
    }

    #startBtn, .device-start { background: var(--accent); }
    #stopBtn, .device-stop { background: var(--danger); color: #fff; }
    #addDeviceBtn, .device-remove { background: var(--panel-2); color: var(--text); border: 1px solid var(--border); }

    .message {
      min-height: 20px;
      margin-top: 12px;
      color: var(--warning);
      font-size: 13px;
    }

    .log-header {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
    }

    h2 {
      margin: 0;
      font-size: 16px;
      letter-spacing: 0;
    }

    .polling {
      color: var(--muted);
      font-size: 13px;
    }

    pre {
      margin: 0;
      height: 440px;
      overflow: auto;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: #0b0d11;
      padding: 14px;
      color: #d7dee9;
      font: 13px/1.5 Consolas, Monaco, monospace;
      white-space: pre-wrap;
    }

    @media (max-width: 720px) {
      main { width: min(100vw - 24px, 960px); padding: 20px 0; }
      header { align-items: flex-start; flex-direction: column; }
      .controls { grid-template-columns: 1fr; }
      .device-row { grid-template-columns: 1fr; }
      pre { height: 360px; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>TikFlow</h1>
      <div id="status" class="status"><span class="dot"></span><span>Stopped</span></div>
    </header>

    <section>
      <div class="controls">
        <div class="device-panel">
          <div class="device-header">
            <label>ADB targets</label>
            <div class="device-tools">
              <button id="startBtn" type="button">All Start</button>
              <button id="stopBtn" type="button">All Stop</button>
              <button id="addDeviceBtn" type="button">Add</button>
            </div>
          </div>
          <div id="deviceRows" class="device-list"></div>
          <div>
            <label for="intervalRange">Interval: <span id="intervalLabel">{{ interval }}</span>s</label>
            <div class="interval-row">
              <input id="intervalRange" type="range" min="5" max="60" value="{{ interval }}">
              <input id="intervalInput" type="number" min="5" max="60" value="{{ interval }}">
            </div>
          </div>
        </div>
      </div>
      <div id="message" class="message"></div>
    </section>

    <section>
      <div class="log-header">
        <h2>Live log</h2>
        <span class="polling">Refreshes every 2s</span>
      </div>
      <pre id="logs">Waiting for logs...</pre>
    </section>
  </main>

  <script>
    const deviceRows = document.getElementById('deviceRows');
    const addDeviceBtn = document.getElementById('addDeviceBtn');
    const intervalRange = document.getElementById('intervalRange');
    const intervalInput = document.getElementById('intervalInput');
    const intervalLabel = document.getElementById('intervalLabel');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusEl = document.getElementById('status');
    const messageEl = document.getElementById('message');
    const logsEl = document.getElementById('logs');
    let deviceRowsSynced = false;
    let deviceRowsDirty = false;
    let isRunning = false;

    function clampInterval(value) {
      const parsed = Number.parseInt(value, 10);
      if (Number.isNaN(parsed)) return 20;
      return Math.min(60, Math.max(5, parsed));
    }

    function setIntervalValue(value) {
      const next = clampInterval(value);
      intervalRange.value = next;
      intervalInput.value = next;
      intervalLabel.textContent = next;
    }

    function updateRowState(row) {
      const enabled = row.dataset.enabled !== 'false';
      row.classList.toggle('stopped', !enabled);
      const startButton = row.querySelector('.device-start');
      const stopButton = row.querySelector('.device-stop');
      if (startButton) startButton.disabled = isRunning && enabled;
      if (stopButton) stopButton.disabled = !enabled;
    }

    function updateDeviceRowStates() {
      deviceRows.querySelectorAll('.device-row').forEach(updateRowState);
    }

    function rowIndex(row) {
      return Array.from(deviceRows.querySelectorAll('.device-row')).indexOf(row);
    }

    function collectDeviceRow(row) {
      return {
        name: row.querySelector('.device-name').value.trim(),
        target: row.querySelector('.device-target').value.trim(),
        enabled: row.dataset.enabled !== 'false'
      };
    }

    function createDeviceRow(device) {
      const row = document.createElement('div');
      row.className = 'device-row';
      row.dataset.enabled = device?.enabled === false ? 'false' : 'true';

      const nameInput = document.createElement('input');
      nameInput.type = 'text';
      nameInput.className = 'device-name';
      nameInput.placeholder = 'Name';
      nameInput.autocomplete = 'off';
      nameInput.value = device?.name || '';

      const targetInput = document.createElement('input');
      targetInput.type = 'text';
      targetInput.className = 'device-target';
      targetInput.placeholder = 'IP:port';
      targetInput.autocomplete = 'off';
      targetInput.value = device?.target || '';

      const startDeviceBtn = document.createElement('button');
      startDeviceBtn.type = 'button';
      startDeviceBtn.className = 'device-start device-action';
      startDeviceBtn.textContent = 'Start';
      startDeviceBtn.addEventListener('click', () => {
        const device = collectDeviceRow(row);
        if (!device.target) {
          setMessage('ADB target is required.');
          targetInput.focus();
          return;
        }
        row.dataset.enabled = 'true';
        updateRowState(row);
        deviceRowsDirty = true;
        postJson('/api/device/start', {
          adb_devices: collectDevices(),
          index: rowIndex(row),
          target: device.target,
          interval: clampInterval(intervalInput.value)
        });
      });

      const stopDeviceBtn = document.createElement('button');
      stopDeviceBtn.type = 'button';
      stopDeviceBtn.className = 'device-stop device-action';
      stopDeviceBtn.textContent = 'Stop';
      stopDeviceBtn.addEventListener('click', () => {
        const device = collectDeviceRow(row);
        if (!device.target) {
          setMessage('ADB target is required.');
          targetInput.focus();
          return;
        }
        row.dataset.enabled = 'false';
        updateRowState(row);
        deviceRowsDirty = true;
        postJson('/api/device/stop', {
          adb_devices: collectDevices(),
          index: rowIndex(row),
          target: device.target
        });
      });

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'device-remove';
      removeBtn.textContent = 'X';
      removeBtn.addEventListener('click', () => {
        deviceRowsDirty = true;
        row.remove();
        if (!deviceRows.children.length) addDeviceRow();
      });

      row.append(nameInput, targetInput, startDeviceBtn, stopDeviceBtn, removeBtn);
      row.addEventListener('input', () => { deviceRowsDirty = true; });
      updateRowState(row);
      return row;
    }

    function addDeviceRow(device, options = {}) {
      const row = createDeviceRow(device || {});
      deviceRows.appendChild(row);
      if (options.markDirty) {
        deviceRowsDirty = true;
      }
      if (options.focus) {
        row.querySelector('.device-name').focus();
      }
    }
    function parseLegacyDevices(text) {
      return String(text || '').split('\\n').map((line) => {
        const trimmed = line.trim();
        if (!trimmed) return null;
        if (trimmed.includes('=')) {
          const [name, ...targetParts] = trimmed.split('=');
          return { name: name.trim(), target: targetParts.join('=').trim(), enabled: true };
        }
        return { name: '', target: trimmed, enabled: true };
      }).filter((device) => device && device.target);
    }

    function setDeviceRows(devices) {
      const nextDevices = Array.isArray(devices) && devices.length ? devices : [{}];
      deviceRows.replaceChildren();
      nextDevices.forEach(addDeviceRow);
      deviceRowsSynced = true;
      deviceRowsDirty = false;
    }

    function collectDevices() {
      return Array.from(deviceRows.querySelectorAll('.device-row')).map(collectDeviceRow).filter((device) => device.target);
    }
    function allDevicesEnabled() {
      const devices = collectDevices();
      return devices.length > 0 && devices.every((device) => device.enabled);
    }

    intervalRange.addEventListener('input', () => setIntervalValue(intervalRange.value));
    intervalInput.addEventListener('input', () => setIntervalValue(intervalInput.value));
    addDeviceBtn.addEventListener('click', () => addDeviceRow({}, { focus: true, markDirty: true }));

    function setMessage(text) {
      messageEl.textContent = text || '';
    }

    function renderStatus(data, options = {}) {
      const running = Boolean(data.running);
      isRunning = running;
      statusEl.classList.toggle('running', running);
      statusEl.querySelector('span:last-child').textContent = running ? 'Running' : 'Stopped';
      startBtn.disabled = running && allDevicesEnabled();
      stopBtn.disabled = !running;
      addDeviceBtn.disabled = false;
      deviceRows.querySelectorAll('input, .device-remove').forEach((element) => { element.disabled = false; });
      updateDeviceRowStates();
      intervalRange.disabled = running;
      intervalInput.disabled = running;

      if (options.syncDevices || !deviceRowsSynced || (!deviceRowsDirty && !deviceRows.contains(document.activeElement))) {
        const devices = Array.isArray(data.adb_devices) ? data.adb_devices : parseLegacyDevices(data.adb_target);
        setDeviceRows(devices);
        updateDeviceRowStates();
      }

      startBtn.disabled = isRunning && allDevicesEnabled();

      if (running && data.interval) {
        setIntervalValue(data.interval);
      }

      const logs = data.logs || [];
      logsEl.textContent = logs.length ? logs.join('\\n') : 'No logs yet.';
      logsEl.scrollTop = logsEl.scrollHeight;
    }

    async function fetchStatus() {
      try {
        const response = await fetch('/api/status');
        renderStatus(await response.json());
      } catch (error) {
        setMessage('Unable to reach Flask server.');
      }
    }

    async function postJson(url, body) {
      setMessage('');
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
      });
      const data = await response.json();
      if (!response.ok) setMessage(data.error || 'Request failed.');
      renderStatus(data, { syncDevices: response.ok });
    }

    startBtn.addEventListener('click', () => {
      deviceRows.querySelectorAll('.device-row').forEach((row) => {
        row.dataset.enabled = 'true';
        updateRowState(row);
      });
      deviceRowsDirty = true;
      postJson('/api/start', {
        adb_devices: collectDevices(),
        interval: clampInterval(intervalInput.value)
      });
    });

    stopBtn.addEventListener('click', () => {
      deviceRows.querySelectorAll('.device-row').forEach((row) => {
        row.dataset.enabled = 'false';
        updateRowState(row);
      });
      deviceRowsDirty = true;
      postJson('/api/devices/enabled', { adb_devices: collectDevices(), enabled: false });
    });

    setDeviceRows(parseLegacyDevices({{ adb_targets|tojson }}));
    setIntervalValue(intervalInput.value);
    fetchStatus();
    setInterval(fetchStatus, 2000);
  </script>
</body>
</html>
"""


@app.get("/")
def index():
    state = runner.status()
    return render_template_string(
        PAGE,
        adb_targets=state["adb_target"],
        interval=state["interval"],
    )


@app.get("/api/status")
def status():
    return jsonify(runner.status())


@app.post("/api/start")
def start():
    data = request.get_json(silent=True) or {}
    try:
        runner.start(
            adb_target=data.get("adb_target", DEFAULT_ADB_TARGET),
            adb_targets=data.get("adb_devices", data.get("adb_targets")),
            swipe_interval=data.get("interval", DEFAULT_SWIPE_INTERVAL),
        )
    except ValueError as error:
        response = runner.status()
        response["error"] = str(error)
        return jsonify(response), 400

    return jsonify(runner.status())


@app.post("/api/connect")
def connect():
    data = request.get_json(silent=True) or {}
    try:
        runner.connect(adb_target=data.get("adb_target", DEFAULT_ADB_TARGET), adb_targets=data.get("adb_devices", data.get("adb_targets")))
    except ValueError as error:
        response = runner.status()
        response["error"] = str(error)
        return jsonify(response), 400
    except FileNotFoundError:
        response = runner.status()
        response["error"] = "ADB command not found. Install Android platform-tools, add adb.exe to PATH, or place it in platform-tools\\adb.exe."
        return jsonify(response), 500
    except Exception as error:
        response = runner.status()
        response["error"] = str(error)
        return jsonify(response), 500

    return jsonify(runner.status())


@app.post("/api/device/start")
def start_device():
    data = request.get_json(silent=True) or {}
    try:
        runner.start_device(
            data.get("adb_devices", data.get("adb_targets")),
            index=data.get("index"),
            target=data.get("target"),
            swipe_interval=data.get("interval", DEFAULT_SWIPE_INTERVAL),
        )
    except ValueError as error:
        response = runner.status()
        response["error"] = str(error)
        return jsonify(response), 400
    except FileNotFoundError:
        response = runner.status()
        response["error"] = "ADB command not found. Install Android platform-tools, add adb.exe to PATH, or place it in platform-tools\\adb.exe."
        return jsonify(response), 500
    except Exception as error:
        response = runner.status()
        response["error"] = str(error)
        return jsonify(response), 500

    return jsonify(runner.status())
@app.post("/api/device/connect")
def connect_device():
    data = request.get_json(silent=True) or {}
    try:
        runner.connect_device(
            data.get("device"),
            adb_targets=data.get("adb_devices", data.get("adb_targets")),
        )
    except ValueError as error:
        response = runner.status()
        response["error"] = str(error)
        return jsonify(response), 400
    except FileNotFoundError:
        response = runner.status()
        response["error"] = "ADB command not found. Install Android platform-tools, add adb.exe to PATH, or place it in platform-tools\\adb.exe."
        return jsonify(response), 500
    except Exception as error:
        response = runner.status()
        response["error"] = str(error)
        return jsonify(response), 500

    return jsonify(runner.status())


@app.post("/api/device/stop")
def stop_device():
    data = request.get_json(silent=True) or {}
    try:
        runner.set_device_enabled(
            data.get("adb_devices", data.get("adb_targets")),
            index=data.get("index"),
            target=data.get("target"),
            enabled=False,
        )
    except ValueError as error:
        response = runner.status()
        response["error"] = str(error)
        return jsonify(response), 400

    return jsonify(runner.status())


@app.post("/api/devices/enabled")
def set_devices_enabled():
    data = request.get_json(silent=True) or {}
    try:
        runner.set_all_devices_enabled(
            data.get("adb_devices", data.get("adb_targets")),
            enabled=bool(data.get("enabled")),
        )
    except ValueError as error:
        response = runner.status()
        response["error"] = str(error)
        return jsonify(response), 400

    return jsonify(runner.status())


@app.post("/api/stop")
def stop():
    runner.stop()
    return jsonify(runner.status())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, threaded=True)

