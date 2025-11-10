# Celery Beat com Flower

Projeto para testar Celery Beat (agendador de tarefas) e Flower (monitoramento) usando RabbitMQ como broker e Redis como backend.

## Estrutura

- **Infraestrutura**: RabbitMQ e Redis
- **Aplicativos**: Celery Beat, Celery Worker e Flower

## Configuração

O projeto suporta rodar de duas formas:

- **Localmente** (fora do Docker): Usa `localhost` para conectar aos serviços
- **Docker**: Usa os nomes dos serviços (`rabbit`, `redis`) para conectar

A configuração é feita via variáveis de ambiente:

- `CELERY_BROKER_HOST`: Host do RabbitMQ (padrão: `localhost`)
- `CELERY_REDIS_HOST`: Host do Redis (padrão: `localhost`)
- `CELERY_BEAT_SCHEDULE_FILENAME`: Caminho do arquivo SQLite3 do schedule (padrão: `celerybeat-schedule`)

## Opção 1: Rodar Localmente (Recomendado para desenvolvimento)

### Passo 1: Iniciar apenas a infraestrutura via Docker

```bash
docker compose --profile infra up -d
```

Isso inicia:

- RabbitMQ na porta 5672 (Management: <http://localhost:15672>)
- Redis na porta 6379 (Stack UI: <http://localhost:8001>)

### Passo 2: Instalar dependências localmente

```bash
# Criar ambiente virtual (recomendado)
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

# Instalar dependências
pip install -e .
```

### Passo 3: Rodar os aplicativos localmente

Em terminais separados:

```bash
# Terminal 1: Celery Beat
celery -A celery_app.celery_beat beat --loglevel=info

# Terminal 2: Celery Worker
celery -A celery_app.celery_app worker --loglevel=info

# Terminal 3: Flower
celery -A celery_app.celery_app flower --port=5555 --broker_api=http://admin:admin@localhost:15672/api/
```

**Nota**: Como está rodando localmente, o código usa `localhost` automaticamente (fallback padrão).

**Importante**: O parâmetro `--broker_api` é necessário para que o Flower acesse a API de gerenciamento do RabbitMQ e mostre informações sobre filas, exchanges, bindings e estatísticas do broker. Sem esse parâmetro, o Flower consegue conectar ao broker via AMQP (mostra tasks e workers), mas não consegue acessar a API HTTP de gerenciamento para mostrar detalhes das filas.

### Parar a infraestrutura

```bash
docker compose --profile infra down
```

## Opção 2: Rodar Tudo via Docker (Opcional)

### Iniciar tudo (infraestrutura + aplicativos)

```bash
docker compose --profile infra --profile apps up -d
```

Ou simplesmente:

```bash
docker compose up -d
```

### Iniciar apenas os aplicativos (requer infra rodando)

```bash
docker compose --profile apps up -d
```

**Nota**: Os aplicativos no Docker usam os nomes dos serviços (`rabbit`, `redis`) configurados via variáveis de ambiente.

### Parar serviços

```bash
# Parar tudo
docker compose down

# Parar apenas apps
docker compose --profile apps down

# Parar apenas infra
docker compose --profile infra down
```

## Acessos

- **Flower**: <http://localhost:5555>
- **RabbitMQ Management**: <http://localhost:15672> (usuário: `admin`, senha: `admin`)
- **Redis Stack**: <http://localhost:8001>

## Persistência do Schedule (SQLite3)

O Celery Beat usa **SQLite3** por padrão para persistir o estado do agendador. O arquivo `celerybeat-schedule` é um banco de dados SQLite3 que armazena:

- Última execução de cada tarefa agendada
- Próxima execução prevista
- Estado do agendador

Os arquivos auxiliares do SQLite são:

- `celerybeat-schedule-wal`: Write-Ahead Log (WAL) do SQLite
- `celerybeat-schedule-shm`: Shared Memory do SQLite

### Configurações locais

O caminho do arquivo SQLite pode ser configurado via variável de ambiente `CELERY_BEAT_SCHEDULE_FILENAME`:

- **Localmente**: Cria na raiz do projeto (padrão: `celerybeat-schedule`)
- **Docker**: Salva no volume persistente `/app/celerybeat-schedule` (volume `celerybeat_data`)

### Localização dos arquivos

- **Localmente**: Arquivos criados na raiz do projeto (ignorados pelo Git via `.gitignore`)
- **Docker**: Arquivos salvos no volume `celerybeat_data` dentro do container em `/app/`

**Nota**: Os arquivos são ignorados pelo Git (via `.gitignore`) para evitar commits acidentais do estado do agendador.

## Conceitos Avançados do Celery

Este repositório demonstra conceitos importantes do Celery para aprendizado. Todos os exemplos podem ser testados e monitorados via Flower.

### 1. ACK Late (Acknowledgment Late)

**O que é?**
ACK Late determina **quando** uma tarefa é confirmada (acknowledged) no broker.

- **`acks_late=False` (padrão)**: A tarefa é confirmada **imediatamente** ao ser recebida pelo worker
  - ✅ Mais rápido
  - ❌ Se o worker morrer durante a execução, a tarefa é **perdida**

- **`acks_late=True`**: A tarefa é confirmada **após** ser executada com sucesso
  - ✅ Se o worker morrer, a tarefa volta para a fila
  - ✅ Garante que tarefas críticas não sejam perdidas
  - ❌ Um pouco mais lento

**Exemplo**: `task_with_ack_late` em `celery_app/tasks.py`

**Como testar no Flower**:

1. Execute a tarefa `task_with_ack_late`
2. Mate o worker durante a execução (`Ctrl+C` ou `docker kill`)
3. Com `acks_late=True`: a tarefa volta para a fila
4. Com `acks_late=False`: a tarefa é perdida

---

### 2. Retry (Tentativas)

**O que é?**
Retry permite que tarefas que falharam sejam tentadas novamente automaticamente.

**Configurações**:

- `max_retries`: Número máximo de tentativas
- `default_retry_delay`: Tempo de espera entre tentativas (em segundos)
- `retry_backoff`: Ativa backoff exponencial (aumenta o tempo entre tentativas)

**Exemplo**: `task_with_retry` em `celery_app/tasks.py`

**Como testar no Flower**:

1. Execute `task_with_retry` com uma URL inválida
2. Observe no Flower a aba "Tasks" as tentativas sendo executadas
3. Veja o tempo entre tentativas aumentando (backoff exponencial)

---

### 3. Backoff Exponencial

**O que é?**
Backoff exponencial aumenta o tempo de espera entre tentativas de forma exponencial.

**Exemplo com `retry_backoff=True`**:

- 1ª tentativa: após 60 segundos
- 2ª tentativa: após 120 segundos (60 × 2)
- 3ª tentativa: após 240 segundos (60 × 4)

**Fórmula**: `delay = base_delay × (2 ^ tentativa)`

**Configurações**:

- `retry_backoff=True`: Ativa backoff exponencial
- `retry_backoff_max`: Tempo máximo entre tentativas (em segundos)

**Exemplo**: `task_with_retry` e `task_with_custom_backoff` em `celery_app/tasks.py`

---

### 4. Dead Letter Queue (DLQ)

**O que é?**
DLQ é uma fila especial para tarefas que **falharam definitivamente** após esgotar todas as tentativas.

**Fluxo**:

1. Tarefa falha
2. Retry automático (até `max_retries`)
3. Se todas as tentativas falharem → vai para DLQ
4. Tarefas na DLQ podem ser analisadas e reprocessadas manualmente

**Configurações**:

- `dead_letter_exchange`: Exchange para DLQ (padrão: `dlx`)
- `dead_letter_queue`: Nome da fila DLQ (padrão: `dlq`)
- `dead_letter_routing_key`: Routing key para DLQ

**Exemplo**: `task_that_fails_to_dlq` em `celery_app/tasks.py`

**Como testar no Flower**:

1. Execute `task_that_fails_to_dlq` (vai falhar propositalmente)
2. Aguarde as tentativas de retry
3. Após esgotar tentativas, vá em "Broker" > "Queues" > "dlq"
4. Veja a tarefa na Dead Letter Queue

---

### 5. Timeout (Soft e Hard Limit)

**O que é?**
Timeout limita o tempo de execução de uma tarefa para evitar que trave indefinidamente.

**Tipos**:

- **Soft Time Limit**: Envia exceção `SoftTimeLimitExceeded` mas **não mata** a tarefa
  - Permite limpeza/rollback antes de terminar
- **Hard Time Limit**: **Mata** a tarefa forçadamente após o tempo limite
  - Útil para tarefas que podem travar completamente

**Configurações**:

- `time_limit`: Hard limit (em segundos)
- `soft_time_limit`: Soft limit (em segundos)

**Exemplo**: `task_with_timeout` em `celery_app/tasks.py`

**Como testar no Flower**:

1. Execute `task_with_timeout` com `duration=25` (segundos)
2. Com `soft_time_limit=20`: recebe exceção após 20s mas continua
3. Com `time_limit=30`: é morta após 30s

---

### 6. Prefetch

**O que é?**
Prefetch determina quantas tarefas o worker **reserva** antes de processar.

**Configurações**:

- `worker_prefetch_multiplier=1`: Processa uma tarefa por vez
  - ✅ Melhor para tarefas longas
  - ✅ Distribuição mais uniforme entre workers
- `worker_prefetch_multiplier=4` (padrão): Reserva 4 tarefas
  - ✅ Melhor para tarefas rápidas
  - ❌ Pode causar distribuição desigual entre workers

**Exemplo**: Configurado globalmente em `celery_app/celery_app.py`

---

## Tarefas de Exemplo

Todas as tarefas estão em `celery_app/tasks.py` com comentários explicativos:

1. **`simple_task`**: Tarefa simples sem tratamento de erro
2. **`task_with_retry`**: Demonstra retry automático com backoff exponencial
3. **`task_that_fails_to_dlq`**: Demonstra Dead Letter Queue
4. **`task_with_custom_backoff`**: Demonstra backoff customizado
5. **`task_with_timeout`**: Demonstra soft e hard time limit
6. **`task_with_ack_late`**: Demonstra ACK late

### Como Testar as Tarefas

#### Via Python (localmente)

```python
from celery_app.tasks import (
    task_with_retry,
    task_that_fails_to_dlq,
    task_with_timeout,
    task_with_ack_late,
)

# Testar retry
task_with_retry.delay("https://httpstat.us/500")  # URL que retorna erro

# Testar DLQ
task_that_fails_to_dlq.delay(should_fail=True)

# Testar timeout
task_with_timeout.delay(duration=25)

# Testar ACK late
task_with_ack_late.delay({"test": "data"})
```

#### Via Flower

1. Acesse <http://localhost:5555>
2. Vá em "Tasks"
3. Clique em uma tarefa para ver detalhes
4. Use "Apply" para executar com parâmetros customizados

---

## Monitoramento no Flower

O Flower permite monitorar todos esses conceitos em tempo real:

- **Tasks**: Veja todas as tarefas, tentativas, retries e resultados
- **Workers**: Veja workers conectados e suas estatísticas
- **Broker**: Veja filas, exchanges, bindings e a DLQ
- **Monitor**: Veja métricas em tempo real

### O que observar

1. **Retry**: Veja tarefas sendo tentadas novamente na aba "Tasks"
2. **DLQ**: Veja tarefas na fila `dlq` na aba "Broker" > "Queues"
3. **Backoff**: Observe o tempo entre tentativas aumentando
4. **ACK Late**: Mate um worker durante execução e veja a tarefa voltar para a fila

---

## Agendamento com Celery Beat

O Celery Beat permite agendar tarefas de forma periódica usando diferentes tipos de schedule. Os principais são:

### 1. Crontab Schedule

Crontab permite agendar tarefas usando a sintaxe similar ao cron do Unix/Linux.

**Sintaxe básica**:

```python
from celery.schedules import crontab

crontab(minute=0, hour=0, day_of_week=None, day_of_month=None, month_of_year=None)
```

**Exemplos práticos**:

| Exemplo | Significado |
|---------|-------------|
| `crontab()` | Executa a cada minuto |
| `crontab(minute=0, hour=0)` | Executa diariamente à meia-noite |
| `crontab(minute=0, hour='*/3')` | Executa a cada 3 horas: 00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00 |
| `crontab(minute=0, hour='0,3,6,9,12,15,18,21')` | Mesmo que o anterior |
| `crontab(minute='*/15')` | Executa a cada 15 minutos |
| `crontab(day_of_week='sunday')` | Executa a cada minuto aos domingos |
| `crontab(minute='*', hour='*', day_of_week='sun')` | Mesmo que o anterior |
| `crontab(minute='*/10', hour='3,17,22', day_of_week='thu,fri')` | Executa a cada 10 minutos, apenas entre 3-4h, 17-18h e 22-23h nas quintas ou sextas |
| `crontab(minute=0, hour='*/2,*/3')` | Executa a cada hora par e a cada hora divisível por 3 (exceto: 1h, 5h, 7h, 11h, 13h, 17h, 19h, 23h) |
| `crontab(minute=0, hour='*/5')` | Executa em horas divisíveis por 5 (ex: 15h, não 17h) |
| `crontab(minute=0, hour='*/3,8-17')` | Executa a cada hora divisível por 3 E durante horário comercial (8h-17h) |
| `crontab(0, 0, day_of_month='2')` | Executa no dia 2 de cada mês |
| `crontab(0, 0, day_of_month='2-30/2')` | Executa em dias pares do mês |
| `crontab(0, 0, day_of_month='1-7,15-21')` | Executa na primeira e terceira semana do mês |
| `crontab(0, 0, day_of_month='11', month_of_year='5')` | Executa no dia 11 de maio de cada ano |
| `crontab(0, 0, month_of_year='*/3')` | Executa diariamente no primeiro mês de cada trimestre |

**Valores aceitos**:

- `minute`: `0-59` ou `'*'` ou `'*/N'` ou lista `'0,15,30'` ou range `'0-30'`
- `hour`: `0-23` ou `'*'` ou `'*/N'` ou lista `'0,3,6'` ou range `'8-17'`
- `day_of_week`: `0-6` (0=domingo) ou `'sun'`, `'mon'`, etc. ou `'*'`
- `day_of_month`: `1-31` ou `'*'` ou `'*/N'` ou lista ou range
- `month_of_year`: `1-12` ou `'*'` ou `'*/N'` ou lista ou range

**Exemplo de uso**:

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'daily-report': {
        'task': 'tasks.generate_daily_report',
        'schedule': crontab(minute=0, hour=0),  # Meia-noite
    },
    'every-15-minutes': {
        'task': 'tasks.check_status',
        'schedule': crontab(minute='*/15'),
    },
}
```

---

### 2. Solar Schedule

Solar schedule permite agendar tarefas baseado em eventos solares (nascer/pôr do sol, alvorecer, crepúsculo).

**Sintaxe básica**:

```python
from celery.schedules import solar

solar(event, latitude, longitude)
```

**Argumentos**:

- `event`: Tipo de evento solar (ver tabela abaixo)
- `latitude`: Latitude do local (positivo = Norte, negativo = Sul)
- `longitude`: Longitude do local (positivo = Leste, negativo = Oeste)

**Sinais de latitude e longitude**:

| Sinal | Argumento | Significado |
|-------|-----------|-------------|
| `+` | latitude | Norte |
| `-` | latitude | Sul |
| `+` | longitude | Leste |
| `-` | longitude | Oeste |

**Tipos de eventos solares**:

| Evento | Significado |
|--------|-------------|
| `dawn_astronomical` | Executa quando o céu não está mais completamente escuro (sol 18° abaixo do horizonte) |
| `dawn_nautical` | Executa quando há luz suficiente para distinguir o horizonte (sol 12° abaixo do horizonte) |
| `dawn_civil` | Executa quando há luz suficiente para atividades ao ar livre (sol 6° abaixo do horizonte) |
| `sunrise` | Executa quando a borda superior do sol aparece no horizonte leste |
| `solar_noon` | Executa quando o sol está mais alto acima do horizonte no dia |
| `sunset` | Executa quando a borda do sol desaparece no horizonte oeste |
| `dusk_civil` | Executa no fim do crepúsculo civil (sol 6° abaixo do horizonte) |
| `dusk_nautical` | Executa quando o sol está 12° abaixo do horizonte |
| `dusk_astronomical` | Executa quando o céu fica completamente escuro (sol 18° abaixo do horizonte) |

**Exemplo de uso**:

```python
from celery.schedules import solar

celery_app.conf.beat_schedule = {
    # Executa no pôr do sol em Melbourne, Austrália
    'task-at-melbourne-sunset': {
        'task': 'tasks.evening_task',
        'schedule': solar('sunset', -37.81753, 144.96715),  # Melbourne
    },
    # Executa no nascer do sol em São Paulo, Brasil
    'task-at-sao-paulo-sunrise': {
        'task': 'tasks.morning_task',
        'schedule': solar('sunrise', -23.5505, -46.6333),  # São Paulo
    },
}
```

**Coordenadas de exemplo**:

- **São Paulo, Brasil**: `-23.5505, -46.6333`
- **Rio de Janeiro, Brasil**: `-22.9068, -43.1729`
- **Melbourne, Austrália**: `-37.81753, 144.96715`
- **Nova York, EUA**: `40.7128, -74.0060`
- **Londres, Reino Unido**: `51.5074, -0.1278`

---

### 3. Timedelta Schedule

Timedelta permite agendar tarefas com intervalos fixos de tempo.

**Exemplo de uso**:

```python
from celery.schedules import timedelta

celery_app.conf.beat_schedule = {
    'every-30-seconds': {
        'task': 'tasks.periodic_task',
        'schedule': timedelta(seconds=30),
    },
    'every-5-minutes': {
        'task': 'tasks.check_status',
        'schedule': timedelta(minutes=5),
    },
    'every-hour': {
        'task': 'tasks.hourly_task',
        'schedule': timedelta(hours=1),
    },
}
```

---

## Comparação de Schedules

| Tipo | Uso | Exemplo |
|------|-----|---------|
| **timedelta** | Intervalos fixos | A cada 30 segundos, a cada 1 hora |
| **crontab** | Horários específicos | Diariamente à meia-noite, toda segunda-feira às 9h |
| **solar** | Eventos solares | No nascer do sol, no pôr do sol |

**Recomendações**:

- Use `timedelta` para intervalos regulares simples
- Use `crontab` para horários específicos e complexos
- Use `solar` para tarefas relacionadas a eventos naturais (iluminação, segurança, etc.)

---

## Documentação Adicional

Para mais informações sobre schedules, consulte:

- [Celery Schedules Documentation](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html#crontab-schedules)
- [celery.schedules.crontab](https://docs.celeryq.dev/en/stable/reference/celery.schedules.html#celery.schedules.crontab)
- [celery.schedules.solar](https://docs.celeryq.dev/en/stable/reference/celery.schedules.html#celery.schedules.solar)
