# src/settings.py
from pydantic_settings import BaseSettings
from typing import List, Optional
from pathlib import Path


class Settings(BaseSettings):
    # Bot
    BOT_TOKEN: str
    # ADMIN_IDS: List[int] = []
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    DEBUG: bool = False
        
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name == "ADMIN_IDS":
                if raw_val:
                    return [int(id.strip()) for id in raw_val.split(",")]
                return []
            elif field_name == "DEBUG":
                return raw_val.lower() in ("true", "1", "yes")
            return raw_val


settings = Settings()