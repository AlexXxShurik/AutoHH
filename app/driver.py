import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from app.config import settings


def create_driver() -> webdriver.Chrome:
    options = Options()
    if settings.HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver_path = os.getenv("CHROMEDRIVER_PATH")
    service = Service(driver_path) if driver_path else Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_window_size(1366, 900)
    return driver
