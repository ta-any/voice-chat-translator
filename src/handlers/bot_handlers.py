"""
Обработчики сообщений для Telegram-бота
"""

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from loguru import logger
import os

router = Router()

from ..services.user_lang import UserLanguageManager
from ..services.translator import safe_translate 
lang_manager = UserLanguageManager(default_language="en")


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Обработчик команды /start
    """
    user = message.from_user
    user_id = user.id
    logger.info("clear all data users")
    lang_manager.clear_all()
    logger.info(f"Реакция на команду /start пользователем: {user.id}")

    if user.language_code:
        lang_manager.set_user_language(user_id, "en")
    else: 
        logger.info(f"Нет маркировки языка у пользователя {user}")
        lang_manager.set_user_language(user_id, "ru")

    
    # Получаем язык пользователя
    user_lang = lang_manager.get_user_language(user_id)
    
    # Мультиязычный ответ
    greetings = {
        "ru": f"Привет, {user.first_name}! 👋",
        "en": f"Hello, {user.first_name}! 👋",
        "de": f"Hallo, {user.first_name}! 👋"
    }
    
    greeting = greetings.get(user_lang, greetings["en"])
    await message.answer(
        f"{greeting}"
    )

@router.message(Command("help"))
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


@router.message(Command("info"))
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


@router.message(Command("logs"))
async def command_logs_handler(message: Message) -> None:
    """
    Обработчик команды /logs
    """
    try:
        if os.path.exists("logs/main.log"):
            with open("logs/main.log", "r", encoding="utf-8") as f:
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


@router.message(F.text)
async def echo_handler(message: Message) -> None:
    """
    Обработчик текстовых сообщений (эхо)
    """
    user_text = message.text
    user_name = message.from_user.first_name
    user_id = message.from_user.id

    if not lang_manager.has_user(user_id):
        logger.info("Нет такого пользователя в базе данных")
        await message.answer(f"Вас нет в базе пользователей нажмите \start")
        return None
    
    lang = lang_manager.get_user_language(user_id)

    logger.info(f"Сообщение от {user_id}: {user_text[:50]}...")
    translate_text = safe_translate(user_text, target_lang=lang)
    logger.info(f"Сообщение переведино: {translate_text[:50]}...")

    # Отвечаем пользователю
    await message.answer(
        f"{user_name} написал: \n"
        f"*{translate_text}*\n\n",
        parse_mode=ParseMode.MARKDOWN
    )