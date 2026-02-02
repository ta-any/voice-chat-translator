#!/usr/bin/env python3
"""
Простой Telegram бот с aiogram, python-dotenv и loguru
"""

import asyncio
import sys
import os

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from dotenv import load_dotenv
from loguru import logger


from .config import Config
config_bot = Config.from_env()

# Загружаем переменные окружения
load_dotenv()

# Настройка loguru
logger.remove()  # Убираем стандартный обработчик
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

# Создаем диспетчер
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Обработчик команды /start
    """
    user = message.from_user
    logger.info(f"Реакция на команду /start пользователем: {user.id}")
    logger.debug(f"Успешная обработка /start от пользователя {user.id}")
    
    await message.answer(
        f"👋 Привет, {user.full_name}!\n\n"
        f"Я простой бот на aiogram.\n"
        f"Использую:\n"
        f"• python-dotenv для настроек\n"
        f"• loguru для логирования\n"
        f"• aiogram для Telegram API"
    )

@dp.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    """
    Обработчик команды /help
    """
    logger.debug(f"Пользователь {message.from_user.id} запросил помощь")
    
    help_text = (
        "📚 *Доступные команды:*\n\n"
        "/start - Начать диалог\n"
        "/help - Показать эту справку\n"
        "/info - Информация о боте\n"
        "/logs - Статистика логов\n\n"
        "Просто напишите что-нибудь, и я отвечу!"
    )
    
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("info"))
async def command_info_handler(message: Message) -> None:
    """
    Обработчик команды /info
    """
    user = message.from_user
    
    info_text = (
        "🤖 *Информация о боте*\n\n"
        "*Технологии:*\n"
        "• Aiogram 3.x (асинхронный)\n"
        "• Python-dotenv (конфигурация)\n"
        "• Loguru (логирование)\n"
        "• Docker (контейнеризация)\n\n"
        "*Ваши данные:*\n"
        f"• ID: `{user.id}`\n"
        f"• Имя: {user.first_name}\n"
        f"• Фамилия: {user.last_name or '❌'}\n"
        f"• Username: @{user.username or '❌'}\n"
        f"• Язык: {user.language_code or '❌'}"
    )
    
    logger.info(f"Отправлена информация пользователю {user.id}")
    await message.answer(info_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("logs"))
async def command_logs_handler(message: Message) -> None:
    """
    Обработчик команды /logs
    """
    try:
        import os
        if os.path.exists("logs/bot.log"):
            with open("logs/bot.log", "r", encoding="utf-8") as f:
                lines = f.readlines()[-5:]  # Последние 5 строк
            
            log_text = "📊 *Последние записи в логе:*\n\n"
            log_text += "```\n"
            log_text += "".join(lines)
            log_text += "```"
            
            await message.answer(log_text, parse_mode=ParseMode.MARKDOWN)
        else:
            await message.answer("Файл логов не найден")
    except Exception as e:
        logger.error(f"Ошибка при чтении логов: {e}")
        await message.answer(f"Ошибка при чтении логов: {e}")

@dp.message(F.text)
async def echo_handler(message: Message) -> None:
    """
    Обработчик текстовых сообщений (эхо)
    """
    user_text = message.text
    
    # Логируем полученное сообщение
    logger.info(f"Сообщение от {message.from_user.id}: {user_text[:50]}...")
    
    # Отвечаем пользователю
    await message.answer(
        f"📝 Вы написали: *{user_text}*\n\n"
        f"Количество символов: {len(user_text)}",
        parse_mode=ParseMode.MARKDOWN
    )

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
            log.critical("Не удалось инициализировать бота")
            return
        
        # Запускаем бота
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        logger.warning("👋 Бот остановлен")
        await bot.session.close()

if __name__ == "__main__":
    # Создаем папку для логов
    import os
    os.makedirs("logs", exist_ok=True)
    
    # Запускаем бота
    asyncio.run(main())