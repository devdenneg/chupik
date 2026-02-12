import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, Optional

class MoodManager:
    """Управление персистентным настроением бота"""

    def __init__(self, state_file: str = "mood_state.json"):
        self.state_file = state_file
        self.mood_states = self._load_state()
        self.last_decay = datetime.now()

    def _load_state(self) -> Dict:
        """Загрузить состояние настроения из файла"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_state(self):
        """Сохранить состояние настроения в файл"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.mood_states, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving mood state: {e}")

    def get_or_create_mood(self, chat_id: int) -> Dict:
        """Получить или создать настроение для чата"""
        chat_key = str(chat_id)
        if chat_key not in self.mood_states:
            self.mood_states[chat_key] = {
                "mood_score": 0,
                "energy": 5,
                "last_update": datetime.now().isoformat(),
                "messages_count": 0
            }
            self._save_state()
        return self.mood_states[chat_key]

    def update_mood(self, chat_id: int, sentiment: Optional[str], decay: bool = True):
        """Обновить настроение на основе сентимента"""
        mood = self.get_or_create_mood(chat_id)

        # Применить decay если нужно
        if decay:
            self._apply_decay(chat_id)

        # Изменить настроение на основе сентимента
        if sentiment == 'joy':
            mood['mood_score'] = min(mood['mood_score'] + 1, 10)
            mood['energy'] = min(mood['energy'] + 0.5, 10)
        elif sentiment == 'sadness':
            mood['mood_score'] = max(mood['mood_score'] - 1, -10)
            mood['energy'] = max(mood['energy'] - 0.5, 0)
        elif sentiment == 'anger':
            mood['mood_score'] = max(mood['mood_score'] - 0.5, -10)
            mood['energy'] = min(mood['energy'] + 1, 10)  # Раздражение даёт энергию

        mood['last_update'] = datetime.now().isoformat()
        mood['messages_count'] = mood.get('messages_count', 0) + 1

        # Усталость после 50 сообщений
        if mood['messages_count'] >= 50:
            mood['energy'] = max(mood['energy'] - 1, 0)
            mood['messages_count'] = 0

        self._save_state()

    def _apply_decay(self, chat_id: int):
        """Применить затухание настроения к нейтралу"""
        mood = self.get_or_create_mood(chat_id)

        last_update = datetime.fromisoformat(mood['last_update'])
        minutes_passed = (datetime.now() - last_update).total_seconds() / 60

        # Каждые 5 минут: -0.5 к абсолютному значению (стремится к 0)
        decay_amount = (minutes_passed / 5) * 0.5

        if mood['mood_score'] > 0:
            mood['mood_score'] = max(mood['mood_score'] - decay_amount, 0)
        elif mood['mood_score'] < 0:
            mood['mood_score'] = min(mood['mood_score'] + decay_amount, 0)

        # Энергия восстанавливается за 30 минут
        if mood['energy'] < 5:
            mood['energy'] = min(mood['energy'] + (minutes_passed / 30) * 5, 5)

        self._save_state()

    def get_mood_category(self, chat_id: int) -> str:
        """Получить категорию настроения"""
        mood = self.get_or_create_mood(chat_id)
        score = mood['mood_score']

        if score >= 6:
            return "очень_радостное"
        elif score >= 2:
            return "радостное"
        elif score >= -1 and score <= 1:
            return "нейтральное"
        elif score >= -5:
            return "грустное"
        else:
            return "очень_грустное"

    def get_mood_prompt_context(self, chat_id: int) -> str:
        """Получить текст для добавления в промпт GLM"""
        mood = self.get_or_create_mood(chat_id)
        category = self.get_mood_category(chat_id)

        mood_descriptions = {
            "очень_радостное": "Ты в отличном настроении! Много эмодзи, шуток, жизнеутверждающий позитив. Веди себя гиперактивно и весело.",
            "радостное": "Ты в хорошем настроении. Добавляй эмодзи, будь дружелюбнее и позитивнее обычного.",
            "нейтральное": "Твое обычное настроение. Веди себя как всегда - дружелюбно но без лишних эмоций.",
            "грустное": "Ты немного грусти. Будь более сочувствующим, добавляй поддержки в ответы. Меньше шуток.",
            "очень_грустное": "Ты подавлен и грустен. Очень спокойный, сочувствующий тон. Предлагай поддержку и понимание."
        }

        energy_level = "высокий" if mood['energy'] > 7 else "средний" if mood['energy'] > 3 else "низкий"

        context = f"\n📊 КОНТЕКСТ НАСТРОЕНИЯ:\n"
        context += f"Текущее настроение: {category.replace('_', ' ')}\n"
        context += f"Уровень энергии: {energy_level}\n"
        context += f"Инструкция: {mood_descriptions[category]}\n"

        return context

    def get_mood_info(self, chat_id: int) -> Dict:
        """Получить полную информацию о настроении"""
        mood = self.get_or_create_mood(chat_id)
        return {
            "score": mood['mood_score'],
            "energy": mood['energy'],
            "category": self.get_mood_category(chat_id),
            "last_update": mood['last_update']
        }
