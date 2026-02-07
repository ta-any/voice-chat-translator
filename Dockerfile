# # Dockerfile.dev (для разработки)
# FROM python:3.11-slim

# # RUN apt-get update && apt-get install -y \
# #     gcc \
# #     ffmpeg \
# #     && rm -rf /var/lib/apt/lists/*

# RUN apt-get update && apt-get install -y \
#     gcc \
#     g++ \
#     make \
#     curl \
#     ffmpeg \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt && \
#     pip install watchdog  # Для hot reload

# COPY src/ ./src/

# RUN python -c "import aiogram; print(f'✅ aiogram {aiogram.__version__} установлен')"

# # Для разработки с hot reload
# CMD ["sh", "-c", "watchmedo auto-restart --pattern='*.py' --recursive --directory=/app/src -- python -m src.main"]

# Dockerfile.dev (для разработки с hot reload)
FROM python:3.11-slim

# Установка системных зависимостей для:
# - asyncpg (требует libpq-dev для нативных расширений)
# - компиляции C-расширений Python
# - ffmpeg для работы с медиа в телеграм-боте
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl \
    libpq-dev \
    python3-dev \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Кэшируем зависимости отдельно (ускоряет повторные сборки при изменении кода)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir watchdog  # Для hot reload

# Копируем только исходный код (логи и данные будут в volumes)
COPY src/ ./src/

# Проверка установки ключевых библиотек
RUN python -c "import aiogram; print(f'✅ aiogram {aiogram.__version__} установлен')"

# Для разработки: запуск с горячей перезагрузкой при изменении .py файлов
# --directory=/app/src — следим только за кодом (игнорируем логи/volumes)
CMD ["sh", "-c", \
  "watchmedo auto-restart \
    --pattern='*.py' \
    --recursive \
    --directory=/app/src \
    --directory=/app/alembic \
    --ignore-pattern='*/__pycache__/*' \
    --ignore-pattern='*/logs/*' \
    -- python -u -m src.main"]