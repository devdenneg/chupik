"""
Система уровней пользователей
"""
import json
import os
from typing import Dict, Tuple


class LevelsManager:
    """Управляет уровнями пользователей на основе рейтинга"""

    # Таблица опыта: уровень -> требуемое количество очков
    LEVEL_THRESHOLDS = {
        1: 0,
        2: 10,
        3: 25,
        4: 50,
        5: 100,
        6: 150,
        7: 250,
        8: 400,
        9: 600,
        10: 1000,
        11: 1500,
        12: 2500,
    }

    LEVEL_NAMES = {
        1: "🌱 Новичок",
        2: "📈 Растущая звезда",
        3: "⭐ Талант",
        4: "🔥 Звезда",
        5: "💫 Яркая звезда",
        6: "🏅 Мастер",
        7: "👑 Легенда",
        8: "🌟 Супер легенда",
        9: "💎 Драгоценность",
        10: "🚀 Гений",
        11: "✨ Бог общения",
        12: "♾️ Бесконечная легенда",
    }

    def __init__(self):
        self.levels_cache: Dict[Tuple[int, int], int] = {}  # (chat_id, user_id) -> level

    def get_level_by_rating(self, rating: int) -> int:
        """Получить уровень по количеству очков рейтинга"""
        level = 1
        for lvl in sorted(self.LEVEL_THRESHOLDS.keys(), reverse=True):
            if rating >= self.LEVEL_THRESHOLDS[lvl]:
                level = lvl
                break
        return min(level, max(self.LEVEL_THRESHOLDS.keys()))

    def get_level_info(self, rating: int) -> Dict:
        """Получить полную информацию об уровне"""
        current_level = self.get_level_by_rating(rating)
        next_level = min(current_level + 1, max(self.LEVEL_THRESHOLDS.keys()))

        current_threshold = self.LEVEL_THRESHOLDS[current_level]
        next_threshold = self.LEVEL_THRESHOLDS[next_level]

        progress = rating - current_threshold
        needed = next_threshold - current_threshold
        progress_percent = int((progress / needed) * 100) if needed > 0 else 100

        return {
            "level": current_level,
            "level_name": self.LEVEL_NAMES.get(current_level, f"Уровень {current_level}"),
            "current_rating": rating,
            "current_threshold": current_threshold,
            "next_threshold": next_threshold,
            "progress": progress,
            "needed": needed,
            "progress_percent": progress_percent,
            "next_level_name": self.LEVEL_NAMES.get(next_level, f"Уровень {next_level}"),
        }

    def get_level_progress_bar(self, rating: int, length: int = 10) -> str:
        """Получить прогресс-бар в виде строки"""
        info = self.get_level_info(rating)
        filled = int((info["progress_percent"] / 100) * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}] {info['progress_percent']}%"

    def check_level_up(self, old_rating: int, new_rating: int) -> Tuple[bool, int, int]:
        """
        Проверить, произошел ли уровень вверх.
        Returns: (level_up_happened, old_level, new_level)
        """
        old_level = self.get_level_by_rating(old_rating)
        new_level = self.get_level_by_rating(new_rating)

        if new_level > old_level:
            return True, old_level, new_level
        return False, old_level, new_level
