import pickle
import time
from pathlib import Path
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.config import settings

if settings.INPUT_SERVER_URL:
    from app.input_client import request_captcha, request_otp, request_password
else:
    from app.input_server import request_captcha, request_otp, request_password

COOKIES_FILE = Path(settings.COOKIES_FILE or "cookies.pkl")
LOGIN_URL = f"{settings.BASE_URL}/account/login"
LOG_DIR = Path("logs")
TIMEOUT = 30


def _dump(driver: WebDriver, tag: str) -> Path:
    """Сохраняет скриншот и HTML страницы для диагностики."""
    LOG_DIR.mkdir(exist_ok=True)
    driver.save_screenshot(LOG_DIR / f"{tag}.png")
    html = LOG_DIR / f"{tag}.html"
    with open(html, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print(f"[diagnostic] {tag}: url={driver.current_url}, сохранено {LOG_DIR}/{tag}.png и .html", flush=True)
    return html


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
    driver.delete_all_cookies()
    driver.get(settings.BASE_URL)
    host = urlparse(driver.current_url).netloc
    with open(COOKIES_FILE, "rb") as f:
        cookies = pickle.load(f)
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except Exception:
            fallback = dict(cookie)
            fallback["domain"] = host
            try:
                driver.add_cookie(fallback)
            except Exception:
                continue
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


def _enter_password(driver: WebDriver) -> None:
    """Ждёт поле пароля; если появилось — запрашивает и вводит пароль."""
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        if driver.find_elements(By.CSS_SELECTOR, 'input[name="password"]'):
            break
        if driver.find_elements(By.CSS_SELECTOR, 'input[data-qa="magritte-pincode-input-field"]'):
            return
        time.sleep(1)
    else:
        return

    password = request_password()
    driver.find_element(By.CSS_SELECTOR, 'input[name="password"]').send_keys(password)

    try:
        submit = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))
        )
    except Exception:
        submit = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[.//span[text()="Войти"]]'))
        )
    submit.click()


def _solve_captcha(driver: WebDriver) -> bool:
    """Решает капчу, если она есть. Возвращает True, если капчи больше нет."""
    for _ in range(5):
        img = driver.find_elements(By.CSS_SELECTOR, '[data-qa="account-captcha-picture"]')
        if not img:
            return True
        try:
            field = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa="account-captcha-input"]'))
            )
            png = img[0].screenshot_as_png
        except Exception:
            continue
        text = request_captcha(png)
        if not text:
            continue
        try:
            field.send_keys(text)
            field.send_keys(Keys.ENTER)
        except Exception:
            continue
        try:
            WebDriverWait(driver, 10).until(
                lambda d: not d.find_elements(By.CSS_SELECTOR, '[data-qa="account-captcha-picture"]')
                or d.find_elements(By.CSS_SELECTOR, '[data-qa="account-captcha-error"]')
            )
        except Exception:
            pass
    return not driver.find_elements(By.CSS_SELECTOR, '[data-qa="account-captcha-picture"]')


def _enter_otp(driver: WebDriver) -> None:
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        _solve_captcha(driver)
        fields = driver.find_elements(By.CSS_SELECTOR, 'input[data-qa="magritte-pincode-input-field"]')
        if fields:
            code = request_otp()
            fields[0].send_keys(code)
            return
        time.sleep(1)
    _dump(driver, "otp_timeout")
    raise TimeoutError("OTP-поле не появилось после входа.")


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
        driver.delete_all_cookies()
        _click_first_step(driver)
        _select_email_tab(driver)
        _enter_email(driver)
        _solve_captcha(driver)
        _enter_password(driver)
        _solve_captcha(driver)
        _enter_otp(driver)

    if not is_logged_in(driver):
        _wait_manual_login(driver)
    save_cookies(driver)
    print("Вход выполнен, куки сохранены.")
