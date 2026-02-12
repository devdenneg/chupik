"""
Менеджер рейтинга пользователей в чатах
"""
import json
import os
from typing import Dict, List
from datetime import datetime


class RatingManager:
    """Управляет рейтингом пользователей в разных чатах"""

    def __init__(self, ratings_file: str = "ratings.json"):
        """
        Args:
            ratings_file: Путь к файлу с рейтингами
        """
        self.ratings_file = ratings_file
        self.ratings: Dict[int, Dict[int, int]] = {}  # chat_id -> {user_id: rating}
        self.history: Dict[int, Dict[int, List[Dict]]] = {}  # chat_id -> {user_id: [history_items]}
        self.load_ratings()

    def load_ratings(self):
        """Загрузить рейтинги из файла"""
        if os.path.exists(self.ratings_file):
            try:
                with open(self.ratings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Преобразуем строковые ключи в int для ratings
                    self.ratings = {int(chat_id): {int(user_id): rating for user_id, rating in users.items()}
                                   for chat_id, users in data.get('ratings', {}).items()}
                    # История - это список для каждого пользователя в каждом чате
                    self.history = {int(chat_id): {int(user_id): hist_list for user_id, hist_list in users.items()}
                                   for chat_id, users in data.get('history', {}).items()}
            except Exception as e:
                print(f"Error loading ratings: {e}")
                self.ratings = {}
                self.history = {}
        else:
            self.ratings = {}
            self.history = {}

    def save_ratings(self):
        """Сохранить рейтинги в файл"""
        try:
            data = {
                'ratings': {str(chat_id): {str(user_id): rating for user_id, rating in users.items()}
                           for chat_id, users in self.ratings.items()},
                'history': {str(chat_id): {str(user_id): hist for user_id, hist in users.items()}
                           for chat_id, users in self.history.items()}
            }
            with open(self.ratings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving ratings: {e}")

    def add_rating(self, chat_id: int, user_id: int, username: str, points: int = 1, reason: str = ""):
        """
        Добавить рейтинг пользователю

        Args:
            chat_id: ID чата
            user_id: ID пользователя
            username: Имя пользователя
            points: Количество очков (по умолчанию 1)
            reason: Причина добавления рейтинга
        """
        if chat_id not in self.ratings:
            self.ratings[chat_id] = {}
            self.history[chat_id] = {}

        if user_id not in self.ratings[chat_id]:
            self.ratings[chat_id][user_id] = 0
            self.history[chat_id][user_id] = []

        old_rating = self.ratings[chat_id][user_id]
        self.ratings[chat_id][user_id] += points
        new_rating = self.ratings[chat_id][user_id]

        self.history[chat_id][user_id].append({
            "timestamp": datetime.now().isoformat(),
            "points": points,
            "reason": reason,
            "username": username
        })

        self.save_ratings()
        print(f"[RATING_MANAGER] {username} (user_id={user_id}, chat_id={chat_id}): {old_rating} + {points} = {new_rating} points. Reason: {reason}")

    def get_user_rating(self, chat_id: int, user_id: int) -> int:
        """Получить рейтинг пользователя в чате"""
        if chat_id not in self.ratings:
            return 0
        return self.ratings[chat_id].get(user_id, 0)

    def get_top_users(self, chat_id: int, limit: int = 10) -> List[tuple]:
        """
        Получить топ пользователей по рейтингу

        Returns: Список (user_id, rating, last_known_username)
        """
        if chat_id not in self.ratings:
            return []

        users = []
        for user_id, rating in self.ratings[chat_id].items():
            if rating > 0:
                # Получаем последнее известное имя
                username = "Unknown"
                if chat_id in self.history and user_id in self.history[chat_id]:
                    if self.history[chat_id][user_id]:
                        username = self.history[chat_id][user_id][-1].get('username', 'Unknown')
                users.append((user_id, rating, username))

        # Сортируем по рейтингу (убывание)
        users.sort(key=lambda x: x[1], reverse=True)
        return users[:limit]

    def get_chat_stats(self, chat_id: int) -> Dict:
        """Получить статистику рейтинга чата"""
        if chat_id not in self.ratings:
            return {
                'total_users': 0,
                'total_points': 0,
                'top_user': None,
                'average_rating': 0
            }

        ratings = self.ratings[chat_id]
        total_users = len([r for r in ratings.values() if r > 0])
        total_points = sum([r for r in ratings.values() if r > 0])
        average_rating = total_points / total_users if total_users > 0 else 0

        top_user = None
        if ratings:
            top_user_id = max(ratings.items(), key=lambda x: x[1])[0]
            top_rating = ratings[top_user_id]
            if chat_id in self.history and top_user_id in self.history[chat_id]:
                if self.history[chat_id][top_user_id]:
                    top_user = self.history[chat_id][top_user_id][-1].get('username', 'Unknown')

        return {
            'total_users': total_users,
            'total_points': total_points,
            'top_user': top_user,
            'top_user_rating': ratings.get(top_user_id, 0) if top_user_id else 0,
            'average_rating': round(average_rating, 2)
        }

    def get_user_history(self, chat_id: int, user_id: int, limit: int = 5) -> List[Dict]:
        """Получить историю рейтинга пользователя"""
        if chat_id not in self.history or user_id not in self.history[chat_id]:
            return []
        return self.history[chat_id][user_id][-limit:]
