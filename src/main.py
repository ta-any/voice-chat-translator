# src/main.py
import asyncio
import sys

# Импортируем логгер
from src.domain.logging import logger, setup_logging
# from src.settings import settings

async def main_async():
    """Асинхронная основная функция."""
    # Настройка логирования
    setup_logging()
    
    logger.info("=" * 60)
    logger.info("Starting Voice Chat Translator Bot")



def main():
    """Точка входа приложения."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()