"""
app.py - one-file website for your Personal AI Assistant.

- Your original dream.py is NOT modified.
- No templates folder needed: the web page is inside this file.
- It finds dream.py by itself (next to this file, or in Downloads,
  Desktop or Documents).

Run:  python app.py   (the browser opens automatically)
"""

import importlib.util
import os
import sys
import threading
import webbrowser

from flask import Flask, Response, jsonify, request

MODULE_FILE = "dream.py"  # name of your original file


def find_original():
    here = os.path.dirname(os.path.abspath(__file__))
    home = os.path.expanduser("~")
    roots = [here] + [os.path.join(home, d) for d in ("Downloads", "Desktop", "Documents")]
    skip = {"venv", ".venv", "site-packages", "node_modules", "__pycache__", ".git"}
    for root in roots:
        if not os.path.isdir(root):
            continue
        base_depth = root.rstrip(os.sep).count(os.sep)
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
            if dirpath.count(os.sep) - base_depth >= 3:
                dirs[:] = []
            if MODULE_FILE in files:
                return os.path.join(dirpath, MODULE_FILE)
    return None


path = find_original()
if path is None:
    sys.exit(f"Could not find {MODULE_FILE}. Put it in the same folder as app.py.")

sys.path.insert(0, os.path.dirname(path))
spec = importlib.util.spec_from_file_location("dream", path)
dream = importlib.util.module_from_spec(spec)
sys.modules["dream"] = dream
spec.loader.exec_module(dream)
AssistantCore = dream.AssistantCore
print(f"Using your assistant code from: {path}")

app = Flask(__name__)
core = AssistantCore(user_name="User")  # same default as your GUI

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Personal AI Assistant</title>
<style>
  :root { --bg:#1e1e2e; --panel:#181825; --text:#cdd6f4; --muted:#a6adc8; --user:#89b4fa; --bot:#a6e3a1; --sys:#f9e2af; --line:#313244; }
  * { box-sizing:border-box; }
  html,body { height:100%; margin:0; }
  body { background:var(--bg); color:var(--text); font-family:"Segoe UI",system-ui,sans-serif; display:flex; justify-content:center; }
  .app { width:100%; max-width:640px; height:100%; display:flex; flex-direction:column; padding:12px; }
  h1 { font-size:1.3rem; text-align:center; margin:8px 0 12px; }
  #chat { flex:1; overflow-y:auto; background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px; }
  .msg { margin:0 0 10px; line-height:1.5; white-space:pre-wrap; overflow-wrap:anywhere; }
  .user { color:var(--user); } .assistant { color:var(--bot); } .system { color:var(--sys); }
  form { display:flex; gap:8px; margin-top:10px; }
  input { flex:1; min-width:0; padding:12px; font-size:1rem; border-radius:8px; border:1px solid var(--line); background:var(--panel); color:var(--text); }
  button { padding:0 16px; font-size:1rem; border-radius:8px; border:0; background:var(--user); color:#11111b; cursor:pointer; }
  button#mic { background:var(--line); color:var(--text); }
  button#mic.on { background:#f38ba8; color:#11111b; }
  button:disabled { opacity:.4; cursor:not-allowed; }
  :focus-visible { outline:2px solid var(--sys); outline-offset:2px; }
  #status { text-align:center; font-size:.8rem; color:var(--muted); margin:8px 0 0; }
</style>
</head>
<body>
<div class="app">
  <h1>Personal AI Assistant</h1>
  <div id="chat" role="log" aria-live="polite"></div>
  <form id="form">
    <input id="input" autocomplete="off" placeholder="Type a command, e.g. what is python" aria-label="Command">
    <button type="submit">Send</button>
    <button type="button" id="mic">Mic</button>
  </form>
  <p id="status"></p>
</div>
<script>
const chat = document.getElementById("chat");
const input = document.getElementById("input");
const micBtn = document.getElementById("mic");
const statusEl = document.getElementById("status");

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const canSpeak = "speechSynthesis" in window;
if (!SR) micBtn.disabled = true;
const idle = SR && canSpeak ? "Voice and text available"
  : canSpeak ? "Voice output only (mic not supported in this browser)"
  : "Text-only mode";
statusEl.textContent = idle;

function log(text, cls, prefix) {
  const p = document.createElement("p");
  p.className = "msg " + cls;
  p.textContent = (prefix || "") + text;
  chat.appendChild(p);
  chat.scrollTop = chat.scrollHeight;
}

function speak(text) {
  if (!canSpeak) return;
  speechSynthesis.cancel();
  speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}

async function respond(text) {
  log(text, "user", "You: ");
  let reply;
  try {
    const r = await fetch("/api/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: text })
    });
    reply = (await r.json()).reply;
  } catch (e) {
    log("Can't reach the Python server. Make sure app.py is running.", "system");
    return;
  }
  if (reply === "__EXIT__") reply = "Goodbye! Refresh the page to start again.";
  log(reply, "assistant", "Assistant: ");
  speak(reply);
}

document.getElementById("form").addEventListener("submit", e => {
  e.preventDefault();
  const v = input.value.trim();
  if (!v) return;
  input.value = "";
  respond(v);
});

if (SR) {
  const rec = new SR();
  rec.lang = "en-US";
  rec.onstart = () => { micBtn.classList.add("on"); statusEl.textContent = "Listening..."; };
  rec.onend = () => { micBtn.classList.remove("on"); statusEl.textContent = idle; };
  rec.onresult = e => respond(e.results[0][0].transcript);
  rec.onerror = e => log(e.error === "not-allowed" ? "Microphone permission was blocked." : "I didn't catch that.", "system");
  micBtn.addEventListener("click", () => { try { rec.start(); } catch (e) {} });
}

log("Assistant ready. Type a command below or tap Mic.", "system");
</script>
</body>
</html>
"""


@app.route("/")
def home():
    return Response(PAGE, mimetype="text/html")


@app.post("/api/command")
def command():
    data = request.get_json(silent=True) or {}
    return jsonify(reply=core.process(data.get("command", "")))


if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host="127.0.0.1", port=5000, debug=False)