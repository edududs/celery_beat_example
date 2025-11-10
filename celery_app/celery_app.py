"""Celery application configuration."""

import os

from celery import Celery

# Configuração via variáveis de ambiente com fallback para localhost
# Quando rodando localmente, usa localhost
# Quando rodando no Docker, usa os nomes dos serviços
broker_host = os.getenv("CELERY_BROKER_HOST", "localhost")
redis_host = os.getenv("CELERY_REDIS_HOST", "localhost")

broker_url = f"amqp://admin:admin@{broker_host}:5672//"
result_backend = f"redis://{redis_host}:6379/0"

celery_app = Celery(
    "celery_app",
    broker=broker_url,
    backend=result_backend,
    include=["celery_app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
