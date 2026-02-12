"""
Система достижений (ачивок) для пользователей
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Set


class AchievementsManager:
    """Управляет достижениями пользователей"""

    # Определение всех возможных ачивок
    ACHIEVEMENTS = {
        "first_points": {
            "name": "🎯 Первый шаг",
            "description": "Получить первые очки рейтинга",
            "icon": "🎯"
        },
        "ten_points": {
            "name": "⭐ Горячая звезда",
            "description": "Набрать 10 очков рейтинга",
            "icon": "⭐"
        },
        "fifty_points": {
            "name": "🔥 Огненный",
            "description": "Набрать 50 очков рейтинга",
            "icon": "🔥"
        },
        "hundred_points": {
            "name": "💫 Сотник",
            "description": "Набрать 100 очков рейтинга",
            "icon": "💫"
        },
        "five_hundred_points": {
            "name": "👑 Король",
            "description": "Набрать 500 очков рейтинга",
            "icon": "👑"
        },
        "level_5": {
            "name": "📈 Уровень 5",
            "description": "Достичь 5-го уровня",
            "icon": "📈"
        },
        "level_10": {
            "name": "🏆 Гений",
            "description": "Достичь 10-го уровня",
            "icon": "🏆"
        },
        "hundred_messages": {
            "name": "💬 Болтун",
            "description": "Написать 100 сообщений в одном чате",
            "icon": "💬"
        },
        "five_excellent": {
            "name": "✨ Идеальный",
            "description": "Получить 5 оценок 'отличное сообщение'",
            "icon": "✨"
        },
        "ten_excellent": {
            "name": "🌟 Мастер слова",
            "description": "Получить 10 оценок 'отличное сообщение'",
            "icon": "🌟"
        },
        "twenty_excellent": {
            "name": "💎 Легенда",
            "description": "Получить 20 оценок 'отличное сообщение'",
            "icon": "💎"
        },
        "early_bird": {
            "name": "🌅 Ранняя пташка",
            "description": "Написать сообщение между 5 и 7 утра",
            "icon": "🌅"
        },
        "night_owl": {
            "name": "🌙 Ночная сова",
            "description": "Написать сообщение между 23 и 5 утра",
            "icon": "🌙"
        },
    }

    def __init__(self, achievements_file: str = "achievements.json"):
        """
        Args:
            achievements_file: Путь к файлу со статистикой ачивок
        """
        self.achievements_file = achievements_file
        # chat_id -> {user_id -> {achievement_id -> {'unlocked_at': timestamp}}}
        self.achievements: Dict[int, Dict[int, Dict[str, Dict]]] = {}
        self.load_achievements()

    def load_achievements(self):
        """Загрузить ачивки из файла"""
        if os.path.exists(self.achievements_file):
            try:
                with open(self.achievements_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.achievements = {int(chat_id): {int(user_id): user_ach
                                                       for user_id, user_ach in chat.items()}
                                        for chat_id, chat in data.items()}
            except Exception as e:
                print(f"Error loading achievements: {e}")
                self.achievements = {}
        else:
            self.achievements = {}

    def save_achievements(self):
        """Сохранить ачивки в файл"""
        try:
            data = {str(chat_id): {str(user_id): user_ach for user_id, user_ach in chat.items()}
                   for chat_id, chat in self.achievements.items()}
            with open(self.achievements_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving achievements: {e}")

    def unlock_achievement(self, chat_id: int, user_id: int, achievement_id: str) -> bool:
        """
        Разблокировать ачивку для пользователя.
        Returns: True если ачивка была разблокирована, False если уже была разблокирована
        """
        if achievement_id not in self.ACHIEVEMENTS:
            return False

        if chat_id not in self.achievements:
            self.achievements[chat_id] = {}

        if user_id not in self.achievements[chat_id]:
            self.achievements[chat_id][user_id] = {}

        # Если ачивка уже разблокирована, не добавляем еще раз
        if achievement_id in self.achievements[chat_id][user_id]:
            return False

        self.achievements[chat_id][user_id][achievement_id] = {
            "unlocked_at": datetime.now().isoformat()
        }
        self.save_achievements()
        return True

    def get_user_achievements(self, chat_id: int, user_id: int) -> List[Dict]:
        """Получить все ачивки пользователя"""
        if chat_id not in self.achievements or user_id not in self.achievements[chat_id]:
            return []

        achievements_list = []
        for ach_id in self.achievements[chat_id][user_id]:
            if ach_id in self.ACHIEVEMENTS:
                ach_data = self.ACHIEVEMENTS[ach_id].copy()
                ach_data['id'] = ach_id
                unlocked_at = self.achievements[chat_id][user_id][ach_id].get('unlocked_at', '')
                ach_data['unlocked_at'] = unlocked_at
                achievements_list.append(ach_data)

        return achievements_list

    def get_achievement_count(self, chat_id: int, user_id: int) -> int:
        """Получить количество ачивок пользователя"""
        return len(self.get_user_achievements(chat_id, user_id))

    def has_achievement(self, chat_id: int, user_id: int, achievement_id: str) -> bool:
        """Проверить, есть ли у пользователя ачивка"""
        if chat_id not in self.achievements or user_id not in self.achievements[chat_id]:
            return False
        return achievement_id in self.achievements[chat_id][user_id]

    def get_all_achievements_info(self) -> Dict:
        """Получить информацию о всех возможных ачивках"""
        return self.ACHIEVEMENTS
