"""Celery Beat schedule configuration."""

import os

from celery.schedules import timedelta

from celery_app.celery_app import celery_app

# Configurar o arquivo de schedule SQLite3
# Por padrão, o Celery Beat usa SQLite3 para persistir o estado do agendador
# O arquivo é criado no diretório de trabalho atual
# Quando rodando localmente: usa o diretório atual
# Quando rodando no Docker: usa /app (volume persistente)
schedule_filename = os.getenv(
    "CELERY_BEAT_SCHEDULE_FILENAME",
    "celerybeat-schedule",  # Padrão: cria na raiz do projeto
)
celery_app.conf.beat_schedule_filename = schedule_filename

celery_app.conf.beat_schedule = {
    "periodic-task": {
        "task": "celery_app.tasks.periodic_task",
        "schedule": timedelta(seconds=30),  # Executa a cada 30 segundos
    },
}
