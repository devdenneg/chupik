"""
Ежедневная статистика по сообщениям и рейтингу
"""
import json
import os
from datetime import datetime
from typing import Dict, List


class DailyStatsManager:
    """Управляет ежедневной статистикой чатов"""

    def __init__(self, stats_file: str = "daily_stats.json"):
        """
        Args:
            stats_file: Путь к файлу со статистикой
        """
        self.stats_file = stats_file
        self.stats: Dict[int, Dict] = {}  # chat_id -> {date: stats_data}
        self.load_stats()

    def load_stats(self):
        """Загрузить статистику из файла"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Преобразуем строковые ключи в int
                    self.stats = {int(chat_id): chat_stats for chat_id, chat_stats in data.items()}
            except Exception as e:
                print(f"Error loading daily stats: {e}")
                self.stats = {}
        else:
            self.stats = {}

    def save_stats(self):
        """Сохранить статистику в файл"""
        try:
            data = {str(chat_id): chat_stats for chat_id, chat_stats in self.stats.items()}
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving daily stats: {e}")

    def get_today_key(self) -> str:
        """Получить ключ дня в формате YYYY-MM-DD"""
        return datetime.now().strftime("%Y-%m-%d")

    def add_message(self, chat_id: int):
        """Добавить сообщение в статистику дня"""
        if chat_id not in self.stats:
            self.stats[chat_id] = {}

        today = self.get_today_key()
        if today not in self.stats[chat_id]:
            self.stats[chat_id][today] = {
                "messages": 0,
                "rating_points": 0,
                "manual_grant_points": 0,
                "date": today
            }

        self.stats[chat_id][today]["messages"] += 1
        self.save_stats()

    def add_rating_points(self, chat_id: int, points: int):
        """Добавить очки рейтинга в статистику дня"""
        if chat_id not in self.stats:
            self.stats[chat_id] = {}

        today = self.get_today_key()
        if today not in self.stats[chat_id]:
            self.stats[chat_id][today] = {
                "messages": 0,
                "rating_points": 0,
                "date": today
            }

        self.stats[chat_id][today]["rating_points"] += points
        self.save_stats()

    def get_today_stats(self, chat_id: int) -> Dict:
        """Получить статистику за сегодня"""
        if chat_id not in self.stats:
            return {"messages": 0, "rating_points": 0}

        today = self.get_today_key()
        if today not in self.stats[chat_id]:
            return {"messages": 0, "rating_points": 0}

        return self.stats[chat_id][today]

    def add_manual_grant_points(self, chat_id: int, points: int):
        """Добавить ручно начисленные очки в статистику дня"""
        if chat_id not in self.stats:
            self.stats[chat_id] = {}

        today = self.get_today_key()
        if today not in self.stats[chat_id]:
            self.stats[chat_id][today] = {
                "messages": 0,
                "rating_points": 0,
                "manual_grant_points": 0,
                "date": today
            }

        self.stats[chat_id][today]["manual_grant_points"] += points
        self.save_stats()

    def get_today_manual_grants(self, chat_id: int) -> int:
        """Получить количество ручно начисленных очков за сегодня"""
        if chat_id not in self.stats:
            return 0

        today = self.get_today_key()
        if today not in self.stats[chat_id]:
            return 0

        return self.stats[chat_id][today].get("manual_grant_points", 0)

    def reset_today_stats(self, chat_id: int):
        """Сбросить статистику за сегодня (после отправки)"""
        if chat_id in self.stats:
            today = self.get_today_key()
            if today in self.stats[chat_id]:
                self.stats[chat_id][today] = {
                    "messages": 0,
                    "rating_points": 0,
                    "manual_grant_points": 0,
                    "date": today
                }
                self.save_stats()
