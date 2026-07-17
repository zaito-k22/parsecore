FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv
RUN pip install uv

# Copiar únicamente dependencias primero
COPY pyproject.toml .
COPY uv.lock .

# Instalar dependencias
RUN uv sync --frozen

# Copiar el proyecto
COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]