from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.config import settings

TIMEOUT = 30


def raise_resume(driver: WebDriver) -> bool:
    """Поднимает резюме, если кнопка доступна. Возвращает True при успехе."""
    driver.get(settings.BASE_URL)
    try:
        button = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-qa="applicant-index-nba-action_update-resumes"]')
            )
        )
        button.click()
        return True
    except Exception:
        return False
