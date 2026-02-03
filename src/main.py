#!/usr/bin/env python3
import asyncio
import sys
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from loguru import logger

from .config import Config
from .handlers.bot_handlers import router  

load_dotenv()

logger.remove()  
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=os.getenv("LOG_LEVEL", "INFO"),
    colorize=True
)

logger.add(
    "logs/main.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="30 days",
    compression="zip"
)

dp = Dispatcher()
dp.include_router(router)

config_bot = Config.from_env()


async def main() -> None:
    """
    Основная функция запуска бота
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК ПРИЛОЖЕНИЯ")
        logger.info("=" * 60)

        bot = Bot(token=config_bot.bot_token, parse_mode=ParseMode.HTML)
        if not bot:
            logger.critical("Не удалось инициализировать бота")
            return

        # Запускаем бота
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        logger.warning("👋 Бот остановлен")
        await bot.session.close()


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    asyncio.run(main())