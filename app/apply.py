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
    (By.CSS_SELECTOR, 'button[data-qa="vacancy-response-button"]'),
    (By.XPATH, '//button[.//span[text()="Откликнуться"]]'),
]
_RELOCATION_CONFIRM = (By.CSS_SELECTOR, 'button[data-qa="relocation-warning-confirm"]')
_LETTER_INPUT = (By.CSS_SELECTOR, 'textarea[data-qa="vacancy-response-popup-form-letter-input"]')
_SUBMIT_BUTTON = (By.CSS_SELECTOR, 'button[data-qa="vacancy-response-submit-popup"]')
_RESPONDED_MARKERS = ("вы откликнулись", "отклик уже отправлен")


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
    page = driver.page_source.lower()
    return any(marker in page for marker in _RESPONDED_MARKERS)


def apply_to_vacancy(driver: WebDriver, vacancy: Vacancy, letter: str) -> str:
    driver.get(urljoin(settings.BASE_URL, vacancy.url))

    apply_btn = _first_found(driver, _APPLY_BUTTON_SELECTORS, timeout=15)
    if apply_btn is None:
        if _already_responded(driver):
            return "пропущено: отклик уже отправлен"
        return "ошибка: кнопка «Откликнуться» не найдена"

    _click(apply_btn)

    confirm = _first_found(driver, [_RELOCATION_CONFIRM], timeout=5)
    if confirm is not None:
        _click(confirm)

    textarea = _first_found(driver, [_LETTER_INPUT], timeout=15)
    if textarea is None:
        submit = _first_found(driver, [_SUBMIT_BUTTON], timeout=5)
        if submit is not None:
            _click(submit)
            return "отклик отправлен (без сопроводительного письма)"
        return "ошибка: форма отклика не найдена"

    textarea.send_keys(letter)
    try:
        submit = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(_SUBMIT_BUTTON))
    except Exception:
        return "ошибка: кнопка отправки не стала активной"
    _click(submit)
    return "отклик отправлен"


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