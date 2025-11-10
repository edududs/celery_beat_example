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
celery -A celery_app.celery_app flower --port=5555
```

**Nota**: Como está rodando localmente, o código usa `localhost` automaticamente (fallback padrão).

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
