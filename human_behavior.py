import asyncio
import random
from typing import Tuple

# Карта соседних букв на русской клавиатуре
KEYBOARD_NEIGHBORS = {
    'а': ['ф', 'ы', 'я'],
    'б': ['ю', 'в'],
    'в': ['б', 'г', 'л'],
    'г': ['в', 'д'],
    'д': ['г', 'е', 'л'],
    'е': ['д', 'р', 'н'],
    'ё': ['е'],
    'ж': ['з', 'х'],
    'з': ['ж', 'х', 'с'],
    'и': ['й', 'ш', 'у'],
    'й': ['и', 'ц'],
    'к': ['й', 'л'],
    'л': ['к', 'о', 'д'],
    'м': ['и', 'ь'],
    'н': ['е', 'г', 'й'],
    'о': ['л', 'п', 'р'],
    'п': ['о', 'р', 'а'],
    'р': ['п', 'о', 'е'],
    'с': ['з', 'д', 'ь'],
    'т': ['ы', 'р'],
    'у': ['и', 'й'],
    'ф': ['а', 'в'],
    'х': ['ж', 'з', 'ь'],
    'ц': ['й', 'ы'],
    'ч': ['с', 'ь'],
    'ш': ['и', 'щ'],
    'щ': ['ш', 'з'],
    'ъ': ['п'],
    'ы': ['т', 'у', 'ц'],
    'ь': ['м', 'с', 'х'],
    'э': ['ж'],
    'ю': ['б'],
    'я': ['а', 'ч']
}

FILLER_WORDS = [
    "эм", "ну", "типа", "короче", "в общем", "честно", "слушай",
    "знаешь", "блин", "блинь", "пацан", "ребят", "кстати", "кихи"
]

class HumanBehavior:
    """Естественное человеческое поведение для бота"""

    @staticmethod
    async def typing_pause(context, chat_id: int, text_length: int, variance: bool = True) -> float:
        """
        Отправить индикатор печати и подождать естественное время.
        Возвращает время паузы в секундах.
        """
        # Базовое время: 2 секунды на начало
        base_delay = 2.0
        # 0.02 сек на символ
        char_delay = min(text_length * 0.02, 3.0)
        # Максимум 5 секунд
        total = min(base_delay + char_delay, 5.0)

        # Добавляем вариацию для естественности
        if variance:
            variance_amount = random.uniform(-0.5, 0.5)
            total = max(1.0, total + variance_amount)

        try:
            await context.bot.send_chat_action(chat_id, action="typing")
            await asyncio.sleep(total)
        except Exception:
            # Если ошибка с отправкой action, просто ждем
            await asyncio.sleep(total)

        return total

    @staticmethod
    def add_typos(text: str, typo_chance: float = 0.05) -> Tuple[str, bool]:
        """
        Добавить опечатки в текст.
        Возвращает: (текст_с_опечатками, есть_ли_опечатка_для_исправления)
        """
        words = text.split()
        modified = []
        has_typo = False

        for word in words:
            # Пропускаем короткие слова и числа
            if len(word) <= 3 or word.isdigit() or not any(c.isalpha() for c in word):
                modified.append(word)
                continue

            # Чистое слово (только буквы)
            clean_word = ''.join(c for c in word if c.isalpha())
            if not clean_word:
                modified.append(word)
                continue

            if random.random() < typo_chance:
                typo_type = random.choice(['skip', 'neighbor', 'double'])

                if typo_type == 'skip' and len(clean_word) > 2:
                    # Пропустить случайную букву в середине
                    idx = random.randint(1, len(clean_word) - 2)
                    typo_word = clean_word[:idx] + clean_word[idx+1:]
                    modified.append(typo_word)
                    has_typo = True

                elif typo_type == 'neighbor' and len(clean_word) > 2:
                    # Заменить на соседнюю букву на клавиатуре
                    idx = random.randint(0, len(clean_word) - 1)
                    letter = clean_word[idx].lower()
                    neighbors = KEYBOARD_NEIGHBORS.get(letter, [])
                    if neighbors:
                        neighbor = random.choice(neighbors)
                        typo_word = clean_word[:idx] + neighbor + clean_word[idx+1:]
                        modified.append(typo_word)
                        has_typo = True
                    else:
                        modified.append(word)

                elif typo_type == 'double' and len(clean_word) > 1:
                    # Удвоить случайную букву
                    idx = random.randint(0, len(clean_word) - 1)
                    typo_word = clean_word[:idx+1] + clean_word[idx] + clean_word[idx+1:]
                    modified.append(typo_word)
                    has_typo = True
                else:
                    modified.append(word)
            else:
                modified.append(word)

        return ' '.join(modified), has_typo

    @staticmethod
    def add_filler_words(text: str) -> str:
        """Добавить словесные паразиты в текст"""
        if not text or random.random() > 0.15:
            return text

        sentences = text.split('. ')
        if len(sentences) < 2:
            return text

        # Выбираем случайное предложение для вставки паразита
        idx = random.randint(0, len(sentences) - 2)
        filler = random.choice(FILLER_WORDS)

        sentences[idx] = f"{sentences[idx]}, {filler},"
        return '. '.join(sentences)

    @staticmethod
    def should_fix_typo(has_typo: bool) -> bool:
        """Определить, нужно ли исправлять опечатку (3% шанс)"""
        return has_typo and random.random() < 0.03

    @staticmethod
    def should_add_space_typo() -> bool:
        """1% шанс добавить лишний пробел"""
        return random.random() < 0.01

    @staticmethod
    def split_into_messages(text: str, max_length: int = 200) -> list:
        """
        Разбить длинный текст на несколько сообщений.

        Args:
            text: Текст для разбиения
            max_length: Максимальная длина одного сообщения

        Returns:
            Список сообщений
        """
        if len(text) <= max_length:
            return [text]

        messages = []

        # Сначала пробуем разбить по абзацам
        paragraphs = text.split('\n\n')
        current_message = ""

        for paragraph in paragraphs:
            # Если параграф сам длиннее max_length, разбиваем по предложениям
            if len(paragraph) > max_length:
                sentences = paragraph.replace('! ', '!|').replace('? ', '?|').replace('. ', '.|').split('|')

                for sentence in sentences:
                    if len(current_message) + len(sentence) + 1 <= max_length:
                        current_message += (" " if current_message else "") + sentence
                    else:
                        if current_message:
                            messages.append(current_message.strip())
                        current_message = sentence
            else:
                # Проверяем, поместится ли параграф в текущее сообщение
                if len(current_message) + len(paragraph) + 2 <= max_length:
                    current_message += ("\n\n" if current_message else "") + paragraph
                else:
                    if current_message:
                        messages.append(current_message.strip())
                    current_message = paragraph

        # Добавляем последнее сообщение
        if current_message:
            messages.append(current_message.strip())

        return messages if messages else [text]
