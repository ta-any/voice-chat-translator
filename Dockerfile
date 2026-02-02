# Dockerfile.dev (для разработки)
FROM python:3.11-slim

# RUN apt-get update && apt-get install -y \
#     gcc \
#     ffmpeg \
#     && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install watchdog  # Для hot reload

COPY src/ ./src/

RUN python -c "import aiogram; print(f'✅ aiogram {aiogram.__version__} установлен')"

# Для разработки с hot reload
CMD ["sh", "-c", "watchmedo auto-restart --pattern='*.py' --recursive --directory=/app/src -- python -m src.main"]