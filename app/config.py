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
    RESUME_ID: str | None = getenv("RESUME_ID")
    BLOCKED_WORDS_FILE: str = getenv("BLOCKED_WORDS_FILE", "blocked_words.txt")
    COVER_LETTER_FILE: str = getenv("COVER_LETTER_FILE", "cover_letter.txt")
    RESPONSE_DELAY: float = float(getenv("RESPONSE_DELAY", "5"))

    @property
    def resume_search_url(self) -> str:
        return (
            f"{self.BASE_URL}/search/vacancy?resume={self.RESUME_ID}"
            "&hhtmFromLabel=tab_byResume&hhtmFrom=main"
        )


settings = Settings()
