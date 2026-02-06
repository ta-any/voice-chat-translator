import unittest
from src.services.translator import translate_one, translate_batch_safe

base_tests = [
    # английский
    "Hello, how are you?",
    "I love programming in Python.",
    "Today is a great day for work.",
    # русский
    "Привет! Как твои дела?",
    "Солнце уже поднялось выше, разогнав последние клочья тумана.",
    "Мне нужно перевести длинный текст на английский.",
    # французский
    "Bonjour! Comment ça va?",
    "Aujourd'hui est une excellente journée pour travailler.",
    "Je dois traduire un long texte en anglais.",
    # японский
    "こんにちは！お元気ですか？",
    "今日は仕事に最適な日です。",
    "長いテキストを英語に翻訳する必要があります。",
]


edge_tests = [
    # пустая строка
    "",
    # только пробелы
    "   ",
    # один символ
    "a",
    "あ",
    "А",
    # очень длинный текст
    "Солнце уже поднялось выше, разогнав последние клочья тумана. "
    "На горизонте показалось первое солнце, и мир озарился мягким светом. "
    "Это был прекрасный момент для начала нового дня.",
    # текст без пробелов
    "Привет!Кактвоидела?",
    "Hello,howareyou?",
    # смесь языков
    "Привет! Hello! Bonjour! こんにちは！",
    # спецсимволы и знаки препинания
    "Привет! Как твои дела?..!@#$%^&*()",
    "Hello, how are you?..!@#$%^&*()",
]


lang_tests = [
    # английский
    "Hello, how are you?",
    # русский
    "Привет! Как твои дела?",
    # французский
    "Bonjour! Comment ça va?",
    # японский
    "こんにちは！お元気ですか？",
    # смесь, где langdetect может ошибиться
    "Привет! Hello! Bonjour!",
    # текст, который langdetect может не распознать
    "1234567890",
    "!@#$%^&*()",
]


error_tests = [
    # строка, которая может вызвать ошибку у MyMemoryTranslator
    "A" * 5000,  # очень длинная строка
    # текст с символами, которые могут сломать запрос
    "Привет! Как твои дела? \n\t\r",
    # текст, который может вызвать ошибку
    "Привет! Как твои дела? <script>alert('test')</script>",
]


batch_tests = [
    # пустой список
    [],
    # один элемент
    ["Привет! Как твои дела?"],
    # несколько элементов
    [
        "Hello, how are you?",
        "Привет! Как твои дела?",
        "Bonjour! Comment ça va?",
        "こんにちは！お元気ですか？",
    ],
    # список с пустыми строками
    ["", "Привет! Как твои дела?", ""],
]


class TestTranslator(unittest.TestCase):
    def test_base_cases(self):
        for text in base_tests:
            result = translate_one(text, dest="en-US")
            self.assertIsInstance(result, str)
            self.assertNotEqual(result, "")  # хотя бы не пустая строка

    def test_edge_cases(self):
        for text in edge_tests:
            result = translate_one(text, dest="en-US")
            self.assertIsInstance(result, str)

    def test_lang_detection(self):
        for text in lang_tests:
            result = translate_one(text, dest="en-US")
            self.assertIsInstance(result, str)

    def test_error_handling(self):
        for text in error_tests:
            result = translate_one(text, dest="en-US")
            self.assertIsInstance(result, str)

    def test_batch_safe(self):
        for texts in batch_tests:
            result = translate_batch_safe(texts, dest="en-US", chunk_size=5, delay=0.1)
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), len(texts))


if __name__ == "__main__":
    unittest.main()
