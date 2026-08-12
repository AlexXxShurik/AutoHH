import base64
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

HOST = os.getenv("INPUT_SERVER_HOST", "127.0.0.1")
PORT = 8765
TIMEOUT = 180

PAGE_HTML = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>AutoHH</title>
<style>
  body { font-family: system-ui, sans-serif; display: flex; align-items: center;
         justify-content: center; height: 100vh; margin: 0; background: #f5f6f8; }
  .card { background: #fff; padding: 40px; border-radius: 12px;
          box-shadow: 0 4px 20px rgba(0,0,0,.08); text-align: center; min-width: 320px; }
  h2 { margin-top: 0; color: #333; }
  img { border: 1px solid #ddd; border-radius: 8px; margin: 16px 0; }
  input { font-size: 24px; padding: 10px 16px; width: 280px; text-align: center;
          border: 1px solid #ccc; border-radius: 8px; margin: 12px 0; }
  button { font-size: 16px; padding: 10px 28px; border: none; border-radius: 8px;
           background: #2d7dd2; color: #fff; cursor: pointer; }
  button:hover { background: #266ab5; }
  .badge { width: 64px; height: 64px; margin: 0 auto 20px; border-radius: 50%;
           display: flex; align-items: center; justify-content: center;
           background: #e8f5ee; color: #1e9e5a; font-size: 34px; }
  .muted { color: #777; font-size: 14px; }
</style>
</head>
<body>
<div class="card" id="card"><h2>Ожидание...</h2></div>
<script>
let currentKey = null;

function render(s) {
  if (s.mode === 'password') {
    return `<h2>${s.title}</h2>
            <div><label>${s.label}</label></div>
            <form onsubmit="submitValue(event)">
              <input type="password" name="value" autofocus>
              <div><button type="submit">Отправить</button></div>
            </form>`;
  }
  if (s.mode === 'otp') {
    return `<h2>${s.title}</h2>
            <div><label>${s.label}</label></div>
            <form onsubmit="submitValue(event)">
              <input type="text" name="value" maxlength="4" inputmode="numeric" autofocus>
              <div><button type="submit">Отправить</button></div>
            </form>`;
  }
  if (s.mode === 'captcha') {
    return `<h2>${s.title}</h2>
            <img src="${s.image}" alt="captcha">
            <div><label>${s.label}</label></div>
            <form onsubmit="submitValue(event)">
              <input type="text" name="value" autocomplete="off" autofocus>
              <div><button type="submit">Отправить</button></div>
            </form>`;
  }
  if (s.mode === 'done') {
    return `<div class="badge">&#10003;</div>
            <h2>Спасибо!</h2>
            <p class="muted">Значение отправлено, страницу можно закрыть.</p>`;
  }
  return `<h2>${s.title || 'AutoHH'}</h2><p class="muted">Ожидание ввода...</p>`;
}

async function refresh() {
  const r = await fetch('/api/state');
  const s = await r.json();
  const key = `${s.mode}|${s.title}|${s.label}|${s.image || ''}`;
  const card = document.getElementById('card');
  if (key === currentKey) return;
  currentKey = key;
  const prevInput = card.querySelector('input[name="value"]');
  const prevValue = prevInput ? prevInput.value : '';
  card.innerHTML = render(s);
  const input = card.querySelector('input[name="value"]');
  if (input && prevValue) input.value = prevValue;
}

async function submitValue(ev) {
  ev.preventDefault();
  const input = ev.target.querySelector('input');
  const form = new URLSearchParams();
  form.append('value', input.value);
  await fetch('/submit', { method: 'POST', body: form });
}
setInterval(refresh, 400);
refresh();
</script>
</body>
</html>"""


class InputServer(HTTPServer):
    def __init__(self, server_address):
        super().__init__(server_address, Handler)
        self._state = {"mode": "idle", "title": "AutoHH", "label": "", "image": None}
        self._result: str | None = None
        self._event = threading.Event()
        self.page_opened = False

    def set_request(self, mode: str, title: str, label: str, image: bytes | None = None) -> None:
        self._state = {"mode": mode, "title": title, "label": label, "image": image}
        self._result = None
        self._event.clear()

    def resolve(self, value: str) -> None:
        self._result = value
        self._state["mode"] = "done"
        self._event.set()

    def state_json(self) -> str:
        image = None
        if self._state.get("image"):
            image = "data:image/png;base64," + base64.b64encode(self._state["image"]).decode()
        return json.dumps({
            "mode": self._state["mode"],
            "title": self._state["title"],
            "label": self._state["label"],
            "image": image,
            "value": self._result,
        }, ensure_ascii=False)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/api/state":
            data = self.server.state_json().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(PAGE_HTML.encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        if self.path == "/api/request":
            payload = json.loads(body.decode("utf-8"))
            image = None
            if payload.get("image"):
                image = base64.b64decode(payload["image"])
            self.server.set_request(
                payload.get("mode", "idle"),
                payload.get("title", "AutoHH"),
                payload.get("label", ""),
                image,
            )
            try:
                webbrowser.open(f"http://localhost:{PORT}/")
            except Exception:
                pass
            self.send_response(200)
            self.end_headers()
            return
        if self.path == "/submit":
            data = parse_qs(body.decode("utf-8"))
            value = data.get("value", [""])[0].strip()
            if value:
                self.server.resolve(value)
            self.send_response(200)
            self.end_headers()
            return
        self.send_error(404)


_server: InputServer | None = None
_lock = threading.Lock()


def _get_server() -> InputServer:
    global _server
    with _lock:
        if _server is None:
            _server = InputServer((HOST, PORT))
            threading.Thread(target=_server.serve_forever, daemon=True).start()
    return _server


def request_value(mode: str, title: str, label: str, image: bytes | None = None) -> str:
    """Показывает на localhost форму для ввода и ждёт значение от пользователя."""
    server = _get_server()
    with _lock:
        server.set_request(mode, title, label, image)
        if not server.page_opened:
            try:
                webbrowser.open(f"http://localhost:{PORT}/")
            except Exception:
                pass
            server.page_opened = True
    url = f"http://localhost:{PORT}/"
    print(f"{label}", flush=True)
    print(f"Откройте страницу {url} в браузере и введите значение. Если она не открылась сама — откройте вручную.", flush=True)
    if not server._event.wait(timeout=TIMEOUT):
        raise TimeoutError(f"Не получено значение за {TIMEOUT} секунд.")
    return server._result or ""


def request_password() -> str:
    return request_value("password", "Вход в hh", "Введите пароль от аккаунта:")


def request_otp() -> str:
    return request_value("otp", "Вход в hh", "Введите 4-значный код из письма/СМС:")


def request_captcha(png: bytes) -> str:
    return request_value("captcha", "Подтвердите, что вы не робот", "Введите текст с картинки:", image=png)


def run_server() -> None:
    """Запуск сервера на хосте (например: python -m app.input_server)."""
    host = os.getenv("INPUT_SERVER_HOST", "0.0.0.0")
    print(f"Сервер ввода запущен на http://localhost:{PORT}/ (ждите запросы).", flush=True)
    server = InputServer((host, PORT))
    server.serve_forever()


if __name__ == "__main__":
    run_server()
