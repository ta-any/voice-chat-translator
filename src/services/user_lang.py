from typing import Dict
from loguru import logger

class UserLanguageManager:
    """
    Менеджер языков пользователей
    Хранит языковые предпочтения пользователей в памяти
    Для production используйте Redis или БД
    """
    
    # Статическое хранилище: user_id -> language_code
    _user_languages: Dict[int, str] = {}
    
    def __init__(self, default_language: str = "en"):
        """
        Инициализация менеджера языков
        
        Args:
            default_language: Язык по умолчанию (например, "en")
        """
        self.default_language = default_language
        logger.info(f"Менеджер языков инициализирован. Язык по умолчанию: {default_language}")
    
    def set_user_language(self, user_id: int, language_code: str) -> None:
        """
        Установить язык для пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            language_code: Код языка (ru, en, de и т.д.)
        """
        if not language_code or not isinstance(language_code, str):
            logger.warning(f"Некорректный код языка для пользователя {user_id}: {language_code}")
            return
        
        self._user_languages[user_id] = language_code
        logger.info(f"Установлен язык {language_code} для пользователя {user_id}")
    
    def get_user_language(self, user_id: int) -> str:
        """
        Получить язык пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Код языка пользователя или язык по умолчанию
        """
        language = self._user_languages.get(user_id)
        
        if not language:
            logger.debug(f"Язык пользователя {user_id} не найден, используется {self.default_language}")
            return self.default_language
        
        return language
    
    def remove_user(self, user_id: int) -> bool:
        """
        Удалить язык пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            True если пользователь был удален, False если не найден
        """
        if user_id in self._user_languages:
            del self._user_languages[user_id]
            logger.info(f"Языковые настройки пользователя {user_id} удалены")
            return True
        
        logger.debug(f"Пользователь {user_id} не найден в языковых настройках")
        return False
    
    def clear_all(self) -> int:
        """
        Очистить все языковые настройки
        
        Returns:
            Количество удаленных записей
        """
        count = len(self._user_languages)
        self._user_languages.clear()
        logger.info(f"Очищены языковые настройки {count} пользователей")
        return count
    
    def get_all_users(self) -> Dict[int, str]:
        """
        Получить все языковые настройки
        
        Returns:
            Словарь user_id -> language_code
        """
        return self._user_languages.copy()
    
    def get_users_count(self) -> int:
        """
        Получить количество пользователей с сохраненным языком
        
        Returns:
            Количество пользователей
        """
        return len(self._user_languages)
    
    def has_user(self, user_id: int) -> bool:
        """
        Проверить, есть ли пользователь в настройках
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            True если пользователь существует
        """
        return user_id in self._user_languages
