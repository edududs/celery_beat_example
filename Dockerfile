FROM python:3.13-slim

WORKDIR /app

# Copiar arquivos de dependências
COPY pyproject.toml ./

# Instalar pip e dependências do projeto
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copiar código da aplicação (será sobrescrito pelo volume no docker-compose,
# mas necessário para o build inicial e para rodar sem volumes)
COPY celery_app ./celery_app
COPY main.py ./

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1

# Comando padrão (será sobrescrito no docker-compose)
CMD ["celery", "--help"]

