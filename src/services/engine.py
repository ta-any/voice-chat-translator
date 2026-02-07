from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from loguru import logger
from sqlalchemy import text
import os
from .models import Base

# Настройки из окружения
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "telegram_bot")
DB_USER = os.getenv("DB_USER", "botuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "dev_password")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Асинхронный движок
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    echo=DEBUG,  # SQL-логи только в дебаге
    poolclass=NullPool if DEBUG else None  # Для тестов/разработки
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def init_db():
    """Создание таблиц напрямую без миграций"""
    
    try:
        async with engine.begin() as conn:
            # Создаём все таблицы из моделей
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Таблицы созданы в PostgreSQL")
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблиц: {e}")
        raise

async def dispose_db():
    """Закрытие соединений"""
    await engine.dispose()
    logger.info("🔌 Соединения с БД закрыты")

async def test_tables():
    """Проверка созданных таблиц с корректным выводом"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            # ПРАВИЛЬНЫЙ ВЫВОД ЧЕРЕЗ F-СТРОКУ
            if tables:
                logger.info(f"✅ Найдены таблицы в БД: {tables}")
            else:
                logger.warning("⚠️  В базе данных нет таблиц! Проверь подключение и права доступа.")
                
            return tables
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки таблиц: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []
