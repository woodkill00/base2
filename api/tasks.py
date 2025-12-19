import os
from celery import Celery

# Broker/backends from environment; defaults align with .env.example
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

app = Celery(
    "base2",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

# Basic config can be extended as needed
app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

@app.task(name="base2.ping")
def ping():
    return "pong"

@app.task(name="base2.add")
def add(x: int, y: int) -> int:
    return int(x) + int(y)
