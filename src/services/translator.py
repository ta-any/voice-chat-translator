from deep_translator import (
    GoogleTranslator,
    exceptions
)

def safe_translate(text, source_lang="auto", target_lang='en') -> str:
    """Безопасный перевод с обработкой ошибок"""
    try:
        print(f"From fn safe_translate: {text}")
        # Проверяем длину текста
        if len(text) > 4000:
            return "❌ Текст слишком длинный. Максимум 4000 символов."
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        return translator.translate(text)
    
    except exceptions.TranslationNotFound:
        return "❌ Перевод не найден"
    
    except exceptions.TooManyRequests:
        return "⚠️  Слишком много запросов. Попробуйте позже."
    
    except exceptions.NotValidPayload:
        return "❌ Некорректный текст для перевода"
    
    except exceptions.LanguageNotSupportedException:
        return f"❌ Язык {target_lang} не поддерживается"
    
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"
