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
from ..services.translator import translate_msg
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert

from ..services.engine import AsyncSessionLocal
from ..services.models import User, Chat

lang_manager = UserLanguageManager(default_language="en")


# Маппинг языковых кодов Telegram → NLLB
TELEGRAM_TO_NLLB = {
    'en': 'eng_Latn',
    'ru': 'rus_Cyrl',
    'de': 'deu_Latn',
    'fr': 'fra_Latn',
    'es': 'spa_Latn',
    'zh': 'zho_Hans',
    'ja': 'jpn_Jpan',
    'ko': 'kor_Hang',
    'uk': 'ukr_Cyrl',
    'be': 'bel_Cyrl',
    'kk': 'kaz_Cyrl',
    'hy': 'hye_Armn',
    # Добавь другие языки по необходимости
}

def map_language_code(telegram_code: str) -> str:
    """Конвертирует код языка Telegram в формат NLLB"""
    if not telegram_code:
        return 'rus_Cyrl'  # Язык по умолчанию
    
    # Обрабатываем коды вида 'en-GB', 'ru-RU'
    base_code = telegram_code.split('-')[0].lower()
    return TELEGRAM_TO_NLLB.get(base_code, 'rus_Cyrl')


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Обработчик команды /start — сохраняет пользователя и чат в БД
    """
    user = message.from_user
    chat = message.chat
    
    logger.info(f"🚀 /start от пользователя {user.id} в чате {chat.id}")
    
    async with AsyncSessionLocal() as session:
        try:
            # === ШАГ 1: Сохраняем/обновляем пользователя ===
            # Используем PostgreSQL UPSERT (INSERT ... ON CONFLICT DO UPDATE)
            user_stmt = insert(User).values(
                telegram_user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                default_src_lang='auto',  # Автоматическое определение языка
                default_tgt_lang=map_language_code(user.language_code),
                style='formal',  # Стиль по умолчанию
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ).on_conflict_do_update(
                index_elements=['telegram_user_id'],  # Уникальный ключ
                set_={
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'default_tgt_lang': map_language_code(user.language_code),
                    'updated_at': datetime.utcnow()
                }
            ).returning(User)
            
            user_result = await session.execute(user_stmt)
            db_user = user_result.scalar_one()
            await session.commit()
            
            logger.info(f"✅ Пользователь {user.id} сохранён/обновлён (ID в БД: {db_user.id})")
            
            # === ШАГ 2: Сохраняем/обновляем чат ===
            chat_stmt = insert(Chat).values(
                telegram_chat_id=chat.id,
                type=chat.type,
                title=chat.title,
                settings_json={
                    "auto_translate": False,
                    "default_target_lang": map_language_code(user.language_code),
                    "allowed_languages": ["eng_Latn", "rus_Cyrl", "deu_Latn", "fra_Latn"],
                    "translation_buttons": True
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ).on_conflict_do_update(
                index_elements=['telegram_chat_id'],
                set_={
                    'type': chat.type,
                    'title': chat.title,
                    'updated_at': datetime.utcnow()
                }
            ).returning(Chat)
            
            chat_result = await session.execute(chat_stmt)
            db_chat = chat_result.scalar_one()
            await session.commit()
            
            logger.info(f"✅ Чат {chat.id} сохранён/обновлён (ID в БД: {db_chat.id}, тип: {chat.type})")
            
            # === ШАГ 3: Устанавливаем язык для менеджера ===
            target_lang = map_language_code(user.language_code)
            lang_manager.set_user_language(user.id, target_lang.split('_')[0])  # 'eng_Latn' → 'en'
            
            # === ШАГ 4: Формируем мультиязычное приветствие ===
            greetings = {
                "ru": (
                    f"Привет, {user.first_name or 'друг'}! 👋\n\n"
                    "Я бот-переводчик. Просто отправь сообщение в чат, и я предложу варианты перевода.\n"
                    "Используй команду /language для изменения языка перевода."
                ),
                "en": (
                    f"Hello, {user.first_name or 'friend'}! 👋\n\n"
                    "I'm a translation bot. Just send a message in the chat, and I'll offer translation options.\n"
                    "Use /language command to change translation language."
                ),
                "de": (
                    f"Hallo, {user.first_name or 'Freund'}! 👋\n\n"
                    "Ich bin ein Übersetzungsbot. Sende einfach eine Nachricht im Chat, und ich biete Übersetzungsoptionen an.\n"
                    "Verwende den Befehl /language, um die Übersetzungssprache zu ändern."
                )
            }
            
            # Определяем язык приветствия на основе языка пользователя
            lang_prefix = target_lang.split('_')[0]  # 'eng_Latn' → 'eng'
            lang_short = lang_prefix[:2]  # 'eng' → 'en'
            greeting = greetings.get(lang_short, greetings["en"])
            
            # === ШАГ 5: Отправляем приветствие ===
            await message.answer(greeting)
            
            logger.info(f"📨 Приветствие отправлено пользователю {user.id} на языке {lang_short}")
            
        except Exception as e:
            logger.exception(f"❌ Ошибка при обработке /start для пользователя {user.id}: {e}")
            await session.rollback()
            await message.answer(
                "Произошла ошибка при инициализации. Попробуйте позже."
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

    logger.info(f"Сообщение от {str(user_id)[:3]}: {user_text[:50]}...")
    translate_text = translate_msg(user_text)
    logger.info(f"Сообщение переведино: {translate_text[:50]}...")
    if "Таймаут" in translate_text:
        logger.warning(f"Translation timeout for user {user_id}")
        await message.answer(
            f"Ошибка таймаута",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Отвечаем пользователю
        # await message.reply(f"Перевод:\n{translate_text}")
        await message.answer(
            f"{user_name} написал: \n"
            f"*{translate_text}*\n\n",
            parse_mode=ParseMode.MARKDOWN
        )