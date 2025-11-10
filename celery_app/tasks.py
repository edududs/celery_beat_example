"""Celery tasks com exemplos didáticos de retry, DLQ, backoff e ACK late."""

import time
from typing import Any

import requests
from bs4 import BeautifulSoup

from celery_app.celery_app import celery_app


# ============================================================================
# TAREFA PERIÓDICA (Beat Schedule)
# ============================================================================
@celery_app.task
def periodic_task() -> dict[str, Any]:
    """Tarefa periódica executada pelo Celery Beat."""
    response = requests.get("https://www.google.com", timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.string if soup.title else "No title found"
    return {"title": title}


# ============================================================================
# EXEMPLO 1: Tarefa Simples (sem retry)
# ============================================================================
@celery_app.task
def simple_task(message: str) -> str:
    """Tarefa simples sem tratamento de erro."""
    print(f"Processando: {message}")
    return f"Processado: {message}"


# ============================================================================
# EXEMPLO 2: Tarefa com Retry Automático
# ============================================================================
@celery_app.task(
    bind=True,  # bind=True permite acessar self (a instância da tarefa)
    max_retries=3,  # Máximo de 3 tentativas
    default_retry_delay=60,  # Espera 60 segundos entre tentativas
    retry_backoff=True,  # Backoff exponencial: 60s, 120s, 240s
    retry_backoff_max=600,  # Máximo de 10 minutos entre tentativas
)
def task_with_retry(self, url: str) -> dict[str, Any]:
    """Tarefa que tenta fazer uma requisição HTTP e retenta em caso de falha.

    Demonstra:
    - Retry automático com backoff exponencial
    - ACK late (só confirma após sucesso)
    - Tratamento de exceções com retry
    """
    try:
        print(f"[Tentativa {self.request.retries + 1}] Acessando: {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return {"status": "success", "url": url, "status_code": response.status_code}
    except requests.RequestException as exc:
        print(f"Erro ao acessar {url}: {exc}")
        # Retry: relança a tarefa para tentar novamente
        raise self.retry(exc=exc)


# ============================================================================
# EXEMPLO 3: Tarefa que Falha e Vai para DLQ
# ============================================================================
@celery_app.task(
    bind=True,
    max_retries=2,  # Apenas 2 tentativas
    default_retry_delay=30,
    retry_backoff=True,
    # Configuração de DLQ (Dead Letter Queue)
    dead_letter_exchange="dlx",
    dead_letter_queue="dlq",
    dead_letter_routing_key="dlq",
)
def task_that_fails_to_dlq(self, should_fail: bool = True) -> dict[str, Any]:
    """Tarefa que falha propositalmente para demonstrar DLQ.

    Demonstra:
    - Retry limitado (2 tentativas)
    - Após esgotar tentativas, vai para Dead Letter Queue
    - Pode ser monitorada no Flower na aba "Broker" > "Queues" > "dlq"
    """
    if should_fail:
        print(f"[Tentativa {self.request.retries + 1}] Esta tarefa vai falhar!")
        raise ValueError("Falha proposital para demonstrar DLQ")

    return {"status": "success", "message": "Tarefa executada com sucesso"}


# ============================================================================
# EXEMPLO 4: Tarefa com Retry Manual e Backoff Customizado
# ============================================================================
@celery_app.task(bind=True, max_retries=5)
def task_with_custom_backoff(self, attempt: int = 1) -> dict[str, Any]:
    """Tarefa que demonstra retry manual com backoff customizado.

    Demonstra:
    - Retry manual com controle total
    - Backoff customizado (não exponencial)
    - Contagem de tentativas
    """
    try:
        # Simula uma operação que pode falhar
        error_msg = f"Falha na tentativa {attempt}"
        if attempt < 3:
            raise ValueError(error_msg)

        return {
            "status": "success",
            "attempt": attempt,
            "total_retries": self.request.retries,
        }
    except ValueError as exc:
        # Backoff customizado: espera 10 segundos * número da tentativa
        wait_time = 10 * (self.request.retries + 1)
        print(f"Erro na tentativa {self.request.retries + 1}. Retry em {wait_time}s")
        raise self.retry(exc=exc, countdown=wait_time)


# ============================================================================
# EXEMPLO 5: Tarefa com Timeout
# ============================================================================
@celery_app.task(
    time_limit=30,  # Hard limit: mata a tarefa após 30 segundos
    soft_time_limit=20,  # Soft limit: envia exceção após 20 segundos
)
def task_with_timeout(duration: int = 25) -> dict[str, Any]:
    """Tarefa que demonstra timeout (soft e hard limit).

    Demonstra:
    - Soft time limit: envia exceção mas não mata a tarefa
    - Hard time limit: mata a tarefa forçadamente
    - Útil para tarefas que podem travar
    """
    print(f"Executando tarefa que vai demorar {duration} segundos...")
    start_time = time.time()

    try:
        time.sleep(duration)
        return {
            "status": "success",
            "duration": duration,
            "elapsed": time.time() - start_time,
        }
    except Exception as exc:
        return {
            "status": "timeout",
            "error": str(exc),
            "elapsed": time.time() - start_time,
        }


# ============================================================================
# EXEMPLO 6: Tarefa com ACK Late (demonstração)
# ============================================================================
@celery_app.task(acks_late=True)
def task_with_ack_late(data: dict[str, Any]) -> dict[str, Any]:
    """Tarefa que demonstra ACK Late.

    Com acks_late=True:
    - A tarefa só é confirmada (ACK) DEPOIS de executar com sucesso
    - Se o worker morrer durante a execução, a tarefa volta para a fila
    - Útil para tarefas críticas que não podem ser perdidas

    Sem acks_late (padrão):
    - A tarefa é confirmada imediatamente ao ser recebida
    - Se o worker morrer, a tarefa é perdida
    """
    print(f"Processando dados: {data}")
    # Simula processamento
    time.sleep(2)
    return {"status": "success", "processed": data}
