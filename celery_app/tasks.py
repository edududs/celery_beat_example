"""Celery tasks."""

from typing import Any

import requests
from bs4 import BeautifulSoup

from celery_app.celery_app import celery_app


@celery_app.task
def periodic_task() -> dict[str, Any]:
    """Tarefa periódica."""
    response = requests.get("https://www.google.com", timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.string if soup.title else "No title found"
    return {"title": title}


@celery_app.task
def example_task(message: str) -> str:
    """Tarefa de exemplo."""
    print(f"Processando: {message}")
    return f"Processado: {message}"
