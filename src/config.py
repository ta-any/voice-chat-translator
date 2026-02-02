from os import getenv
from dataclasses import dataclass

@dataclass
class Config:
    """Конфигурация приложения"""
    # Telegram
    bot_token: str
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Настройки приложения
    environment: str = "development"
    log_level: str = "INFO"
    debug: bool = False
    
    # Языки
    source_language: str = "ru"
    target_language: str = "en"
    
    # Лимиты
    max_audio_duration: int = 300  # секунд
    max_file_size: int = 50  # МБ
    
    # Пути
    data_dir: str = "/app/data"
    log_dir: str = "/app/logs"
    
    @classmethod
    def from_env(cls) -> "Config":
        """Создание конфигурации из переменных окружения"""
        return cls(
            bot_token=getenv("BOT_TOKEN", ""),
            # redis_host=getenv("REDIS_HOST", "redis"),
            # redis_port=int(getenv("REDIS_PORT", 6379)),
            # redis_db=int(getenv("REDIS_DB", 0)),
            # environment=getenv("ENVIRONMENT", "development"),
            # log_level=getenv("LOG_LEVEL", "INFO"),
            # debug=getenv("DEBUG", "false").lower() == "true",
            # source_language=getenv("SOURCE_LANGUAGE", "ru"),
            # target_language=getenv("TARGET_LANGUAGE", "en"),
            # max_audio_duration=int(getenv("MAX_AUDIO_DURATION", 300)),
            # max_file_size=int(getenv("MAX_FILE_SIZE", 50)),
            # data_dir=getenv("DATA_DIR", "/app/data"),
            # log_dir=getenv("LOG_DIR", "/app/logs"),
        )
    
    def validate(self) -> bool:
        """Валидация конфигурации"""
        if not self.bot_token or self.bot_token == "your_bot_token_here":
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
        return True