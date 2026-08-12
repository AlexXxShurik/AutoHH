FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-ansi

COPY . .

ENV HEADLESS=true \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

CMD ["python", "scheduler.py"]
