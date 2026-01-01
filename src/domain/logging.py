"""
Конфигурация логгера для проекта.
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from loguru import logger
from pydantic import BaseModel, Field

from src.settings import settings


class LogConfig(BaseModel):
    """Конфигурация логгера."""
    
    # Уровни логирования
    console_level: str = "INFO"
    file_level: str = "DEBUG"
    json_level: str = "INFO"
    
    # Файлы логов
    log_dir: Path = Field(default=Path("logs"))
    general_log: str = "bot.log"
    error_log: str = "errors.log"
    json_log: str = "bot.json"
    
    # Ротация логов
    rotation: str = "500 MB"
    retention: str = "30 days"
    compression: str = "zip"
    
    # Форматы
    console_format: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    file_format: str = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # Для отладки
    enable_backtrace: bool = False
    enable_diagnose: bool = False
    
    # Дополнительные параметры
    serialize: bool = False  # Для JSON логов


def serialize_record(record: Dict[str, Any]) -> str:
    """
    Сериализация записи лога в JSON.
    """
    subset = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
        "thread": record["thread"].name if record["thread"].name else record["thread"].id,
        "process": record["process"].name if hasattr(record["process"], 'name') else record["process"].id,
    }
    
    # Добавляем exception если есть
    if record["exception"]:
        subset["exception"] = {
            "type": record["exception"].type,
            "value": str(record["exception"].value),
            "traceback": record["exception"].traceback.format() if record["exception"].traceback else None,
        }
    
    # Добавляем extra поля
    if record.get("extra"):
        subset["extra"] = record["extra"]
    
    return json.dumps(subset, ensure_ascii=False)


def create_log_directory(log_dir: Path) -> None:
    """
    Создание директории для логов.
    """
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Log directory created: {log_dir}")
    except Exception as e:
        logger.error(f"Failed to create log directory: {e}")
        raise


def setup_logging(
    config: Optional[LogConfig] = None,
    intercept_third_party: bool = True
) -> None:
    """
    Настройка логгера.
    
    Args:
        config: Конфигурация логгера
        intercept_third_party: Перехватывать логи сторонних библиотек
    """
    # Используем переданную конфигурацию или создаем из настроек
    if config is None:
        config = LogConfig(
            console_level=settings.LOG_LEVEL,
            file_level="DEBUG" if settings.DEBUG else "INFO",
            log_dir=Path(settings.LOG_DIR) if hasattr(settings, 'LOG_DIR') else Path("logs"),
        )
    
    # Создаем директорию для логов
    create_log_directory(config.log_dir)
    
    # Удаляем стандартный обработчик loguru
    logger.remove()
    
    # 1. Консольный вывод (stderr)
    logger.add(
        sys.stderr,
        format=config.console_format,
        level=config.console_level,
        colorize=True,
        backtrace=config.enable_backtrace,
        diagnose=config.enable_diagnose,
        filter=lambda record: record["extra"].get("channel") != "json" if record.get("extra") else True
    )
    
    # 2. Основной файловый лог
    logger.add(
        config.log_dir / config.general_log,
        format=config.file_format,
        level=config.file_level,
        rotation=config.rotation,
        retention=config.retention,
        compression=config.compression,
        enqueue=True,  # Асинхронная запись
        backtrace=config.enable_backtrace,
        diagnose=config.enable_diagnose,
        filter=lambda record: record["level"].no >= logger.level("INFO").no
    )
    
    # 3. Лог ошибок (только ERROR и выше)
    logger.add(
        config.log_dir / config.error_log,
        format=config.file_format,
        level="ERROR",
        rotation=config.rotation,
        retention=config.retention,
        compression=config.compression,
        enqueue=True,
        backtrace=True,  # Всегда включаем backtrace для ошибок
        diagnose=True,   # Всегда включаем diagnose для ошибок
    )
    
    # 4. JSON лог (для анализа в ELK/Splunk и т.д.)
    if config.serialize:
        logger.add(
            config.log_dir / config.json_log,
            format=serialize_record,
            level=config.json_level,
            rotation=config.rotation,
            retention=config.retention,
            compression=config.compression,
            enqueue=True,
            serialize=True,
        )
    
    # 5. Лог отладки (только в режиме DEBUG)
    if settings.DEBUG:
        logger.add(
            config.log_dir / "debug.log",
            format=config.file_format,
            level="DEBUG",
            rotation="100 MB",
            retention="7 days",
            compression=config.compression,
            enqueue=True,
            filter=lambda record: record["level"].no == logger.level("DEBUG").no
        )
    
    logger.info(f"Logging configured. Console level: {config.console_level}, File level: {config.file_level}")
    logger.info(f"Logs directory: {config.log_dir.absolute()}")


# Декораторы и утилиты для логирования
def log_execution_time(func):
    """
    Декоратор для логирования времени выполнения функции.
    """
    async def async_wrapper(*args, **kwargs):
        start_time = datetime.now()
        logger.debug(f"Starting {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Finished {func.__name__} in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    def sync_wrapper(*args, **kwargs):
        start_time = datetime.now()
        logger.debug(f"Starting {func.__name__}")
        try:
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Finished {func.__name__} in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


class LoggerMixin:
    """
    Миксин для добавления логгера в классы.
    """
    
    @property
    def logger(self):
        """
        Возвращает именованный логгер для класса.
        """
        if not hasattr(self, '_logger'):
            class_name = self.__class__.__name__
            self._logger = logger.bind(class_name=class_name)
        return self._logger


# Контекстные менеджеры для логирования
class LoggingContext:
    """
    Контекстный менеджер для временного изменения уровня логирования.
    """
    
    def __init__(self, level: str = "DEBUG", logger_name: Optional[str] = None):
        self.level = level
        self.logger_name = logger_name
        self.original_level = None
        self.logger = logger.bind(context=logger_name) if logger_name else logger
    
    def __enter__(self):
        self.original_level = self.logger._core.min_level
        self.logger.level(self.level)
        self.logger.debug(f"Temporarily changed log level to {self.level}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_level:
            self.logger.level(self.original_level.name)
            self.logger.debug(f"Restored log level to {self.original_level.name}")


# Инициализация логгера при импорте
if not logger._core.handlers:
    setup_logging()

# Экспорт логгера для удобного импорта
__all__ = ["logger", "setup_logging", "log_execution_time", "LoggerMixin", "LoggingContext"]