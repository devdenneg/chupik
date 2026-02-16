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
    
    # Начальный капитал казино - 10 миллиардов очков!
    INITIAL_BANK = 10_000_000_000
    
    # Вероятности при ручном выборе множителя
    MANUAL_MULTIPLIER_CHANCES = {
        2: 45,   # 45% шанс выиграть x2
        3: 30,   # 30% шанс выиграть x3
        5: 15,   # 15% шанс выиграть x5
        10: 5,   # 5% шанс выиграть x10
    }

    def __init__(self):
        """Инициализация менеджера казино"""
        self.last_play: Dict[Tuple[int, int], float] = {}  # (chat_id, user_id) -> timestamp
        self.stats: Dict[Tuple[int, int], Dict] = {}  # Статистика игрока
        
        # Глобальная статистика казино
        self.global_stats = {
            'total_games': 0,
            'total_players': 0,
            'total_won_by_players': 0,  # Сколько выиграли игроки
            'total_lost_by_players': 0,  # Сколько проиграли игроки (забрало казино)
            'casino_bank': self.INITIAL_BANK,  # Текущая казна казино
        }

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
    
    def spin_with_target(self, target_multiplier: int) -> int:
        """
        Крутануть рулетку с выбранным множителем
        
        Args:
            target_multiplier: Желаемый множитель (2, 3, 5, 10)
            
        Returns:
            множитель (или 0 при проигрыше)
        """
        if target_multiplier not in self.MANUAL_MULTIPLIER_CHANCES:
            return 0
        
        chance = self.MANUAL_MULTIPLIER_CHANCES[target_multiplier]
        roll = random.randint(1, 100)
        
        return target_multiplier if roll <= chance else 0

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
        
        # Обновляем глобальную статистику
        self._update_global_stats(result)

        return True, multiplier, result, message
    
    def play_with_multiplier(self, chat_id: int, user_id: int, bet: int, user_rating: int, target_multiplier: int) -> Tuple[bool, int, int, str]:
        """
        Сыграть в рулетку с выбранным множителем
        
        Args:
            chat_id: ID чата
            user_id: ID пользователя
            bet: Размер ставки
            user_rating: Текущий рейтинг пользователя
            target_multiplier: Желаемый множитель (2, 3, 5, 10)
        
        Returns:
            (успех, множитель, выигрыш/проигрыш, сообщение)
        """
        # Проверка множителя
        if target_multiplier not in self.MANUAL_MULTIPLIER_CHANCES:
            return False, 0, 0, f"⚠️ Недопустимый множитель! Доступны: 2, 3, 5, 10"
        
        # Проверка кулдауна
        can_play, error = self.can_play(chat_id, user_id)
        if not can_play:
            return False, 0, 0, error
        
        # Проверка ставки
        valid_bet, error = self.validate_bet(bet, user_rating)
        if not valid_bet:
            return False, 0, 0, error
        
        # Крутим рулетку с целевым множителем
        multiplier = self.spin_with_target(target_multiplier)
        
        # Вычисляем результат
        if multiplier == 0:
            # Проигрыш
            result = -bet
            chance = self.MANUAL_MULTIPLIER_CHANCES[target_multiplier]
            message = f"💥 <b>Облом!</b> Ты проиграл <b>{bet}</b> очков... (Шанс был {chance}%)"
        else:
            # Выигрыш
            winnings = bet * multiplier - bet
            result = winnings
            emoji = self.OUTCOME_EMOJI[multiplier]
            chance = self.MANUAL_MULTIPLIER_CHANCES[target_multiplier]
            message = f"{emoji} <b>Jackpot x{multiplier}!</b> Ты выиграл <b>+{winnings}</b> очков! (Шанс был {chance}%)"
        
        # Обновляем время последней игры
        key = (chat_id, user_id)
        self.last_play[key] = time.time()
        
        # Обновляем статистику
        self._update_stats(key, bet, result, multiplier)
        
        # Обновляем глобальную статистику
        self._update_global_stats(result)
        
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
    
    def _update_global_stats(self, result: int):
        """Обновить глобальную статистику казино"""
        self.global_stats['total_games'] += 1
        self.global_stats['total_players'] = len(self.stats)
        
        if result > 0:
            # Игрок выиграл - казино потеряло
            self.global_stats['total_won_by_players'] += result
            self.global_stats['casino_bank'] -= result
        else:
            # Игрок проиграл - казино забрало
            self.global_stats['total_lost_by_players'] += abs(result)
            self.global_stats['casino_bank'] += abs(result)

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
    
    def get_global_stats(self) -> Dict:
        """Получить глобальную статистику казино"""
        # Вычисляем общий баланс игроков
        total_players_balance = self.global_stats['total_won_by_players'] - self.global_stats['total_lost_by_players']
        
        return {
            'total_games': self.global_stats['total_games'],
            'total_players': self.global_stats['total_players'],
            'total_won_by_players': self.global_stats['total_won_by_players'],
            'total_lost_by_players': self.global_stats['total_lost_by_players'],
            'players_balance': total_players_balance,
            'casino_bank': self.global_stats['casino_bank'],
            'initial_bank': self.INITIAL_BANK,
        }
    
    def format_global_stats(self) -> str:
        """Форматировать глобальную статистику для отображения"""
        stats = self.get_global_stats()
        
        if stats['total_games'] == 0:
            return (
                f"🎰 <b>Общая статистика казино</b>\n\n"
                f"🏛️ Казна казино: <b>{stats['casino_bank']:,}</b> очков\n"
                f"🎯 Цель: забрать все 10 миллиардов!\n\n"
                f"Еще никто не играл. Будь первым!"
            )
        
        # Эмодзи для баланса
        players_balance = stats['players_balance']
        balance_emoji = "📈" if players_balance > 0 else "📉" if players_balance < 0 else "➡️"
        balance_text = f"+{players_balance:,}" if players_balance > 0 else f"{players_balance:,}"
        
        # Процент ограбления казино
        stolen_amount = stats['initial_bank'] - stats['casino_bank']
        stolen_percent = (stolen_amount / stats['initial_bank']) * 100
        
        message = (
            f"🎰 <b>Общая статистика казино</b>\n\n"
            f"👥 Игроков: <b>{stats['total_players']}</b>\n"
            f"🎲 Всего игр: <b>{stats['total_games']}</b>\n\n"
            f"🏛️ <b>Казна казино:</b> <b>{stats['casino_bank']:,}</b> очков\n"
            f"💰 Начальный капитал: {stats['initial_bank']:,} очков\n"
            f"🎯 Украдено игроками: <b>{stolen_amount:,}</b> ({stolen_percent:.2f}%)\n\n"
            f"📊 <b>Баланс игроков:</b>\n"
            f"📈 Выиграно: <b>{stats['total_won_by_players']:,}</b> очков\n"
            f"📉 Проиграно: <b>{stats['total_lost_by_players']:,}</b> очков\n"
            f"{balance_emoji} Чистый баланс: <b>{balance_text}</b> очков\n\n"
        )
        
        # Добавляем мотивационное сообщение
        if stolen_percent < 1:
            message += "🔥 Казино почти нетронуто! Покажите им, кто здесь хозяин!"
        elif stolen_percent < 10:
            message += "👊 Неплохое начало! Продолжайте в том же духе!"
        elif stolen_percent < 50:
            message += "🚀 Отличный прогресс! Казино уже тревожится!"
        elif stolen_percent < 90:
            message += "🔥 Вы почти ограбили казино! Еще немного!"
        else:
            message += "🏆 Казино почти разорено! Вы - легенды!"
        
        return message
