import time
from pathlib import Path
from urllib.parse import urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.config import settings
from app.vacancies import Vacancy

_APPLY_BUTTON_SELECTORS = [
    (By.CSS_SELECTOR, 'a[data-qa="vacancy-response-link-top"]'),
    (By.CSS_SELECTOR, 'button[data-qa="vacancy-response-button"]'),
    (By.XPATH, '//button[.//span[text()="Откликнуться"]]'),
    (By.XPATH, '//a[.//span[text()="Откликнуться"]]'),
]
_RELOCATION_CONFIRM = (By.CSS_SELECTOR, 'button[data-qa="relocation-warning-confirm"]')
_LETTER_INPUT = (By.CSS_SELECTOR, 'textarea[data-qa="vacancy-response-popup-form-letter-input"]')
_RESPONSE_CLOSE = (By.CSS_SELECTOR, 'button[data-qa="response-popup-close"]')
_RESPONDED_MARKERS = ("вы откликнулись", "отклик уже отправлен")
_CHAT_BUTTON = (By.CSS_SELECTOR, 'button[data-qa="vacancy-response-link-view-topic"]')
_CHAT_IFRAME = (By.CSS_SELECTOR, 'iframe.chatik-integration-iframe')
_ADD_COVER_LETTER = (By.CSS_SELECTOR, '[data-qa="chatik-chat-message-applicant-action"]')
_CHAT_MESSAGE_INPUT = (By.CSS_SELECTOR, 'textarea[data-qa="chatik-new-message-text"]')
_CHAT_SEND_BUTTON = (By.CSS_SELECTOR, 'button[data-qa="chatik-do-send-message"]')


def load_cover_letter() -> str:
    path = Path(settings.COVER_LETTER_FILE)
    if not path.exists():
        raise SystemExit(f"Файл сопроводительного письма {path} не найден")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit(f"Файл сопроводительного письма {path} пуст")
    return text


def _first_found(driver: WebDriver, locators: list[tuple], timeout: float = 10):
    for by, value in locators:
        try:
            return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
        except Exception:
            continue
    return None


def _click(element) -> None:
    try:
        element.click()
    except Exception:
        element.parent.execute_script("arguments[0].click();", element)


def _already_responded(driver: WebDriver) -> bool:
    elements = driver.find_elements(By.CSS_SELECTOR, "[data-qa]")
    for element in elements:
        try:
            text = element.text.strip().lower()
        except Exception:
            continue
        if text and any(marker in text for marker in _RESPONDED_MARKERS):
            return True
    return False


def _set_value_js(driver: WebDriver, element, value: str) -> None:
    """Надёжно выставляет значение React-управляемого textarea."""
    driver.execute_script(
        """
        const el = arguments[0];
        const value = arguments[1];
        const proto = Object.getPrototypeOf(el);
        const desc = Object.getOwnPropertyDescriptor(proto, 'value');
        desc.set.call(el, value);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        """,
        element,
        value,
    )


def _add_cover_letter_in_chat(driver: WebDriver, letter: str) -> str:
    """Добавляет сопроводительное письмо в чат с работодателем."""
    chat_btn = _first_found(driver, [_CHAT_BUTTON], timeout=10)
    if chat_btn is None:
        return "ошибка: кнопка «Чат» не найдена"
    _click(chat_btn)

    try:
        WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it(_CHAT_IFRAME))
    except Exception:
        return "ошибка: окно чата (iframe) не загрузилось"
    try:
        try:
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            return "ошибка: документ чата не загрузился"

        action = _first_found(driver, [_ADD_COVER_LETTER], timeout=15)
        if action is None:
            return "ошибка: действие «Добавить сопроводительное» не найдено"
        _click(action)

        textarea = _first_found(driver, [_CHAT_MESSAGE_INPUT], timeout=10)
        if textarea is None:
            return "ошибка: поле сообщения не найдено"

        _set_value_js(driver, textarea, letter)
        try:
            WebDriverWait(driver, 5).until(
                lambda d: textarea.get_attribute("value") == letter
            )
        except Exception:
            return "ошибка: не удалось вставить сопроводительное письмо"

        try:
            send = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(_CHAT_SEND_BUTTON))
        except Exception:
            return "ошибка: кнопка отправки не стала активной"
        _click(send)
        return "отклик отправлен, сопроводительное письмо добавлено в чат"
    finally:
        driver.switch_to.default_content()


def apply_to_vacancy(driver: WebDriver, vacancy: Vacancy, letter: str) -> str:
    driver.get(urljoin(settings.BASE_URL, vacancy.url))

    apply_btn = _first_found(driver, _APPLY_BUTTON_SELECTORS, timeout=15)
    if apply_btn is None:
        if _already_responded(driver):
            return _add_cover_letter_in_chat(driver, letter)
        return "ошибка: кнопка «Откликнуться» не найдена"

    _click(apply_btn)

    confirm = _first_found(driver, [_RELOCATION_CONFIRM], timeout=5)
    if confirm is not None:
        _click(confirm)

    textarea = _first_found(driver, [_LETTER_INPUT], timeout=8)
    if textarea is not None:
        close = _first_found(driver, [_RESPONSE_CLOSE], timeout=3)
        if close is not None:
            _click(close)
        return "пропущено: нужна форма с сопроводительным письмом"

    return _add_cover_letter_in_chat(driver, letter)


def apply_to_all(driver: WebDriver, vacancies: list[Vacancy], letter: str) -> None:
    total = len(vacancies)
    for i, vacancy in enumerate(vacancies, 1):
        try:
            result = apply_to_vacancy(driver, vacancy, letter)
        except Exception as exc:
            result = f"ошибка: {exc}"
        print(f"[{i}/{total}] #{vacancy.id} {vacancy.title}: {result}", flush=True)
        if i < total and settings.RESPONSE_DELAY:
            time.sleep(settings.RESPONSE_DELAY)