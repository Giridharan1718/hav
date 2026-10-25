# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
 && apt-get install --no-install-recommends -y build-essential libpq5 \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY seed ./seed
COPY evaluation ./evaluation

RUN pip install --upgrade pip && pip install .

RUN useradd --create-home --uid 10001 hva \
 && chown -R hva:hva /app
USER hva

EXPOSE 8000

# Migrations and seeding are one-shot commands run by docker compose before the API
# starts; this image's default command only serves traffic.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
