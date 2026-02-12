import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

class MembersManager:
    """Менеджер для отслеживания активности участников"""

    def __init__(self, data_file: str = "members_data.json"):
        self.data_file = data_file
        self.members: Dict[int, Dict] = {}
        self.messages: List[Dict] = []
        self.load_data()

    def load_data(self):
        """Загрузка данных из файла"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.members = data.get('members', {})
                    self.messages = data.get('messages', [])
            except Exception as e:
                print(f"Ошибка загрузки данных: {e}")
                self.members = {}
                self.messages = []

    def save_data(self):
        """Сохранение данных в файл"""
        try:
            data = {
                'members': self.members,
                'messages': self.messages
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")

    def add_member(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Добавить или обновить информацию об участнике"""
        if user_id not in self.members:
            self.members[user_id] = {
                'id': user_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'message_count': 0,
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat()
            }
        else:
            # Обновляем информацию если она изменилась
            if username:
                self.members[user_id]['username'] = username
            if first_name:
                self.members[user_id]['first_name'] = first_name
            if last_name:
                self.members[user_id]['last_name'] = last_name
            self.members[user_id]['last_seen'] = datetime.now().isoformat()

        self.save_data()

    def record_message(self, user_id: int, chat_id: int, message_text: str, username: str = None):
        """Записать сообщение от участника"""
        # Обновляем счетчик сообщений
        if user_id in self.members:
            self.members[user_id]['message_count'] += 1
            self.members[user_id]['last_seen'] = datetime.now().isoformat()

        # Сохраняем сообщение
        message_data = {
            'user_id': user_id,
            'username': username,
            'chat_id': chat_id,
            'text': message_text[:500],  # Ограничиваем длину
            'timestamp': datetime.now().isoformat()
        }
        self.messages.append(message_data)

        # Ограничиваем количество сохраненных сообщений (последние 1000)
        if len(self.messages) > 1000:
            self.messages = self.messages[-1000:]

        self.save_data()

    def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Получить информацию о пользователе"""
        return self.members.get(user_id)

    def get_chat_stats(self, chat_id: int, days: int = 7) -> Dict:
        """Получить статистику по чату за указанный период"""
        cutoff_date = datetime.now() - timedelta(days=days)

        # Фильтруем сообщения за период
        recent_messages = [
            msg for msg in self.messages
            if msg['chat_id'] == chat_id and
            datetime.fromisoformat(msg['timestamp']) > cutoff_date
        ]

        # Считаем активность пользователей
        user_activity = {}
        for msg in recent_messages:
            user_id = msg['user_id']
            if user_id not in user_activity:
                user_activity[user_id] = {
                    'count': 0,
                    'username': msg.get('username', 'Unknown')
                }
            user_activity[user_id]['count'] += 1

        # Сортируем по активности
        top_users = sorted(
            user_activity.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:10]  # Топ-10

        return {
            'total_messages': len(recent_messages),
            'unique_users': len(user_activity),
            'period_days': days,
            'top_users': top_users
        }

    def get_members_list(self, chat_id: int = None) -> List[Dict]:
        """Получить список участников"""
        if chat_id:
            # Фильтруем по чату
            user_ids = set(msg['user_id'] for msg in self.messages if msg['chat_id'] == chat_id)
            return [self.members[uid] for uid in user_ids if uid in self.members]
        return list(self.members.values())

    def export_to_json(self, filename: str = None) -> str:
        """Экспорт данных в JSON файл"""
        if not filename:
            filename = f"members_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            data = {
                'export_date': datetime.now().isoformat(),
                'members': self.members,
                'messages': self.messages[-100:]  # Последние 100 сообщений
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return filename
        except Exception as e:
            raise Exception(f"Ошибка при экспорте: {e}")

    def export_to_csv(self, filename: str = None) -> str:
        """Экспорт участников в CSV файл"""
        if not filename:
            filename = f"members_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("ID,Username,First Name,Last Name,Messages,First Seen,Last Seen\n")
                for member in self.members.values():
                    f.write(f"{member['id']},{member.get('username', '')},{member.get('first_name', '')},")
                    f.write(f"{member.get('last_name', '')},{member['message_count']},{member['first_seen']},{member['last_seen']}\n")

            return filename
        except Exception as e:
            raise Exception(f"Ошибка при экспорте: {e}")
