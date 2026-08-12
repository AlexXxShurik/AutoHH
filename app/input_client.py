import base64
import json
import time
import urllib.request

from app.config import settings

TIMEOUT = 180


def _base() -> str:
    return (settings.INPUT_SERVER_URL or "http://127.0.0.1:8765").rstrip("/")


def _post(path: str, payload: dict) -> None:
    req = urllib.request.Request(
        _base() + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=10)


def _get_state() -> dict:
    with urllib.request.urlopen(_base() + "/api/state", timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def request_value(mode: str, title: str, label: str, image: bytes | None = None) -> str:
    """Отправляет запрос на сервер ввода (на хосте) и ждёт значение."""
    payload = {
        "mode": mode,
        "title": title,
        "label": label,
        "image": base64.b64encode(image).decode() if image else None,
    }
    _post("/api/request", payload)
    print(f"{label}", flush=True)
    print(f"Страница {_base()}/ должна открыться в браузере автоматически.", flush=True)
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        state = _get_state()
        if state.get("mode") == "done":
            return state.get("value") or ""
        time.sleep(0.5)
    raise TimeoutError(f"Не получено значение за {TIMEOUT} секунд.")


def request_password() -> str:
    return request_value("password", "Вход в hh", "Введите пароль от аккаунта:")


def request_otp() -> str:
    return request_value("otp", "Вход в hh", "Введите 4-значный код из письма/СМС:")


def request_captcha(png: bytes) -> str:
    return request_value("captcha", "Подтвердите, что вы не робот", "Введите текст с картинки:", image=png)
