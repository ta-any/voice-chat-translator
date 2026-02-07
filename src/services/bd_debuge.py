from sqlalchemy import text
from loguru import logger
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
import os

from .engine import engine, AsyncSessionLocal
from .models import Base


async def inspect_table(
    table_name: str,
    limit: int = 5,
    order_by: Optional[str] = None,
    where_clause: Optional[str] = None,
    show_schema: bool = True
) -> Dict[str, Any]:
    """
    Инспектирует содержимое таблицы в БД с подробной диагностикой
    
    Args:
        table_name: Имя таблицы (например, 'users', 'messages')
        limit: Количество записей для вывода (по умолчанию 5)
        order_by: Колонка для сортировки (например, 'created_at DESC')
        where_clause: Условие WHERE без слова WHERE (например, "telegram_user_id = 123456")
        show_schema: Показывать схему таблицы (колонки и типы)
    
    Returns:
        Словарь с результатами: {
            'exists': bool,
            'row_count': int,
            'columns': List[Dict],
            'sample_rows': List[Dict]
        }
    """
    from src.services.engine import engine
    
    result = {
        'exists': False,
        'row_count': 0,
        'columns': [],
        'sample_rows': []
    }
    
    try:
        async with engine.connect() as conn:
            # 1. Проверяем существование таблицы
            exists_query = text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                )
            """)
            exists_result = await conn.execute(exists_query, {"table_name": table_name})
            table_exists = exists_result.scalar()
            
            if not table_exists:
                logger.warning(f"⚠️  Таблица '{table_name}' НЕ СУЩЕСТВУЕТ в схеме 'public'")
                return result
            
            result['exists'] = True
            logger.info(f"✅ Таблица '{table_name}' найдена")
            
            # 2. Получаем схему таблицы (колонки и типы)
            if show_schema:
                schema_query = text("""
                    SELECT 
                        column_name, 
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                    ORDER BY ordinal_position
                """)
                schema_result = await conn.execute(schema_query, {"table_name": table_name})
                columns = schema_result.fetchall()
                
                logger.info(f"\n📋 Схема таблицы '{table_name}':")
                logger.info(f"{'Колонка':<25} | {'Тип':<20} | {'NULL':<5} | По умолчанию")
                logger.info("-" * 70)
                for col in columns:
                    col_name = col[0]
                    data_type = col[1]
                    nullable = "YES" if col[2] == "YES" else "NO"
                    default = str(col[3])[:30] if col[3] else ""
                    logger.info(f"{col_name:<25} | {data_type:<20} | {nullable:<5} | {default}")
                
                result['columns'] = [
                    {
                        'name': col[0],
                        'type': col[1],
                        'nullable': col[2] == "YES",
                        'default': col[3]
                    }
                    for col in columns
                ]
            
            # 3. Считаем общее количество записей
            count_query = text(f"SELECT COUNT(*) FROM {table_name}")
            if where_clause:
                count_query = text(f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}")
            
            count_result = await conn.execute(count_query)
            row_count = count_result.scalar()
            result['row_count'] = row_count
            
            logger.info(f"\n📊 Статистика таблицы '{table_name}':")
            logger.info(f"   Всего записей: {row_count:,}")
            
            # 4. Получаем образцы записей
            if row_count > 0:
                select_query = f"SELECT * FROM {table_name}"
                if where_clause:
                    select_query += f" WHERE {where_clause}"
                if order_by:
                    select_query += f" ORDER BY {order_by}"
                select_query += f" LIMIT {limit}"
                
                rows_result = await conn.execute(text(select_query))
                rows = rows_result.fetchall()
                
                # 🔑 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: преобразуем RMKeyView в список!
                columns_names = list(rows_result.keys())  # ← БЫЛО: rows_result.keys() → СТАЛО: list(rows_result.keys())
                
                logger.info(f"\n🔍 Примеры записей (первые {min(limit, row_count)} из {row_count}):")
                logger.info("-" * 80)
                
                # Выводим заголовок (первые 5 колонок для компактности)
                header_cols = columns_names[:5]
                header = " | ".join([f"{col:<15}" for col in header_cols])
                if len(columns_names) > 5:
                    header += " | ..."
                logger.info(header)
                logger.info("-" * 80)
                
                # Выводим данные
                for i, row in enumerate(rows, 1):
                    values = []
                    for j, val in enumerate(row[:5]):  # Первые 5 значений
                        # Специальная обработка для длинных текстов и NULL
                        if val is None:
                            display_val = "NULL"
                        elif isinstance(val, str) and len(val) > 20:
                            display_val = val[:17] + "..."
                        else:
                            display_val = str(val)
                        values.append(f"{display_val:<15}")
                    
                    row_str = " | ".join(values)
                    if len(row) > 5:
                        row_str += " | ..."
                    logger.info(f"[{i}] {row_str}")
                
                # Сохраняем полные данные в результат
                result['sample_rows'] = [
                    dict(zip(columns_names, row))
                    for row in rows
                ]
            else:
                logger.info("📭 Таблица пустая (нет записей)")
            
            logger.info("\n" + "=" * 80)
            return result
            
    except Exception as e:
        logger.exception(f"💥 Ошибка при инспекции таблицы '{table_name}': {e}")
        import traceback
        logger.error(traceback.format_exc())
        return result

# ==============================================================================
# Пример использования в main.py
# ==============================================================================

async def debug_database():
    """Полная диагностика БД при запуске в режиме отладки"""
    logger.info("\n" + "🔧" * 40)
    logger.info("🔧 ДИАГНОСТИКА БАЗЫ ДАННЫХ")
    logger.info("🔧" * 40 + "\n")
    
    # Проверяем все основные таблицы
    await check_users_table(limit=2)
    await check_messages_table(limit=2)
    await check_translations_table(limit=2)
    
    # Проверяем связь между таблицами (пример для последнего сообщения)
    from src.services.engine import engine
    async with engine.connect() as conn:
        try:
            result = await conn.execute(text("""
                SELECT 
                    m.id as message_id,
                    m.telegram_message_id,
                    u.telegram_user_id,
                    u.username,
                    m.detected_src_lang,
                    t.target_lang,
                    t.translated_text
                FROM messages m
                JOIN users u ON m.from_user_id = u.id
                LEFT JOIN translations t ON m.id = t.source_message_id
                ORDER BY m.created_at DESC
                LIMIT 3
            """))
            rows = result.fetchall()
            
            if rows:
                logger.info("\n🔗 Пример связанных данных (сообщение → пользователь → перевод):")
                for i, row in enumerate(rows, 1):
                    logger.info(
                        f"[{i}] msg_id={row[1]} | user={row[3] or row[2]} | "
                        f"src={row[4]} → tgt={row[5] or 'N/A'} | "
                        f"text='{(row[6] or '')[:30]}...'"
                    )
        except Exception as e:
            logger.warning(f"⚠️  Не удалось проверить связи между таблицами: {e}")
    
    logger.info("\n" + "✅" * 40)
    logger.info("✅ ДИАГНОСТИКА ЗАВЕРШЕНА")
    logger.info("✅" * 40 + "\n")

async def clear_all_tables(
    session: Optional[AsyncSession] = None,
    confirm: bool = False,
    cascade: bool = False,
    preserve_users: bool = False
) -> dict:
    """
    Очищает содержимое всех таблиц в базе данных
    
    ⚠️ ВНИМАНИЕ: Эта операция НЕОБРАТИМА! Все данные будут удалены.
    
    Args:
        session: Асинхронная сессия (если не передана — создаётся новая)
        confirm: Флаг подтверждения (обязателен в продакшене)
        cascade: Использовать TRUNCATE CASCADE (быстро, но опасно)
        preserve_users: Сохранить таблицу пользователей (полезно для тестов)
    
    Returns:
        dict: Статистика удаления {таблица: количество_удалённых_записей}
    
    Примеры использования:
        # Для разработки (быстро, с подтверждением)
        await clear_all_tables(confirm=True, cascade=True)
        
        # Для тестов (сохранить пользователей)
        await clear_all_tables(confirm=True, preserve_users=True)
        
        # Безопасный режим (без каскада)
        await clear_all_tables(confirm=True)
    """
    # 🔒 Защита от случайного удаления в продакшене
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    if is_production and not confirm:
        raise ValueError(
            "❌ Очистка БД в продакшене запрещена без явного подтверждения (confirm=True). "
            "Убедитесь, что вы понимаете последствия!"
        )
    
    # 🔒 Дополнительная защита: требуем подтверждение всегда в продакшене
    if is_production and not os.getenv("ALLOW_DB_CLEAR", "false").lower() == "true":
        raise ValueError(
            "❌ Очистка БД в продакшене полностью запрещена. "
            "Установите ALLOW_DB_CLEAR=true в .env для разрешения (ТОЛЬКО для экстренных случаев!)."
        )
    
    # Создаём сессию, если не передана
    own_session = False
    if session is None:
        session = AsyncSessionLocal()
        own_session = True
    
    stats = {}
    try:
        logger.warning("⚠️  НАЧАЛО ОЧИСТКИ БАЗЫ ДАННЫХ")
        logger.warning(f"   Режим: {'КАСКАДНЫЙ TRUNCATE' if cascade else 'ПОСЛЕДОВАТЕЛЬНОЕ УДАЛЕНИЕ'}")
        logger.warning(f"   Сохранить пользователей: {preserve_users}")
        logger.warning(f"   Среда: {'ПРОДАКШЕН' if is_production else 'РАЗРАБОТКА'}")
        
        # 🔑 Правильный порядок удаления (с учётом внешних ключей)
        # Сначала дочерние таблицы, потом родительские
        tables_in_order = [
            "translations",        # ← Зависит от messages, users, chats
            "messages",            # ← Зависит от chats, users
            "user_chat_settings",  # ← Зависит от users, chats
            "users",               # ← Родительская таблица
            "chats"                # ← Родительская таблица
        ]
        
        # Удаляем таблицу пользователей, если не нужно сохранять
        if preserve_users:
            tables_in_order.remove("users")
            logger.info("ℹ️  Таблица 'users' будет сохранена")
        
        if cascade:
            # 🔥 БЫСТРЫЙ РЕЖИМ: TRUNCATE CASCADE (только для разработки!)
            # Автоматически удаляет связанные записи через внешние ключи
            table_list = ", ".join(f'"{table}"' for table in tables_in_order)
            truncate_sql = f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"
            
            logger.info(f"⚡ Выполнение: {truncate_sql}")
            result = await session.execute(text(truncate_sql))
            await session.commit()
            
            # Получаем количество удалённых записей через отдельные запросы
            for table in tables_in_order:
                count_result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                stats[table] = count_result.scalar()
            
            logger.success(f"✅ Быстрая очистка завершена. Удалено таблиц: {len(tables_in_order)}")
        
        else:
            # 🐌 БЕЗОПАСНЫЙ РЕЖИМ: Последовательное удаление через DELETE
            for table in tables_in_order:
                # Считаем количество записей ДО удаления
                count_before = await session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                before = count_before.scalar()
                
                # Удаляем записи
                delete_result = await session.execute(
                    text(f"DELETE FROM {table}")
                )
                deleted = delete_result.rowcount
                
                # Сбрасываем автоинкремент (для PostgreSQL)
                await session.execute(
                    text(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1")
                )
                
                await session.commit()
                
                stats[table] = deleted
                logger.info(f"🧹 Таблица '{table}': удалено {deleted} записей (было {before})")
        
        logger.success("✅ ОЧИСТКА БАЗЫ ДАННЫХ ЗАВЕРШЕНА")
        logger.info(f"📊 Статистика: {stats}")
        
        return stats
    
    except Exception as e:
        logger.error(f"💥 Ошибка при очистке БД: {e}")
        await session.rollback()
        raise
    
    finally:
        if own_session:
            await session.close()


async def reset_database(confirm: bool = False) -> bool:
    """
    Полный сброс базы данных: удаление всех таблиц + их повторное создание
    
    ⚠️ ЭТО УДАЛЯЕТ СТРУКТУРУ БД! Используйте с осторожностью.
    
    Args:
        confirm: Подтверждение операции
    
    Returns:
        bool: Успешность операции
    """
    if not confirm:
        raise ValueError("Подтверждение обязательно для сброса структуры БД!")
    
    try:
        logger.warning("⚠️  ПОЛНЫЙ СБРОС СТРУКТУРЫ БАЗЫ ДАННЫХ")
        
        # 1. Удаляем все таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("🗑️  Все таблицы удалены")
        
        # 2. Создаём таблицы заново
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Структура БД восстановлена")
        
        logger.success("✅ Полный сброс БД завершён")
        return True
    
    except Exception as e:
        logger.error(f"💥 Ошибка при сбросе БД: {e}")
        raise


# ==============================================================================
# Утилиты для тестирования и отладки
# ==============================================================================

async def get_table_stats() -> dict:
    """
    Получает статистику по всем таблицам (количество записей)
    
    Returns:
        dict: {таблица: количество_записей}
    """
    stats = {}
    async with AsyncSessionLocal() as session:
        tables = ["users", "chats", "messages", "translations", "user_chat_settings"]
        
        for table in tables:
            try:
                result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                stats[table] = result.scalar()
            except Exception:
                stats[table] = "N/A (таблица не существует)"
    
    return stats


async def print_db_state():
    """Печатает текущее состояние БД для отладки"""
    stats = await get_table_stats()
    
    logger.info("\n" + "=" * 60)
    logger.info("📊 ТЕКУЩЕЕ СОСТОЯНИЕ БАЗЫ ДАННЫХ")
    logger.info("=" * 60)
    
    total = 0
    for table, count in stats.items():
        if isinstance(count, int):
            total += count
            logger.info(f"   {table:<25} : {count:>6} записей")
        else:
            logger.info(f"   {table:<25} : {count}")
    
    logger.info("-" * 60)
    logger.info(f"   ИТОГО                     : {total:>6} записей")
    logger.info("=" * 60 + "\n")