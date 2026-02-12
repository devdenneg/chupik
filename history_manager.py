from typing import Dict, List
import json
from datetime import datetime

class HistoryManager:
    """Менеджер истории сообщений для разных чатов"""

    def __init__(self, max_history: int = 40, expiration_minutes: int = 20):
        """
        Args:
            max_history: Максимальное количество сообщений в истории на чат
            expiration_minutes: Время неактивности (в минутах), после которого контекст сбрасывается
        """
        self.chats: Dict[int, List[Dict]] = {}
        self.max_history = max_history
        self.expiration_minutes = expiration_minutes
        self.last_interactions: Dict[int, datetime] = {}
        self.counters: Dict[int, int] = {}
        self.bot_messages_unanswered: Dict[int, int] = {}  # Счетчик игнорируемых сообщений бота
        self.last_bot_message_time: Dict[int, datetime] = {}  # Когда бот последний раз писал

    def add_message(self, chat_id: int, role: str, content: str, sender_name: str = "Assistant"):
        """Добавить сообщение в историю чата"""
        if chat_id not in self.chats:
            self.chats[chat_id] = []
            self.counters[chat_id] = 0

        # Сбрасываем контекст, если прошло слишком много времени
        now = datetime.now()
        if chat_id in self.last_interactions:
            diff = (now - self.last_interactions[chat_id]).total_seconds() / 60
            if diff > self.expiration_minutes:
                self.clear_history(chat_id)

        self.chats[chat_id].append({
            "role": role,
            "content": content,
            "sender": sender_name,
            "timestamp": now.isoformat()
        })
        
        # Обновляем время последнего взаимодействия
        self.last_interactions[chat_id] = now

        # Увеличиваем счетчик только для пользовательских сообщений
        if role == "user":
            self.counters[chat_id] = self.counters.get(chat_id, 0) + 1
            # Если пользователь ответил - значит бот не игнорируется
            if chat_id in self.bot_messages_unanswered:
                self.bot_messages_unanswered[chat_id] = 0
        else:
            # Бот писал сообщение
            self.last_bot_message_time[chat_id] = now
            if chat_id not in self.bot_messages_unanswered:
                self.bot_messages_unanswered[chat_id] = 0

        # Ограничиваем размер истории
        if len(self.chats[chat_id]) > self.max_history:
            self.chats[chat_id] = self.chats[chat_id][-self.max_history:]

    def should_intervene(self, chat_id: int, probability: float = 0.1, min_delay: int = 5) -> bool:
        """
        Проверить, стоит ли боту проявить инициативу и «оживить» беседу.
        Учитывает, игнорируют ли бота - если да, то снижает вероятность.

        Args:
            chat_id: ID чата
            probability: Вероятность вмешательства (0.0 - 1.0)
            min_delay: Минимальное количество сообщений между вмешательствами
        """
        count = self.counters.get(chat_id, 0)

        # Если сообщений мало, не вмешиваемся
        if count < min_delay:
            return False

        # Если бота игнорируют - снижаем вероятность
        import random
        unanswered_count = self.bot_messages_unanswered.get(chat_id, 0)

        # Если игнорируют подряд 3+ сообщений - прекращаем пытаться
        if unanswered_count >= 3:
            return False

        # Снижаем вероятность пропорционально количеству игнорируемых сообщений
        adjusted_probability = probability * (1 - (unanswered_count * 0.3))

        if random.random() < adjusted_probability:
            self.counters[chat_id] = 0  # Сброс счетчика
            self.bot_messages_unanswered[chat_id] = self.bot_messages_unanswered.get(chat_id, 0) + 1
            return True

        return False

    def get_silence_duration(self, chat_id: int) -> float:
        """Получить время молчания в минутах"""
        if chat_id not in self.last_interactions:
            return 0.0
        return (datetime.now() - self.last_interactions[chat_id]).total_seconds() / 60

    def get_history(self, chat_id: int) -> List[Dict]:
        """Получить историю сообщений для чата с проверкой на протухание"""
        if chat_id in self.last_interactions:
            diff = (datetime.now() - self.last_interactions[chat_id]).total_seconds() / 60
            if diff > self.expiration_minutes:
                self.clear_history(chat_id)
        
        return self.chats.get(chat_id, [])

    def can_send_proactive_message(self, chat_id: int, min_interval_seconds: int = 300) -> bool:
        """
        Проверить, прошло ли достаточно времени с последнего проактивного сообщения.
        Предотвращает спам - не позволяет писать чаще чем каждые N секунд.

        Args:
            chat_id: ID чата
            min_interval_seconds: Минимальный интервал между сообщениями (по умолчанию 5 минут = 300 сек)
        """
        if chat_id not in self.last_bot_message_time:
            return True

        time_since_last = (datetime.now() - self.last_bot_message_time[chat_id]).total_seconds()
        return time_since_last >= min_interval_seconds

    def clear_history(self, chat_id: int):
        """Очистить историю чата"""
        if chat_id in self.chats:
            self.chats[chat_id] = []

    def clear_all_history(self):
        """Очистить всю историю"""
        self.chats.clear()
