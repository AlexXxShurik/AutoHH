from dotenv import load_dotenv
from os import getenv

load_dotenv()


class Settings:
    BASE_URL: str = getenv("BASE_URL", "https://hh.ru")
    HEADLESS: bool = getenv("HEADLESS", "true").lower() == "true"
    HH_EMAIL: str | None = getenv("HH_EMAIL")
    COOKIES_FILE: str | None = getenv("COOKIES_FILE", "cookies.pkl")
    CRON: str = getenv("CRON", "0 * * * *")
    TZ: str = getenv("TZ", "Asia/Almaty")
    INPUT_SERVER_URL: str | None = getenv("INPUT_SERVER_URL")


settings = Settings()
