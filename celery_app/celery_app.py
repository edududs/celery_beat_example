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
    # Serialização
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # ============================================================================
    # Configurações de Acknowledgment (ACK)
    # ============================================================================
    # ACK Late: A tarefa só é confirmada (ACK) DEPOIS de ser executada com sucesso
    # - True: ACK só após execução bem-sucedida (recomendado para tarefas críticas)
    # - False: ACK imediatamente ao receber (padrão, mais rápido mas menos seguro)
    task_acks_late=True,
    # Rejeitar tarefas que falharam após todas as tentativas
    task_reject_on_worker_lost=True,
    # ============================================================================
    # Configurações de Retry e Dead Letter Queue (DLQ)
    # ============================================================================
    # Número máximo de tentativas antes de enviar para DLQ
    task_max_retries=3,
    # Tempo padrão de retry (pode ser sobrescrito por tarefa)
    task_default_retry_delay=60,  # 60 segundos
    # Backoff exponencial: aumenta o tempo entre tentativas
    # Exemplo: 1ª tentativa após 60s, 2ª após 120s, 3ª após 240s
    task_retry_backoff=True,
    # Máximo de tempo de backoff (em segundos)
    task_retry_backoff_max=600,  # 10 minutos
    # ============================================================================
    # Dead Letter Queue (DLQ) - Fila para tarefas que falharam definitivamente
    # ============================================================================
    # Nome da exchange para DLQ
    task_default_dead_letter_exchange="dlx",
    # Nome da fila para DLQ
    task_default_dead_letter_queue="dlq",
    # Routing key para DLQ
    task_default_dead_letter_routing_key="dlq",
    # ============================================================================
    # Configurações de Timeout
    # ============================================================================
    # Timeout padrão para tarefas (em segundos)
    task_time_limit=300,  # 5 minutos
    # Tempo limite suave (soft limit) - envia exceção mas não mata a tarefa
    task_soft_time_limit=240,  # 4 minutos
    # ============================================================================
    # Configurações de Prefetch
    # ============================================================================
    # Prefetch: quantas tarefas o worker reserva antes de processar
    # - 1: Processa uma tarefa por vez (melhor para tarefas longas)
    # - 4: Padrão (melhor para tarefas rápidas)
    worker_prefetch_multiplier=1,
    # ============================================================================
    # Configurações de Result Backend
    # ============================================================================
    # Tempo de expiração dos resultados (em segundos)
    result_expires=3600,  # 1 hora
    # Persistir resultados mesmo após expiração
    result_persistent=True,
)
