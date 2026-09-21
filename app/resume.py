from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.config import settings

TIMEOUT = 30

MY_RESUMES_URL = f"{settings.BASE_URL}/applicant/my_resumes?hhtmFrom=applicant_profile"


def raise_resume(driver: WebDriver) -> int:
    """Поднимает все доступные резюме на странице my_resumes.

    Возвращает количество успешно поднятых резюме.
    """
    driver.get(MY_RESUMES_URL)

    buttons = WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, '[data-qa="resume-update-button_actions"]')
        )
    )

    raised = 0
    for btn in buttons:
        if btn.is_enabled():
            btn.click()
            raised += 1

    return raised
