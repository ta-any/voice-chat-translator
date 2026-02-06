# import asyncio
# from functools import partial
# from deep_translator import GoogleTranslator, exceptions

# async def safe_translate(
#     text: str,
#     source_lang: str = "auto",
#     target_lang: str = "en",
#     timeout: int = 30
# ) -> str:
#     """Асинхронный перевод с таймаутом и защитой от блокировок"""
#     try:
#         if not text or not text.strip():
#             return "⚠️ Пустой текст"

#         if len(text) > 4000:
#             return "❌ Текст слишком длинный. Максимум 4000 символов."

#         # Запускаем синхронный перевод в отдельном потоке
#         loop = asyncio.get_running_loop()
#         translator = GoogleTranslator(source=source_lang, target=target_lang)

#         # Добавляем жёсткий таймаут на весь вызов
#         translated = await asyncio.wait_for(
#             loop.run_in_executor(None, partial(translator.translate, text)),
#             timeout=timeout
#         )
#         return translated.strip() if translated else "⚠️ Пустой результат перевода"

#     except asyncio.TimeoutError:
#         return f"⏰ Таймаут перевода ({timeout} сек). Возможно, проблемы с сетью или Google заблокирован."

#     except exceptions.TranslationNotFound:
#         return "❌ Перевод не найден"

#     except exceptions.TooManyRequests:
#         return "⚠️ Слишком много запросов. Подождите 1–2 минуты."

#     except exceptions.NotValidPayload:
#         return "❌ Некорректный текст для перевода"

#     except exceptions.LanguageNotSupportedException as e:
#         return f"❌ Язык не поддерживается: {target_lang}"

#     except Exception as e:
#         # Логируем реальную ошибку для дебага
#         print(f"[DEBUG] Ошибка перевода: {type(e).__name__}: {str(e)[:150]}")
#         return f"❌ Ошибка перевода: {type(e).__name__}"

 
# async def safe_translate_long(text: str, target_lang: str = "en", timeout: int = 30) -> str:
#     if len(text) <= 4000:
#         return await safe_translate(text, target_lang=target_lang, timeout=timeout)

#     # Разбиваем на чанки по 3500 символов (с запасом под переносы)
#     chunks = [text[i:i+3500] for i in range(0, len(text), 3500)]
    
#     # Переводим все чанки параллельно
#     tasks = [
#         safe_translate(chunk, target_lang=target_lang, timeout=timeout // len(chunks) + 5)
#         for chunk in chunks
#     ]
#     results = await asyncio.gather(*tasks, return_exceptions=True)
    
#     # Собираем результат
#     translated_chunks = []
#     for res in results:
#         if isinstance(res, Exception):
#             return f"❌ Ошибка при переводе части: {type(res).__name__}"
#         translated_chunks.append(res)
    
#     return "\n\n—\n\n".join(translated_chunks)


# async def main() -> None:
#     print("Start!")
#     text = await safe_translate("Python — лучший язык для автоматизации")
#     print(text)



# if __name__ == "__main__":
#     asyncio.run(main())

import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from deep_translator import MyMemoryTranslator
from deep_translator.exceptions import LanguageNotSupportedException
from langdetect import detect, LangDetectException
import re
from typing import List


def recognize_lang(text: str) -> str:
    src: Optional[str] = None

    try:
        detected = detect(text)
        print(f"Detected: {detected} for text: {text[:30]}...")
        if not detected:
            raise LangDetectException("Empty detection result")

        detected = detected.upper()
        if detected == "EN":
            src = "en-US"
        elif detected == "RU":
            src = "ru-RU"
        elif detected == "JA":
            src = "ja-JP"
        elif detected == "FR":
            src = "fr-FR"
        else:
            src = "ru-RU"  # fallback для неизвестных языков
    except LangDetectException:
        src = "en-US"

    if src is None or src.lower() == "auto":
        src = "en-US"

    return src


def translate_one(
    text: str,
    source: str,
    dest: str = "en-US",
    translator: Optional[MyMemoryTranslator] = None,
) -> str:
    
    try:
        if translator is None:
            translator = MyMemoryTranslator(source=source, target="en-US") 
        return translator.translate(text)
    except (LanguageNotSupportedException, Exception) as e:
        print(f"Error translating '{text[:50]}...': {e}")
        return text


def translate_batch_fast(
    texts: List[str],
    source: Optional[str | None] = None,
    dest: str = "en-US",
    chunk_size: int = 5,
    delay: float = 0.5,
    max_workers: int = 8,
) -> List[str]:
    """
    Переводит список текстов максимально быстро:
    - один MyMemoryTranslator на поток,
    - параллельные запросы через ThreadPoolExecutor.
    """
    if not texts:
        return []
    if source is None:
        return []

    def _translate(text: str) -> str:
        results = translate_one(text, source=source, dest=dest)
        return results

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_translate, texts))
        
    # Пауза между чанками (если нужна)
    for i in range(0, len(texts), chunk_size):
        time.sleep(delay)
    return results

def split_text_into_sentences(
    text: str,
    max_chars: int = 100,
) -> List[str]:
    """
    Разбивает большой текст на список предложений.
    Старается не резать посреди предложения.
    Если предложение длиннее max_chars, режет его по символам.
    """
    if not text.strip():
        return []

    # Регулярное выражение для разделения по точкам, восклицательным и вопросительным знакам
    pattern = r"(?<=[.!?])\s+"
    sentences = re.split(pattern, text)

    # Очищаем и фильтруем пустые строки
    sentences = [s.strip() for s in sentences if s.strip()]

    # Дополнительно режем слишком длинные предложения по max_chars
    result: List[str] = []
    for sentence in sentences:
        if len(sentence) <= max_chars:
            result.append(sentence)
        else:
            # режем длинное предложение по max_chars
            while sentence:
                result.append(sentence[:max_chars])
                sentence = sentence[max_chars:]

    return result

def translate_msg(text: str) -> str:
    list_txt = split_text_into_sentences(text, max_chars=100)
    translated = translate_batch_fast(list_txt, source="ru-RU", dest="en-US")

    result_msg = " ".join(translated)
    print(result_msg)
    return result_msg

# if __name__ == "__main__":
