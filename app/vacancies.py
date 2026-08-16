import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver

from app.config import settings

MAX_PAGES = 50

_CURRENCIES = {"RUB", "USD", "EUR", "BYN", "KZT", "UZS"}


@dataclass
class Vacancy:
    id: str | None
    title: str
    url: str
    salary: str | None
    employer: str | None
    address: str | None
    experience: str | None
    remote: bool
    skills_percent: str | None
    no_resume: bool

    def __str__(self) -> str:
        parts = [f"#{self.id}", self.title]
        if self.salary:
            parts.append(f"[{self.salary}]")
        if self.employer:
            parts.append(f"@ {self.employer}")
        if self.address:
            parts.append(f"({self.address})")
        tags = []
        if self.experience:
            tags.append(self.experience)
        if self.remote:
            tags.append("удалённо")
        if self.skills_percent:
            tags.append(self.skills_percent)
        if self.no_resume:
            tags.append("без резюме")
        if tags:
            parts.append("| " + ", ".join(tags))
        parts.append(self.url)
        return " ".join(parts)


def _salary_text(card) -> str | None:
    first = card.find("data", attrs={"value": True})
    if not first:
        return None
    node = first
    while node.parent is not None and node is not card:
        node = node.parent
        if node.name == "span":
            return node.get_text(" ", strip=True)
    return None


def parse_card(card) -> Vacancy | None:
    title_a = card.select_one('a[data-qa="serp-item__title"]')
    if not title_a:
        return None
    title = title_a.get_text(" ", strip=True)
    url = title_a.get("href", "")
    match = re.search(r"/vacancy/(\d+)", url)
    vid = match.group(1) if match else None

    employer_el = card.select_one('span[data-qa="vacancy-serp__vacancy-employer-text"]')
    address_el = card.select_one('span[data-qa="vacancy-serp__vacancy-address"]')
    experience_el = card.select_one('data[data-qa^="vacancy-serp__vacancy-work-experience"]')
    skills_el = card.select_one('[data-qa="vacancy-label-skillsPercentage"]')

    return Vacancy(
        id=vid,
        title=title,
        url=url,
        salary=_salary_text(card),
        employer=employer_el.get_text(" ", strip=True) if employer_el else None,
        address=address_el.get_text(" ", strip=True) if address_el else None,
        experience=experience_el.get_text(" ", strip=True) if experience_el else None,
        remote=bool(card.select_one('[data-qa="vacancy-label-work-schedule-remote"]')),
        skills_percent=skills_el.get_text(" ", strip=True) if skills_el else None,
        no_resume=bool(card.select_one('[data-qa="vacancy-label-no-resume"]')),
    )


def _load_blocked_words() -> list[str]:
    """Читает список запрещённых слов из файла. Пустые строки и комментарии (#) игнорируются."""
    path = Path(settings.BLOCKED_WORDS_FILE)
    if not path.exists():
        return []
    words = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        words.append(line.lower())
    return words


_BLOCKED_WORDS = _load_blocked_words()


def is_blocked(title: str) -> bool:
    """True, если в заголовке встречается хотя бы одно запрещённое слово."""
    lowered = title.lower()
    return any(word in lowered for word in _BLOCKED_WORDS)


def _total_pages(soup) -> int | None:
    """Возвращает общее число страниц из блока пагинации или None, если его нет."""
    max_page = 0
    for link in soup.select('a[data-qa="pager-page"]'):
        try:
            max_page = max(max_page, int(link.get_text(strip=True)))
        except ValueError:
            continue
    return max_page or None


def fetch_all_vacancies(driver: WebDriver, max_pages: int = MAX_PAGES) -> list[Vacancy]:
    if not settings.RESUME_ID:
        raise SystemExit("RESUME_ID не задан в .env")

    base_url = settings.resume_search_url
    vacancies: list[Vacancy] = []
    seen: set[str] = set()
    total_pages: int | None = None

    for page in range(max_pages):
        url = base_url if page == 0 else f"{base_url}&page={page}"
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, "lxml")
        cards = soup.select('article[data-qa="vacancy-serp__vacancy"]')
        for card in cards:
            vacancy = parse_card(card)
            if not vacancy:
                continue
            if is_blocked(vacancy.title):
                continue
            if vacancy.id and vacancy.id in seen:
                continue
            if vacancy.id:
                seen.add(vacancy.id)
            vacancies.append(vacancy)
        print(f"Страница {page + 1}: собрано {len(vacancies)} вакансий...", flush=True)

        if total_pages is None:
            total_pages = _total_pages(soup)
        if total_pages is not None:
            if page + 1 >= total_pages:
                break
        elif not soup.select_one('a[data-qa="pager-next"]'):
            break

    return vacancies
