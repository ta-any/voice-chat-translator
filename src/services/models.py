"""
Модели базы данных для телеграм-бота переводчика
Все таблицы в одном файле — без ошибок с перечислениями
"""
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Index,
    func
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from typing import Tuple, Optional
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from aiogram.types import User as TelegramUser

# ЕДИНСТВЕННЫЙ ИМПОРТ
Base = declarative_base() 

class User(Base):
    """
    Пользователи Telegram с персональными настройками перевода
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    
    # Профиль Telegram
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # Настройки перевода по умолчанию (строки вместо Enum)
    default_src_lang = Column(String(20), default="auto", nullable=False)  # eng_Latn, rus_Cyrl, auto
    default_tgt_lang = Column(String(20), default="rus_Cyrl", nullable=False)
    style = Column(String(20), default="formal", nullable=False)  # formal, informal, simplified, technical
    
    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    messages = relationship("Message", back_populates="from_user", lazy="selectin")
    translations = relationship("Translation", back_populates="user", lazy="selectin")
    chat_settings = relationship("UserChatSettings", back_populates="user", lazy="selectin")
    
    __table_args__ = (
        Index('idx_users_telegram_id', 'telegram_user_id'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_user_id})>"
    
    # ======================
    # МЕТОДЫ РАБОТЫ С БАЗОЙ ДАННЫХ
    # ======================
    
    @classmethod
    async def get_or_create(
        cls,
        session: AsyncSession,
        telegram_user: TelegramUser,
        default_tgt_lang: str = "rus_Cyrl"
    ) -> Tuple["User", bool]:
        """
        Получает существующего пользователя или создаёт нового (аналог get_or_create из Django)
        
        Args:
            session: Асинхронная сессия SQLAlchemy
            telegram_user: Объект пользователя из aiogram
            default_tgt_lang: Язык перевода по умолчанию (формат NLLB: eng_Latn, rus_Cyrl)
        
        Returns:
            Tuple[User, bool]: (пользователь, был_ли_создан_новый)
        
        Пример использования:
            user, is_new = await User.get_or_create(session, message.from_user)
            if is_new:
                logger.info(f"🆕 Новый пользователь {user.telegram_user_id}")
        """
        # Пытаемся найти существующего пользователя
        result = await session.execute(
            select(cls).where(cls.telegram_user_id == telegram_user.id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Обновляем данные профиля (на случай изменения username/имени)
            existing_user.username = telegram_user.username
            existing_user.first_name = telegram_user.first_name
            existing_user.last_name = telegram_user.last_name
            existing_user.updated_at = datetime.utcnow()
            
            # Обновляем целевой язык, если передан
            if default_tgt_lang != "rus_Cyrl":
                existing_user.default_tgt_lang = default_tgt_lang
            
            await session.commit()
            await session.refresh(existing_user)
            return existing_user, False
        
        # Создаём нового пользователя
        new_user = cls(
            telegram_user_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            default_src_lang="auto",
            default_tgt_lang=default_tgt_lang,
            style="formal",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        return new_user, True
    
    @classmethod
    async def upsert(
        cls,
        session: AsyncSession,
        telegram_user: TelegramUser,
        default_tgt_lang: Optional[str] = None
    ) -> "User":
        """
        Атомарный UPSERT через нативный PostgreSQL синтаксис (быстрее чем get_or_create)
        
        Args:
            session: Асинхронная сессия SQLAlchemy
            telegram_user: Объект пользователя из aiogram
            default_tgt_lang: Язык перевода (если None — не обновляется у существующего)
        
        Returns:
            User: Сохранённый/обновлённый пользователь
        
        Преимущества:
            - Один запрос к БД вместо двух (SELECT + INSERT/UPDATE)
            - Атомарная операция (без гонок при параллельных запросах)
            - Оптимально для высоконагруженных ботов
        """
        # Формируем данные для вставки
        insert_data = {
            "telegram_user_id": telegram_user.id,
            "username": telegram_user.username,
            "first_name": telegram_user.first_name,
            "last_name": telegram_user.last_name,
            "default_src_lang": "auto",
            "default_tgt_lang": default_tgt_lang or "rus_Cyrl",
            "style": "formal",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Формируем данные для обновления (только изменяемые поля)
        update_data = {
            "username": telegram_user.username,
            "first_name": telegram_user.first_name,
            "last_name": telegram_user.last_name,
            "updated_at": datetime.utcnow()
        }
        
        # Если передан язык — добавляем в обновление
        if default_tgt_lang:
            update_data["default_tgt_lang"] = default_tgt_lang
        
        # Выполняем нативный PostgreSQL UPSERT
        stmt = insert(cls).values(**insert_data).on_conflict_do_update(
            index_elements=["telegram_user_id"],
            set_=update_data
        ).returning(cls)
        
        result = await session.execute(stmt)
        user = result.scalar_one()
        await session.commit()
        
        return user
    
    @classmethod
    async def get_by_telegram_id(
        cls,
        session: AsyncSession,
        telegram_user_id: int
    ) -> Optional["User"]:
        """
        Получает пользователя по его Telegram ID
        
        Args:
            session: Асинхронная сессия SQLAlchemy
            telegram_user_id: ID пользователя в Telegram
        
        Returns:
            User | None: Пользователь или None если не найден
        """
        result = await session.execute(
            select(cls).where(cls.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()
    
    async def update_language_settings(
        self,
        session: AsyncSession,
        default_src_lang: Optional[str] = None,
        default_tgt_lang: Optional[str] = None,
        style: Optional[str] = None
    ) -> "User":
        """
        Обновляет настройки языка для существующего пользователя
        
        Args:
            session: Асинхронная сессия SQLAlchemy
            default_src_lang: Язык источника (если не None)
            default_tgt_lang: Язык перевода (если не None)
            style: Стиль перевода (если не None)
        
        Returns:
            User: Обновлённый пользователь
        """
        if default_src_lang is not None:
            self.default_src_lang = default_src_lang
        if default_tgt_lang is not None:
            self.default_tgt_lang = default_tgt_lang
        if style is not None:
            self.style = style
        
        self.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(self)
        
        return self


class Chat(Base):
    """
    Чаты, группы и каналы где работает бот
    """
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    type = Column(String(20), nullable=False)  # private/group/supergroup/channel
    title = Column(String(255), nullable=True)
    
    # Гибкие настройки чата в JSONB
    settings_json = Column(JSON, default={
        "auto_translate": False,
        "default_target_lang": "rus_Cyrl",
        "allowed_languages": ["eng_Latn", "rus_Cyrl", "deu_Latn", "fra_Latn"],
        "translation_buttons": True
    }, nullable=False)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    messages = relationship("Message", back_populates="chat", lazy="selectin")
    translations = relationship("Translation", back_populates="delivery_chat", lazy="selectin")
    user_settings = relationship("UserChatSettings", back_populates="chat", lazy="selectin")
    
    __table_args__ = (
        Index('idx_chats_telegram_id', 'telegram_chat_id'),
        Index('idx_chats_type', 'type'),
    )
    
    def __repr__(self):
        return f"<Chat(id={self.id}, telegram_id={self.telegram_chat_id}, type={self.type})>"


class Message(Base):
    """
    Исходные сообщения с детектированным языком
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    telegram_message_id = Column(Integer, nullable=False)
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    text = Column(Text, nullable=False)
    detected_src_lang = Column(String(20), nullable=False)  # eng_Latn, rus_Cyrl
    
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    chat = relationship("Chat", back_populates="messages")
    from_user = relationship("User", back_populates="messages")
    translations = relationship("Translation", back_populates="source_message", lazy="selectin", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('chat_id', 'telegram_message_id', name='uq_chat_message'),
        Index('idx_messages_chat_created', 'chat_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, chat_id={self.chat_id}, msg_id={self.telegram_message_id})>"


class Translation(Base):
    """
    Конкретные переводы для конкретных пользователей
    """
    __tablename__ = "translations"
    
    id = Column(Integer, primary_key=True, index=True)
    source_message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    target_lang = Column(String(20), nullable=False, index=True)
    style = Column(String(20), nullable=False)  # formal, informal, simplified, technical
    translated_text = Column(Text, nullable=False)
    
    delivery_chat_id = Column(Integer, ForeignKey("chats.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending/sent/failed
    
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    source_message = relationship("Message", back_populates="translations")
    user = relationship("User", back_populates="translations")
    delivery_chat = relationship("Chat", foreign_keys=[delivery_chat_id])
    
    __table_args__ = (
        UniqueConstraint('source_message_id', 'user_id', 'target_lang', 'style', name='uq_translation_unique'),
        Index('idx_translations_user_created', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Translation(id={self.id}, msg_id={self.source_message_id})>"


class UserChatSettings(Base):
    """
    Персональные настройки пользователя в конкретном чате
    """
    __tablename__ = "user_chat_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    
    src_lang_override = Column(String(20), nullable=True)
    tgt_lang_override = Column(String(20), nullable=True)
    auto_translate_mode = Column(String(20), default="off", nullable=False)  # off/on/on_command/on_button
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    user = relationship("User", back_populates="chat_settings")
    chat = relationship("Chat", back_populates="user_settings")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'chat_id', name='uq_user_chat_settings'),
        Index('idx_settings_user_chat', 'user_id', 'chat_id'),
    )
    
    def __repr__(self):
        return f"<UserChatSettings(user_id={self.user_id}, chat_id={self.chat_id})>"


# ======================
# ВАЛИДАЦИЯ НА УРОВНЕ ПРИЛОЖЕНИЯ (вместо Enum в БД)
# ======================

VALID_STYLES = {"formal", "informal", "simplified", "technical"}
VALID_CHAT_TYPES = {"private", "group", "supergroup", "channel"}
VALID_TRANSLATION_STATUSES = {"pending", "sent", "failed"}
VALID_AUTO_TRANSLATE_MODES = {"off", "on", "on_command", "on_button"}

def validate_style(style: str) -> str:
    """Валидация стиля перевода"""
    if style not in VALID_STYLES:
        raise ValueError(f"Недопустимый стиль перевода: {style}. Допустимые: {VALID_STYLES}")
    return style

def validate_chat_type(chat_type: str) -> str:
    """Валидация типа чата"""
    if chat_type not in VALID_CHAT_TYPES:
        raise ValueError(f"Недопустимый тип чата: {chat_type}. Допустимые: {VALID_CHAT_TYPES}")
    return chat_type