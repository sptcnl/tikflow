from flask import Flask, jsonify, render_template_string, request

from tikflow import DEFAULT_ADB_TARGET, DEFAULT_ADB_TARGETS, DEFAULT_SWIPE_INTERVAL, TikFlow


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
      grid-template-columns: 1fr 180px;
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

    textarea, input[type="number"] {
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

    textarea {
      min-height: 92px;
      resize: vertical;
      line-height: 1.4;
      padding-top: 10px;
      padding-bottom: 10px;
    }

    textarea:focus, input:focus { border-color: #5b6474; }

    .interval-row {
      display: grid;
      grid-template-columns: 1fr 88px;
      gap: 12px;
      align-items: center;
    }

    input[type="range"] { width: 100%; }

    .actions {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 10px;
    }

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

    #startBtn { background: var(--accent); }
    #connectBtn { background: var(--warning); }
    #stopBtn { background: var(--danger); color: #fff; }

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
      .actions { grid-template-columns: 1fr; }
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
        <div>
          <label for="adbTargets">ADB targets</label>
          <textarea id="adbTargets" autocomplete="off" spellcheck="false">{{ adb_targets }}</textarea>
        </div>
        <div class="actions">
          <button id="startBtn" type="button">Start</button>
          <button id="connectBtn" type="button">Reconnect</button>
          <button id="stopBtn" type="button">Stop</button>
        </div>
        <div>
          <label for="intervalRange">Interval: <span id="intervalLabel">{{ interval }}</span>s</label>
          <div class="interval-row">
            <input id="intervalRange" type="range" min="5" max="60" value="{{ interval }}">
            <input id="intervalInput" type="number" min="5" max="60" value="{{ interval }}">
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
    const adbTargets = document.getElementById('adbTargets');
    const intervalRange = document.getElementById('intervalRange');
    const intervalInput = document.getElementById('intervalInput');
    const intervalLabel = document.getElementById('intervalLabel');
    const startBtn = document.getElementById('startBtn');
    const connectBtn = document.getElementById('connectBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusEl = document.getElementById('status');
    const messageEl = document.getElementById('message');
    const logsEl = document.getElementById('logs');

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

    intervalRange.addEventListener('input', () => setIntervalValue(intervalRange.value));
    intervalInput.addEventListener('input', () => setIntervalValue(intervalInput.value));

    function setMessage(text) {
      messageEl.textContent = text || '';
    }

    function renderStatus(data) {
      const running = Boolean(data.running);
      statusEl.classList.toggle('running', running);
      statusEl.querySelector('span:last-child').textContent = running ? 'Running' : 'Stopped';
      startBtn.disabled = running;
      connectBtn.disabled = false;
      stopBtn.disabled = !running;
      adbTargets.disabled = false;
      intervalRange.disabled = running;
      intervalInput.disabled = running;

      const targetText = Array.isArray(data.adb_targets) ? data.adb_targets.join('\\n') : data.adb_target;
      if (targetText && document.activeElement !== adbTargets) adbTargets.value = targetText;

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
      renderStatus(data);
    }

    startBtn.addEventListener('click', () => {
      postJson('/api/start', {
        adb_targets: adbTargets.value,
        interval: clampInterval(intervalInput.value)
      });
    });

    connectBtn.addEventListener('click', () => {
      postJson('/api/connect', { adb_targets: adbTargets.value });
    });

    stopBtn.addEventListener('click', () => postJson('/api/stop'));

    setIntervalValue(intervalInput.value);
    fetchStatus();
    setInterval(fetchStatus, 2000);
  </script>
</body>
</html>
"""


@app.get("/")
def index():
    return render_template_string(
        PAGE,
        adb_targets="\n".join(DEFAULT_ADB_TARGETS),
        interval=DEFAULT_SWIPE_INTERVAL,
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
            adb_targets=data.get("adb_targets"),
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
        runner.connect(adb_target=data.get("adb_target", DEFAULT_ADB_TARGET), adb_targets=data.get("adb_targets"))
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


@app.post("/api/stop")
def stop():
    runner.stop()
    return jsonify(runner.status())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, threaded=True)

