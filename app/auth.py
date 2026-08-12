import pickle
import time
from pathlib import Path
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.config import settings

COOKIES_FILE = Path(settings.COOKIES_FILE or "cookies.pkl")
LOGIN_URL = f"{settings.BASE_URL}/account/login"
TIMEOUT = 30


def is_logged_in(driver: WebDriver) -> bool:
    driver.get(settings.BASE_URL)
    try:
        WebDriverWait(driver, 5).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass
    return not driver.find_elements(By.CSS_SELECTOR, '[data-qa="login"], input[name="login"]')


def load_cookies(driver: WebDriver) -> bool:
    if not COOKIES_FILE.exists():
        return False
    driver.get(settings.BASE_URL)
    host = urlparse(driver.current_url).netloc
    with open(COOKIES_FILE, "rb") as f:
        cookies = pickle.load(f)
    for cookie in cookies:
        cookie["domain"] = host
        driver.add_cookie(cookie)
    return bool(cookies)


def save_cookies(driver: WebDriver) -> None:
    with open(COOKIES_FILE, "wb") as f:
        pickle.dump(driver.get_cookies(), f)


def _click_first_step(driver: WebDriver) -> None:
    driver.get(LOGIN_URL)
    submit = WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-qa="submit-button"]'))
    )
    submit.click()


def _select_email_tab(driver: WebDriver) -> None:
    email_tab = WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[data-qa="credential-type-email"]'))
    )
    driver.execute_script("arguments[0].click();", email_tab)


def _enter_email(driver: WebDriver) -> None:
    email_input = WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="login"][data-qa="applicant-login-input-email"]'))
    )
    email_input.send_keys(settings.HH_EMAIL)

    next_button = WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, '//button[.//span[text()="Дальше"]]'))
    )
    next_button.click()


def _enter_otp(driver: WebDriver) -> None:
    otp_input = WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-qa="magritte-pincode-input-field"]'))
    )
    code = input("Введите 4-значный код из письма/СМС: ").strip()
    otp_input.send_keys(code)


def _wait_manual_login(driver: WebDriver) -> None:
    print("Если появилась капча или требуется подтверждение — завершите вход в открытом браузере вручную.")
    deadline = time.time() + 180
    while time.time() < deadline:
        if is_logged_in(driver):
            return
        time.sleep(2)
    raise TimeoutError("Вход в hh.ru не завершён за отведённое время.")


def ensure_logged_in(driver: WebDriver) -> None:
    if load_cookies(driver) and is_logged_in(driver):
        print("Вход выполнен по сохранённым куки.")
        return

    if settings.HH_EMAIL:
        _click_first_step(driver)
        _select_email_tab(driver)
        _enter_email(driver)
        _enter_otp(driver)

    if not is_logged_in(driver):
        _wait_manual_login(driver)
    save_cookies(driver)
    print("Вход выполнен, куки сохранены.")
