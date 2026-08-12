import asyncio

from taskiq import InMemoryBroker, TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from app.auth import ensure_logged_in
from app.config import settings
from app.driver import create_driver
from app.resume import raise_resume

broker = InMemoryBroker()
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)


@broker.task(schedule=[{"cron": settings.CRON, "cron_offset": settings.TZ}])
async def raise_resume_task() -> str:
    result = await asyncio.to_thread(_raise_resume)
    print(result, flush=True)
    return result


def _raise_resume() -> str:
    print("Открываю браузер...", flush=True)
    driver = create_driver()
    try:
        ensure_logged_in(driver)
        print("Проверяю возможность поднять резюме...", flush=True)
        if raise_resume(driver):
            return "Резюме поднято."
        return "Поднимать резюме сейчас нельзя."
    finally:
        driver.quit()
