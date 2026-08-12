import asyncio

from taskiq.api.scheduler import run_scheduler_task

from app.tasks import raise_resume_task, scheduler


async def main() -> None:
    await raise_resume_task.kiq()
    await run_scheduler_task(
        scheduler,
        run_startup=True,
        interval=None,
        loop_interval=None,
    )


if __name__ == "__main__":
    asyncio.run(main())
