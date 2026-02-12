"""
Менеджер казино/рулетки для бота
"""
import random
import time
from typing import Dict, Tuple
from datetime import datetime, timedelta


class CasinoManager:
    """Управляет играми казино (рулетка)"""

    # Множители и их вероятности
    ROULETTE_OUTCOMES = [
        (0, 40),    # 40% проигрыш
        (2, 35),    # 35% удвоение
        (3, 15),    # 15% утроение
        (5, 7),     # 7% x5
        (10, 3),    # 3% x10
    ]

    # Эмодзи для результатов
    OUTCOME_EMOJI = {
        0: "💥",
        2: "🎉",
        3: "🔥",
        5: "💎",
        10: "🌟"
    }

    # Анимация рулетки
    SPIN_ANIMATION = ["🎰", "🎲", "🃏", "🎯", "🎪"]

    # Настройки
    MIN_BET = 1  # Минимум 1 очко
    MAX_BET = 999999  # Практически без лимита
    COOLDOWN_SECONDS = 30

    def __init__(self):
        """Инициализация менеджера казино"""
        self.last_play: Dict[Tuple[int, int], float] = {}  # (chat_id, user_id) -> timestamp
        self.stats: Dict[Tuple[int, int], Dict] = {}  # Статистика игрока

    def can_play(self, chat_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Проверить, может ли игрок сыграть

        Returns:
            (можно_играть, сообщение_об_ошибке)
        """
        key = (chat_id, user_id)

        if key in self.last_play:
            time_passed = time.time() - self.last_play[key]
            if time_passed < self.COOLDOWN_SECONDS:
                remaining = int(self.COOLDOWN_SECONDS - time_passed)
                return False, f"⏳ Подожди еще {remaining} сек. перед следующей игрой!"

        return True, ""

    def validate_bet(self, bet: int, user_rating: int) -> Tuple[bool, str]:
        """
        Проверить корректность ставки

        Returns:
            (корректна, сообщение_об_ошибке)
        """
        if bet < self.MIN_BET:
            return False, f"⚠️ Минимальная ставка: {self.MIN_BET} очко!"

        if bet > user_rating:
            return False, f"⚠️ У тебя недостаточно очков! Твой рейтинг: {user_rating}"

        return True, ""

    def spin_roulette(self) -> int:
        """
        Крутануть рулетку

        Returns:
            множитель (0, 2, 3, 5, или 10)
        """
        # Создаем взвешенный список
        outcomes = []
        for multiplier, weight in self.ROULETTE_OUTCOMES:
            outcomes.extend([multiplier] * weight)

        return random.choice(outcomes)

    def play(self, chat_id: int, user_id: int, bet: int, user_rating: int) -> Tuple[bool, int, int, str]:
        """
        Сыграть в рулетку

        Args:
            chat_id: ID чата
            user_id: ID пользователя
            bet: Размер ставки
            user_rating: Текущий рейтинг пользователя

        Returns:
            (успех, множитель, выигрыш/проигрыш, сообщение)
        """
        # Проверка кулдауна
        can_play, error = self.can_play(chat_id, user_id)
        if not can_play:
            return False, 0, 0, error

        # Проверка ставки
        valid_bet, error = self.validate_bet(bet, user_rating)
        if not valid_bet:
            return False, 0, 0, error

        # Крутим рулетку
        multiplier = self.spin_roulette()

        # Вычисляем результат
        if multiplier == 0:
            # Проигрыш
            result = -bet
            message = f"💥 <b>Облом!</b> Ты проиграл <b>{bet}</b> очков..."
        else:
            # Выигрыш
            winnings = bet * multiplier - bet  # Чистый выигрыш (без учета ставки)
            result = winnings
            emoji = self.OUTCOME_EMOJI[multiplier]
            message = f"{emoji} <b>Jackpot x{multiplier}!</b> Ты выиграл <b>+{winnings}</b> очков!"

        # Обновляем время последней игры
        key = (chat_id, user_id)
        self.last_play[key] = time.time()

        # Обновляем статистику
        self._update_stats(key, bet, result, multiplier)

        return True, multiplier, result, message

    def _update_stats(self, key: Tuple[int, int], bet: int, result: int, multiplier: int):
        """Обновить статистику игрока"""
        if key not in self.stats:
            self.stats[key] = {
                'total_games': 0,
                'total_bet': 0,
                'total_won': 0,
                'total_lost': 0,
                'biggest_win': 0,
                'biggest_loss': 0,
                'multipliers': {0: 0, 2: 0, 3: 0, 5: 0, 10: 0}
            }

        stats = self.stats[key]
        stats['total_games'] += 1
        stats['total_bet'] += bet
        stats['multipliers'][multiplier] += 1

        if result > 0:
            stats['total_won'] += result
            stats['biggest_win'] = max(stats['biggest_win'], result)
        else:
            stats['total_lost'] += abs(result)
            stats['biggest_loss'] = max(stats['biggest_loss'], abs(result))

    def get_stats(self, chat_id: int, user_id: int) -> Dict:
        """Получить статистику игрока"""
        key = (chat_id, user_id)
        if key not in self.stats:
            return {
                'total_games': 0,
                'total_bet': 0,
                'total_won': 0,
                'total_lost': 0,
                'net_profit': 0,
                'biggest_win': 0,
                'biggest_loss': 0,
                'multipliers': {0: 0, 2: 0, 3: 0, 5: 0, 10: 0}
            }

        stats = self.stats[key].copy()
        stats['net_profit'] = stats['total_won'] - stats['total_lost']
        return stats

    def format_stats(self, stats: Dict) -> str:
        """Форматировать статистику для отображения"""
        if stats['total_games'] == 0:
            return "🎰 <b>Статистика казино</b>\n\nТы еще не играл в рулетку!\nИспользуй: /roulette <ставка>"

        net = stats['net_profit']
        net_emoji = "📈" if net > 0 else "📉" if net < 0 else "➖"
        net_text = f"+{net}" if net > 0 else str(net)

        message = (
            f"🎰 <b>Статистика казино</b>\n\n"
            f"🎲 Всего игр: <b>{stats['total_games']}</b>\n"
            f"💰 Ставок на сумму: <b>{stats['total_bet']}</b> очков\n"
            f"📊 Выиграно: <b>{stats['total_won']}</b> очков\n"
            f"📉 Проиграно: <b>{stats['total_lost']}</b> очков\n"
            f"{net_emoji} Баланс: <b>{net_text}</b> очков\n\n"
            f"🏆 Лучший выигрыш: <b>{stats['biggest_win']}</b> очков\n"
            f"💥 Худший проигрыш: <b>{stats['biggest_loss']}</b> очков\n\n"
            f"<b>Множители:</b>\n"
        )

        for mult in [10, 5, 3, 2, 0]:
            emoji = self.OUTCOME_EMOJI[mult]
            count = stats['multipliers'][mult]
            label = f"x{mult}" if mult > 0 else "Проигрыш"
            message += f"{emoji} {label}: {count} раз\n"

        return message
