import logging
import asyncio
import random
from datetime import datetime
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from config import (
    TELEGRAM_BOT_TOKEN,
    MAX_TOKENS,
    TEMPERATURE,
    ALLOWED_CHAT_IDS,
    GLM_API_KEY,
    GLM_API_URL,
    DEFAULT_MODEL
)
from glm_client import GLMClient
from history_manager import HistoryManager
from members_manager import MembersManager
from knowledge_manager import KnowledgeManager
from smart_ai import SmartLocalAI
from persona import SYSTEM_PERSONA, COMPLEX_MARKERS, SEARCH_MARKERS, FALLBACK_RESPONSES, get_time_context
from settings_manager import SettingsManager
from rating_manager import RatingManager
from daily_stats import DailyStatsManager
from levels_manager import LevelsManager
from achievements_manager import AchievementsManager
from mood_manager import MoodManager
from human_behavior import HumanBehavior
from casino_manager import CasinoManager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация клиентов
glm_client = GLMClient(GLM_API_KEY, GLM_API_URL, DEFAULT_MODEL)
# Храним до 30 сообщений локально, но отправляем в AI только последние 10-12 для экономии токенов
history_manager = HistoryManager(max_history=30, expiration_minutes=60)
members_manager = MembersManager()
knowledge_manager = KnowledgeManager()
smart_ai = SmartLocalAI(knowledge_manager)
settings_manager = SettingsManager()
rating_manager = RatingManager()
daily_stats = DailyStatsManager()
levels_manager = LevelsManager()
achievements_manager = AchievementsManager()
mood_manager = MoodManager()
human_behavior = HumanBehavior()
casino_manager = CasinoManager()


# Система очередей для обработки запросов (чтобы не было багов при множественных запросах)
chat_locks = defaultdict(asyncio.Lock)
chat_queues = defaultdict(asyncio.Queue)

# Хранилище для фоновых задач (напоминания и т.д.), чтобы они не были удалены сборщиком мусора
background_tasks = set()


# Рейтинг-система: каждый пользователь может получить очки независимо
# Нет cooldown - каждое сообщение имеет 25% шанс на рандомное количество очков (1-25)

# Используем персону из файла persona.py
SYSTEM_PROMPT = SYSTEM_PERSONA


def is_chat_allowed(chat_id: int) -> bool:
    """Проверить, разрешен ли чат"""
    if ALLOWED_CHAT_IDS is None:
        return True
    return chat_id in ALLOWED_CHAT_IDS


def get_user_display_name(user) -> str:
    """Получить отображаемое имя пользователя"""
    if user.username:
        return f"@{user.username}"
    elif user.first_name:
        return user.first_name
    else:
        return f"User_{user.id}"


def needs_web_search(text: str) -> bool:
    """Определить, нужен ли веб-поиск для вопроса"""
    text_lower = text.lower()
    for marker in SEARCH_MARKERS:
        if marker in text_lower:
            return True
    return False


async def send_reminder(application, chat_id: int, user_id: int, username: str, seconds: int, reminder_text: str, original_request: str):
    """
    Отправить напоминание через указанное время с AI-генерацией персонализированного сообщения
    """
    try:
        logger.info(f"[REMINDER] Scheduled for {seconds}s, chat={chat_id}, user={username}, text='{reminder_text}'")
        
        # Ждем указанное время
        await asyncio.sleep(seconds)
        
        logger.info(f"[REMINDER] Time elapsed! Generating message for chat {chat_id}")
        
        # Генерируем персонализированное напоминание с помощью AI
        user_name = knowledge_manager.get_user_name(user_id) or username or "друг"
        
        # Формируем промпт для AI
        if reminder_text:
            ai_prompt = f"""Ты - Чупапи, веселый и дружелюбный бот. Пользователь {user_name} попросил напомнить про: "{reminder_text}".

Создай КОРОТКОЕ (1-2 предложения) напоминание в своем стиле:
- Используй эмодзи
- Будь дружелюбным и немного игривым
- Упомяни о чем напомнить
- Не используй слишком много восклицательных знаков

Пример: "Эй, {user_name}! Ты просил напомнить про встречу. Время пришло! 😉"

Твое напоминание:"""
        else:
            ai_prompt = f"""Ты - Чупапи, веселый и дружелюбный бот. Пользователь {user_name} попросил просто напомнить через некоторое время.

Создай КОРОТКОЕ (1-2 предложения) напоминание в своем стиле:
- Используй эмодзи
- Будь дружелюбным и немного игривым
- Напомни что время вышло
- Не используй слишком много восклицательных знаков

Пример: "Привет, {user_name}! Ты просил напомнить - вот и напоминаю! ⏰"

Твое напоминание:"""
        
        try:
            # Генерируем ответ через AI
            ai_response = await glm_client.generate_response(
                prompt=ai_prompt,
                history=[],
                max_tokens=100,
                temperature=0.9
            )
            reminder_message = ai_response.strip()
            logger.info(f"[REMINDER] AI generated: {reminder_message[:50]}...")
        except Exception as e:
            logger.error(f"Error generating AI reminder: {e}")
            # Fallback на простое напоминание
            if reminder_text:
                reminder_message = f"⏰ Эй, {user_name}! Напоминаю про: {reminder_text} 😉"
            else:
                reminder_message = f"⏰ {user_name}, ты просил напомнить - вот и напоминаю! 👋"
            logger.info(f"[REMINDER] Using fallback message")
        
        
        logger.info(f"[REMINDER] Sending to chat {chat_id}...")
        bot = application.bot
        await bot.send_message(
            chat_id=chat_id,
            text=reminder_message
        )
        
        logger.info(f"[REMINDER] ✅ Successfully sent to chat {chat_id} for user {username}")
        
    except Exception as e:
        logger.error(f"[REMINDER] ❌ Error: {e}", exc_info=True)



def is_complex_task(text: str) -> bool:
    """Определить, является ли задача сложной (требует GLM)"""
    text_lower = text.lower()
    
    # 1. Проверка по длине
    if len(text.split()) > 10:
        return True
        
    # 2. Проверка по ключевым словам сложности
    for marker in COMPLEX_MARKERS:
        if marker in text_lower:
            return True
            
    # 3. Если есть код или технические символы
    if any(char in text for char in ['{', '}', 'def ', 'class ', 'import ']):
        return True
        
    return False


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    chat_id = update.effective_chat.id
    user = update.effective_user

    if not is_chat_allowed(chat_id):
        await update.message.reply_text(
            "⛔ Этот бот не настроен для работы в этом чате."
        )
        return

    # Регистрируем пользователя
    if user:
        members_manager.add_member(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

    await update.message.reply_text(
        "🤖 Привет! Я Чупапи - AI-бот на базе GLM 4.6.\n\n"
        "💬 <b>Как обращаться:</b>\n"
        "• В личке: просто напишите сообщение\n"
        "• В группе: напишите \"Чупапи\", \"Чупа\" или \"Чупик\"\n"
        "• Или ответьте на моё сообщение\n"
        "• Или упомяните меня через @username\n\n"
        "📋 <b>Основные команды:</b>\n"
        "/start - Начать работу\n"
        "/help - Показать справку\n"
        "/settings - Настройки (стиль, активность, личность)\n"
        "/clear - Очистить историю диалога\n\n"
        "🧠 <b>Обучение:</b>\n"
        "/learn ключ | информация - Обучить бота\n"
        "/facts - Показать что бот запомнил\n"
        "/forget ключ - Забыть информацию\n"
        "/myinfo - Что бот знает о вас 👤\n\n"
        "👥 <b>Работа с участниками:</b>\n"
        "/members - Список участников\n"
        "/stats - Статистика активности\n"
        "/roast - Подколоть участника 🔥\n\n"
        "💡 Я читаю все сообщения в беседе для контекста, но отвечаю только когда обращаются ко мне!",
        parse_mode='HTML'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    await update.message.reply_text(
        "📚 <b>Справка по боту Чупапи</b>\n\n"
        "<b>🎯 Как я работаю:</b>\n"
        "• Читаю ВСЕ сообщения в беседе (запоминаю контекст)\n"
        "• Отвечаю только когда ко мне обращаются\n"
        "• Иногда оживляю беседу, если долго тишина\n\n"
        "<b>💬 Как обращаться:</b>\n"
        "• В личке: просто напиши сообщение\n"
        "• В группе: \"Чупапи\", \"Чупа\" или \"Чупик\"\n"
        "• Или ответь на моё сообщение\n"
        "• Или упомяни через @username\n\n"
        "<b>⚙️ Основные команды:</b>\n"
        "/start - Начать работу\n"
        "/settings - Настройки (стиль, активность, личность) ⭐\n"
        "/clear - Очистить историю диалога\n\n"
        "<b>🧠 Обучение:</b>\n"
        "/learn ключ | информация - Научить меня чему-то\n"
        "/facts - Показать что я запомнил\n"
        "/forget ключ - Забыть информацию\n"
        "/myinfo - Что я знаю о тебе 👤\n\n"
        "<b>👥 Участники:</b>\n"
        "/members - Список участников\n"
        "/stats [дни] - Статистика активности\n"
        "/roast - Подколоть участника 🔥\n\n"
        "<b>⚠️ Ограничения:</b>\n"
        "Я пока не умею искать в интернете в реальном времени. "
        "Отвечаю на основе своих знаний и контекста беседы.\n\n"
        "<b>Примеры обращения:</b>\n"
        "• Чупапи, сколько будет 2+2?\n"
        "• Чупа, расскажи анекдот\n"
        "• /learn создатель | Денчик",
        parse_mode='HTML'
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистить историю диалога"""
    chat_id = update.effective_chat.id
    history_manager.clear_history(chat_id)
    await update.message.reply_text("🗑 История диалога очищена!")


async def members_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить список участников чата"""
    chat_id = update.effective_chat.id
    chat = update.effective_chat

    await update.message.reply_text("📊 Получаю список участников...")

    try:
        # Получаем участников из чата
        if chat.type == 'private':
            await update.message.reply_text("👤 Это личный чат, только вы и бот!")
            return

        # Пытаемся получить список участников
        members = []

        if chat.type in ['group', 'supergroup']:
            try:
                # Для супергрупп получаем администраторов и участников
                chat_members = await context.bot.get_chat_administrators(chat_id)

                for member in chat_members:
                    user = member.user
                    members_manager.add_member(
                        user_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name
                    )

                    status_icon = "👑" if member.status == 'creator' else "👮"
                    member_info = f"{status_icon} {get_user_display_name(user)}"
                    if member.custom_title:
                        member_info += f" ({member.custom_title})"
                    members.append(member_info)

            except Exception as e:
                logger.error(f"Ошибка при получении администраторов: {e}")

        # Добавляем известных участников из базы данных
        known_members = members_manager.get_members_list(chat_id)
        known_count = len(known_members)

        if isinstance(members, list) and members:
            safe_members = list(members)
            response = f"👥 <b>Администрация чата:</b>\n\n" + "\n".join(safe_members[:20])

            if known_count > len(members):
                response += f"\n\n📊 Всего участников в базе: {known_count}"

            await update.message.reply_text(response, parse_mode='HTML')
        else:
            if known_count > 0:
                response = f"📊 <b>Участники в базе данных:</b> {known_count}\n\n"
                members_to_show = known_members[:10] if isinstance(known_members, list) and known_members else []
                for member_id in members_to_show:
                    response += f"• {get_user_display_name(member_id)}\n"
                await update.message.reply_text(response, parse_mode='HTML')
            else:
                await update.message.reply_text(
                    "📊 База данных пуста. Отправьте сообщения, чтобы я начал отслеживать участников."
                )

    except Exception as e:
        logger.error(f"Ошибка в команде /members: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить информацию о пользователе"""
    message = update.message

    # Проверяем, ответили ли мы на сообщение
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
    elif context.args and len(context.args) > 0:
        # Можно указать username
        username = context.args[0].replace('@', '')
        await message.reply_text("🔍 Поиск по username пока не реализован. Используйте ответ на сообщение.")
        return
    else:
        await message.reply_text(
            "💡 <b>Как использовать:</b> Ответьте на сообщение пользователя и напишите /userinfo",
            parse_mode='HTML'
        )
        return

    user_id = target_user.id
    user_info = members_manager.get_user_info(user_id)

    if not user_info:
        # Создаем запись если её нет
        members_manager.add_member(
            user_id=target_user.id,
            username=target_user.username,
            first_name=target_user.first_name,
            last_name=target_user.last_name
        )
        user_info = members_manager.get_user_info(user_id)

    # Формируем ответ
    response = f"👤 <b>Информация о пользователе</b>\n\n"
    response += f"<b>ID:</b> {user_info['id']}\n"

    if user_info.get('username'):
        response += f"<b>Username:</b> @{user_info['username']}\n"

    if user_info.get('first_name'):
        response += f"<b>Имя:</b> {user_info['first_name']}\n"

    if user_info.get('last_name'):
        response += f"<b>Фамилия:</b> {user_info['last_name']}\n"

    response += f"\n📊 <b>Активность:</b>\n"
    response += f"Сообщений: {user_info['message_count']}\n"
    response += f"Первое сообщение: {user_info['first_seen'][:10]}\n"
    response += f"Последнее сообщение: {user_info['last_seen'][:10]}"

    await message.reply_text(response, parse_mode='HTML')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика активности чата"""
    chat_id = update.effective_chat.id

    # Получаем период
    days = 7
    if context.args and len(context.args) > 0:
        try:
            days = int(context.args[0])
        except ValueError:
            pass

    stats = members_manager.get_chat_stats(chat_id, days)

    response = f"📊 <b>Статистика чата</b> (последние {stats['period_days']} дней)\n\n"
    response += f"💬 Всего сообщений: {stats['total_messages']}\n"
    response += f"👥 Уникальных пользователей: {stats['unique_users']}\n\n"

    if stats['top_users']:
        response += "🏆 <b>Топ активных:</b>\n"

        # Получаем информацию о пользователях
        for i, (user_id, data) in enumerate(stats['top_users'], 1):
            user_info = members_manager.get_user_info(user_id)
            if user_info:
                name = user_info.get('username') or user_info.get('first_name') or f"User_{user_id}"
                response += f"{i}. {name} - {data['count']} сообщ.\n"
            else:
                username = data.get('username', 'Unknown')
                response += f"{i}. {username} - {data['count']} сообщ.\n"

    await update.message.reply_text(response, parse_mode='HTML')


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт данных"""
    chat_id = update.effective_chat.id

    # Определяем формат
    export_format = 'json'
    if context.args and len(context.args) > 0:
        export_format = context.args[0].lower()

    await update.message.reply_text("📦 Подготавливаю экспорт данных...")

    try:
        if export_format == 'csv':
            filename = members_manager.export_to_csv()
        else:
            filename = members_manager.export_to_json()

        # Отправляем файл
        with open(filename, 'rb') as f:
            await update.message.reply_document(
                document=f,
                caption=f"✅ Экспорт данных: {export_format.upper()}\n📁 Файл: {filename}"
            )

    except Exception as e:
        logger.error(f"Ошибка при экспорте: {e}")
        await update.message.reply_text(f"❌ Ошибка при экспорте: {str(e)}")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда поиска - честный ответ о возможностях"""
    message = update.message

    # Проверяем, указан ли поисковый запрос
    if not context.args or len(context.args) == 0:
        await message.reply_text(
            "🔍 <b>О поиске в интернете</b>\n\n"
            "К сожалению, пока что я не умею искать в интернете в реальном времени. 😔\n\n"
            "Я могу ответить только на основе:\n"
            "• Моих базовых знаний (до 2025 года)\n"
            "• Того, что узнал из этой беседы\n"
            "• Информации, которую вы мне рассказали\n\n"
            "💡 <b>Что я могу:</b>\n"
            "• Помочь с вопросами по программированию\n"
            "• Объяснить концепции и идеи\n"
            "• Поболтать и поддержать разговор\n"
            "• Запомнить факты через /learn\n\n"
            "Но для актуальной информации (погода, курсы, новости) лучше обратиться к специализированным сервисам! 🌐",
            parse_mode='HTML'
        )
        return

    # Получаем поисковый запрос
    search_query = ' '.join(context.args)

    await message.reply_text(
        f"🤔 Извини, но я пока не умею искать в интернете!\n\n"
        f"Твой запрос: <b>\"{search_query}\"</b>\n\n"
        f"Я могу ответить только на основе:\n"
        f"• Моих знаний (информация до 2025 года)\n"
        f"• Того, что обсуждалось в этой беседе\n\n"
        f"Для актуальной информации лучше воспользоваться поисковиком! 🌐",
        parse_mode='HTML'
    )


async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обучить бота новой информации"""
    message = update.message
    user = message.from_user

    if not user:
        return

    # Проверяем, указаны ли аргументы
    if not context.args or len(context.args) < 2:
        await message.reply_text(
            "🧠 <b>Как обучить бота:</b>\n\n"
            "Формат: <code>/learn ключевое слово или фраза | информация для запоминания</code>\n\n"
            "<b>Примеры:</b>\n"
            "/learn создатель | Денчик\n"
            "/learn любимая еда | Пицца и суши\n"
            "/learn мой nickname | Суперзвезда\n\n"
            "Разделяйте ключевое слово и информацию символом <code>|</code>",
            parse_mode='HTML'
        )
        return

    # Парсим аргументы
    args = ' '.join(context.args)

    if '|' not in args:
        await message.reply_text(
            "❌ Используйте разделитель <code>|</code> между ключевым словом и информацией.\n\n"
            "Пример: <code>/learn создатель | Денчик</code>",
            parse_mode='HTML'
        )
        return

    parts = args.split('|', 1)
    if len(parts) != 2:
        await message.reply_text("❌ Неверный формат. Используйте: /learn ключевое слово | информация")
        return

    key = parts[0].strip()
    fact = parts[1].strip()

    if not key or not fact:
        await message.reply_text("❌ Ключевое слово и информация не могут быть пустыми.")
        return

    # Добавляем факт
    username = user.username or user.first_name or f"User_{user.id}"
    success = knowledge_manager.add_fact(key, fact, user.id, username)

    if success:
        await message.reply_text(
            f"✅ <b>Запомнил!</b>\n\n"
            f"<b>Ключ:</b> {key}\n"
            f"<b>Информация:</b> {fact}\n\n"
            f"Теперь я буду помнить это! 🧠",
            parse_mode='HTML'
        )
    else:
        await message.reply_text(
            f"⚠️ Такая информация уже есть для ключа <b>{key}</b>.",
            parse_mode='HTML'
        )


async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Забыть информацию"""
    message = update.message
    user = message.from_user

    if not user:
        return

    if not context.args or len(context.args) == 0:
        await message.reply_text(
            "🗑️ <b>Как забыть:</b>\n\n"
            "Напишите: <code>/forget ключевое слово</code>\n\n"
            "<b>Пример:</b> <code>/forget создатель</code>\n\n"
            "Вы можете удалить только информацию, которую добавили вы сами.",
            parse_mode='HTML'
        )
        return

    key = ' '.join(context.args)

    # Пытаемся удалить
    success = knowledge_manager.delete_fact(key, user.id)

    if success:
        await message.reply_text(
            f"🗑️ Забыл информацию по ключу: <b>{key}</b>",
            parse_mode='HTML'
        )
    else:
        await message.reply_text(
            f"❌ Не удалось найти или удалить информацию по ключу <b>{key}</b>.\n\n"
            f"Вы можете удалять только ту информацию, которую добавили сами.",
            parse_mode='HTML'
        )


async def facts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику и последние сохранённые факты"""
    message = update.message

    facts = knowledge_manager.get_all_facts()
    stats = knowledge_manager.get_stats()

    if not facts:
        await message.reply_text(
            "📚 Я пока ничего не запомнил. Начните общаться - я запомню всё!",
            parse_mode='HTML'
        )
        return

    # Формируем ответ со статистикой
    response = f"📚 <b>Моя память:</b>\n\n"
    response += f"📊 <b>Статистика:</b>\n"
    response += f"• Сохранено сообщений: {stats['total_facts']} / {stats['max_facts']}\n"
    response += f"• Заполнено: {stats['usage_percent']}%\n"
    response += f"• Уникальных ключей: {stats['total_keys']}\n\n"

    if stats['top_contributors']:
        response += "🏆 <b>Топ активных:</b>\n"
        for username, count in stats['top_contributors']:
            response += f"  • {username}: {count} сообщ.\n"
        response += "\n"

    response += f"📝 <b>Последние сообщения (последние 20):</b>\n\n"

    # Собираем последние сообщения
    all_messages = []
    for key, fact_list in facts.items():
        if isinstance(fact_list, list):
            for fact in fact_list:
                all_messages.append(fact)

    # Сортируем по времени
    all_messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    # Показываем последние 20
    safe_msgs = list(all_messages) if isinstance(all_messages, list) else []
    msgs_to_show = safe_msgs[:20]
    for msg in msgs_to_show:
        username_val = str(msg.get('username', 'Unknown'))
        ts_val = msg.get('timestamp', '')
        timestamp = str(ts_val)[:16].replace('T', ' ') if ts_val else "Unknown"
        fact_val = msg.get('fact', '')
        text = str(fact_val)[:80]
        response += f"[{timestamp}] @{username_val}: {text}...\n"

    # Если ответ длинный, разбиваем на части
    if len(response) > 4096:
        for f in range(0, len(response), 4096):
            await message.reply_text(response[f:f+4096], parse_mode='HTML')
    else:
        await message.reply_text(response, parse_mode='HTML')


async def myinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать персональную информацию о пользователе"""
    message = update.message
    user = message.from_user
    if not user: return
    user_id = user.id
    info = knowledge_manager.get_user_info(user_id)
    if not info:
        await message.reply_text("👤 Я пока ничего не знаю о вас.", parse_mode='HTML')
        return
    response = f"👤 <b>Что я знаю о вас:</b>\n\n"
    type_names = {'name': '📛 Имя', 'age': '🎂 Возраст', 'city': '🏙 Город'}
    for info_type, data in info.items():
        type_name = type_names.get(info_type, f"📌 {info_type}")
        response += f"{type_name}: {data['value']}\n"
    await message.reply_text(response, parse_mode='HTML')


async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать активные поведенческие правила"""
    message = update.message
    chat_id = update.effective_chat.id
    
    rules = knowledge_manager.get_behavioral_rules(chat_id)
    
    if not rules:
        await message.reply_text(
            "📋 <b>Поведенческие правила</b>\n\n"
            "У меня пока нет специальных правил поведения для этого чата.\n\n"
            "Вы можете задать правило, например:\n"
            "• <code>Чупапи, начинай говорить со слов Абудаби</code>\n"
            "• <code>Чупик, всегда добавляй эмодзи 🔥 в конце</code>\n"
            "• <code>Чупа, отвечай только короткими фразами</code>",
            parse_mode='HTML'
        )
        return
    
    response = f"📋 <b>Активные поведенческие правила:</b>\n\n"
    
    for i, rule_data in enumerate(rules, 1):
        rule = rule_data['rule']
        username = rule_data.get('username', 'Unknown')
        timestamp = rule_data.get('timestamp', '')[:10]
        response += f"{i}. [{timestamp}] @{username}:\n   <code>{rule}</code>\n\n"
    
    response += "\n💡 Чтобы удалить правило, используйте: <code>/forget_rule номер</code>"
    
    await message.reply_text(response, parse_mode='HTML')


async def forget_rule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить поведенческое правило"""
    message = update.message
    chat_id = update.effective_chat.id
    
    if not context.args or len(context.args) == 0:
        await message.reply_text(
            "🗑️ <b>Как удалить правило:</b>\n\n"
            "Используйте: <code>/forget_rule номер</code>\n\n"
            "Посмотреть номера правил: <code>/rules</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        rule_index = int(context.args[0]) - 1  # Пользователь вводит 1-based, конвертируем в 0-based
    except ValueError:
        await message.reply_text("❌ Укажите номер правила (число)", parse_mode='HTML')
        return
    
    success = knowledge_manager.remove_behavioral_rule(chat_id, rule_index)
    
    if success:
        await message.reply_text(
            f"✅ Правило #{rule_index + 1} удалено!\n\n"
            f"Теперь я не буду следовать этому правилу.",
            parse_mode='HTML'
        )
    else:
        await message.reply_text(
            f"❌ Не удалось найти правило #{rule_index + 1}.\n\n"
            f"Проверьте номер командой <code>/rules</code>",
            parse_mode='HTML'
        )



async def track_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отслеживание участников во всех сообщениях"""
    message = update.message
    user = message.from_user
    if not user or user.is_bot: return
    chat_id = message.chat.id
    members_manager.add_member(user.id, user.username, user.first_name, user.last_name)
    if message.text:
        members_manager.record_message(user.id, chat_id, message.text, user.username)


async def auto_learn_facts(message, user_text: str):
    """Автоматически сохраняет все сообщения пользователя"""
    user = message.from_user
    if not user or user.is_bot: return
    username = user.username or user.first_name or f"User_{user.id}"
    knowledge_manager.add_raw_message(user_text, user.id, username)


async def check_and_unlock_achievements(chat_id: int, user_id: int, username: str, old_rating: int, new_rating: int):
    """Проверяет и разблокирует ачивки при изменении рейтинга"""
    try:
        # Проверяем достижения по рейтингу
        if new_rating >= 10 and old_rating < 10:
            achievements_manager.unlock_achievement(chat_id, user_id, "ten_points")
        if new_rating >= 50 and old_rating < 50:
            achievements_manager.unlock_achievement(chat_id, user_id, "fifty_points")
        if new_rating >= 100 and old_rating < 100:
            achievements_manager.unlock_achievement(chat_id, user_id, "hundred_points")
        if new_rating >= 500 and old_rating < 500:
            achievements_manager.unlock_achievement(chat_id, user_id, "five_hundred_points")

        # Проверяем уровни
        level_up_happened, old_level, new_level = levels_manager.check_level_up(old_rating, new_rating)
        if level_up_happened:
            level_name = levels_manager.LEVEL_NAMES.get(new_level, f"Уровень {new_level}")
            message = f"🎉 <b>{username}</b> достиг нового уровня!\n🚀 <b>{level_name}</b>\n⭐ Рейтинг: {new_rating}"

            # Разблокируем ачивки за уровни
            if new_level >= 5:
                achievements_manager.unlock_achievement(chat_id, user_id, "level_5")
            if new_level >= 10:
                achievements_manager.unlock_achievement(chat_id, user_id, "level_10")

            # Отправляем уведомление в чат (asynchronously)
            try:
                from telegram import Bot
                bot = Bot(token=TELEGRAM_BOT_TOKEN)
                await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Error sending level up message: {e}")

    except Exception as e:
        logger.error(f"Error checking achievements: {e}")


async def check_rating_request(update: Update, user_text: str, chat_id: int, user_id: int, username: str) -> bool:
    """
    Проверяет просьбы о начислении очков и начисляет их.
    Возвращает True если очки были начислены.
    """
    import re

    text_lower = user_text.lower()

    # Ищем фразы просьбы о начислении очков
    rating_request_patterns = [
        r'дай\s+(?:мне\s+)?(?:\d+\s+)?очк',  # дай очки, дай 5 очков
        r'начисл[и|ь]\s+(?:мне\s+)?(?:\d+\s+)?(?:рейтинг|очк)',  # начисли очки, начисли рейтинг
        r'добав[ь|и]\s+(?:мне\s+)?(?:\d+\s+)?(?:рейтинг|очк)',  # добавь очки
        r'очк[и|а|ов]\s+(?:плиз|пожалуйста)',  # очки плиз, очки пожалуйста
        r'начисл(?:и|ь)\s+(?:мне\s+)?рейтинг',  # начисли рейтинг
        r'плюс\s+\d+\s+(?:рейтинг|очк)',  # плюс 5 очков
    ]

    # Проверяем, содержит ли сообщение просьбу о начислении очков
    has_rating_request = any(re.search(pattern, text_lower) for pattern in rating_request_patterns)

    if not has_rating_request:
        return False

    # Пытаемся извлечь количество очков из текста
    points_match = re.search(r'(\d+)\s+(?:очк|рейтинг)', text_lower)
    points = int(points_match.group(1)) if points_match else 1

    # Ограничиваем максимум 5 очков за одну просьбу
    points = min(points, 5)

    # Пытаемся найти упоминание другого пользователя (@username или имя)
    target_user_id = user_id
    target_username = username

    # Ищем @mention
    mention_match = re.search(r'@(\w+)', user_text)
    if mention_match:
        mentioned_user = mention_match.group(1)
        # Пытаемся найти этого пользователя в базе членов
        if chat_id in members_manager.members:
            for member in members_manager.members[chat_id]:
                if member.get('username') == mentioned_user or member.get('first_name', '').lower() == mentioned_user.lower():
                    target_user_id = member['user_id']
                    target_username = member.get('username') or member.get('first_name', mentioned_user)
                    break

    # Ищем имя в тексте (после "дай", "начисли" и т.д.)
    name_match = re.search(r'(?:дай|начисл|добав|плюс)\s+(?:\d+\s+)?(?:очк|рейтинг)?\s*(?:для\s+)?(\w+)', user_text)
    if name_match and not mention_match:  # Приоритет @mention
        potential_name = name_match.group(1)
        if chat_id in members_manager.members:
            for member in members_manager.members[chat_id]:
                if member.get('username') == potential_name or member.get('first_name', '').lower() == potential_name.lower():
                    target_user_id = member['user_id']
                    target_username = member.get('username') or member.get('first_name', potential_name)
                    break

    # Проверяем дневной лимит (максимум 10 очков в день)
    daily_manual_grants = daily_stats.get_today_manual_grants(chat_id)
    if daily_manual_grants >= 10:
        await update.message.reply_text(
            "⚠️ Лимит начисления очков на сегодня исчерпан!\n"
            "Максимум 10 очков в день. Приходите завтра! 😊"
        )
        return True  # Очки не начислены, но это была попытка начисления

    # Если просьба превышает оставшийся лимит, уменьшаем количество
    remaining_limit = 10 - daily_manual_grants
    points = min(points, remaining_limit)

    try:
        # Начисляем очки целевому пользователю
        old_rating = rating_manager.get_user_rating(chat_id, target_user_id)
        rating_manager.add_rating(
            chat_id, target_user_id, target_username,
            points=points,
            reason=f"Просьба о начислении очков в чате"
        )
        # Отслеживаем ручное начисление в статистике
        daily_stats.add_manual_grant_points(chat_id, points)
        new_rating = rating_manager.get_user_rating(chat_id, target_user_id)

        # Проверяем уровень и ачивки
        await check_and_unlock_achievements(chat_id, target_user_id, target_username, old_rating, new_rating)

        # Отправляем подтверждение
        remaining = 10 - (daily_manual_grants + points)
        response = (
            f"✅ Начислено {points} очков для <b>{target_username}</b>!\n"
            f"⭐ Новый рейтинг: {new_rating} (было {old_rating})\n"
            f"📊 Осталось очков на сегодня: {remaining}/10"
        )
        await update.message.reply_text(response, parse_mode='HTML')
        logger.info(f"[RATING] Manual grant: {target_username} received {points} points (total: {new_rating}), daily total: {daily_manual_grants + points}/10")
        return True  # Очки успешно начислены

    except Exception as e:
        logger.error(f"Error processing rating request: {e}")
        return False  # Ошибка при начислении


async def evaluate_message(update: Update, user_text: str, username: str, chat_id: int, user_id: int):
    """
    Простая вероятностная система рейтинга.
    Каждое сообщение имеет 10% шанс получить от 1 до 25 очков.
    Без использования AI.
    """
    try:
        logger.info(f"[RATING] Processing message from {username} (user_id={user_id}) in chat {chat_id}")

        # Проверяем 10% вероятность
        rand_value = random.random()
        logger.info(f"[RATING] Random check: {rand_value:.4f} < 0.10? {rand_value < 0.10}")

        if rand_value < 0.10:
            # Награждаем случайным количеством очков от 1 до 25
            points = random.randint(1, 25)
            logger.info(f"[RATING] 10% check PASSED - granting {points} points!")

            rating_manager.add_rating(
                chat_id, user_id, username,
                points=points,
                reason=f"Удачный бросок 🎲 (+{points})"
            )
            daily_stats.add_rating_points(chat_id, points)

            # Отправляем публичное сообщение о начисленных очках
            new_rating = rating_manager.get_user_rating(chat_id, user_id)

            # Разные эмодзи в зависимости от количества очков
            emoji = "🎉" if points <= 10 else "🔥" if points <= 20 else "💎"
            announcement = f"{emoji} <b>{username}</b> получил <b>+{points} очков</b>!\n⭐ Новый рейтинг: <b>{new_rating}</b> очков"

            try:
                await update.message.chat.send_message(announcement, parse_mode='HTML')
            except Exception as e:
                logger.warning(f"[RATING] Could not send rating announcement: {e}")

            # Проверяем ачивки
            old_rating = new_rating - points
            asyncio.create_task(check_and_unlock_achievements(
                chat_id, user_id, username, old_rating, new_rating
            ))
        else:
            logger.info(f"[RATING] 25% check failed - no points this time")

    except Exception as e:
        logger.error(f"[RATING] Error: {e}", exc_info=True)


async def handle_persona_change(message, user_text: str, chat_id: int) -> bool:
    """Обработка смены личности"""
    new_persona, is_reset = smart_ai.detect_persona_change(user_text)
    if is_reset:
        settings_manager.update_setting(chat_id, "custom_persona", None)
        history_manager.clear_history(chat_id)
        await message.reply_text("Хорошо, возвращаюсь в свой обычный облик! Чупапи снова в здании! 😎✨")
        return True
    elif new_persona:
        settings_manager.update_setting(chat_id, "custom_persona", new_persona)
        await message.reply_text(f"Принято! Теперь я — {new_persona}. Посмотрим, как это у меня получится! 😉🎭")
        return True
    return False


async def handle_behavioral_instruction(message, user_text: str, chat_id: int, user_id: int, username: str) -> bool:
    """Обработка поведенческих инструкций"""
    behavioral_instruction = smart_ai.detect_behavioral_instruction(user_text)
    if behavioral_instruction:
        knowledge_manager.add_behavioral_rule(chat_id, behavioral_instruction, user_id, username)
        await message.reply_text(f"✅ Запомнил! Теперь буду: {behavioral_instruction}\n\nПроверь - спроси меня что-нибудь! 😉")
        return True
    return False


async def handle_reminder_request(message, context: ContextTypes.DEFAULT_TYPE, user_text: str, chat_id: int, user_id: int, username: str) -> bool:
    """Обработка запросов на напоминание"""
    logger.info(f"[DEBUG] Checking for reminder in message: '{user_text[:50]}...'")
    reminder_request = smart_ai.detect_reminder_request(user_text)
    logger.info(f"[DEBUG] Reminder detection result: {reminder_request}")
    if reminder_request:
        seconds = reminder_request['seconds']
        amount = reminder_request['amount']
        unit = reminder_request['unit']
        reminder_text = reminder_request['text']
        
        # Формируем единицу времени для отображения
        if unit in ['секунд', 'сек']:
            time_unit = 'секунд' if amount > 1 else 'секунду'
        elif unit in ['минут', 'мин']:
            time_unit = 'минут' if amount > 1 else 'минуту'
        else:
            time_unit = 'час' if amount == 1 else ('часа' if amount < 5 else 'часов')
        
        # Подтверждение
        what_to_remind = f" про '{reminder_text}'" if reminder_text else ""
        await message.reply_text(
            f"⏰ Окей, напомню через {amount} {time_unit}{what_to_remind}! 👌"
        )
        
        # Планируем напоминание
        task = asyncio.create_task(send_reminder(
            context.application,
            chat_id,
            user_id,
            username,
            seconds,
            reminder_text,
            user_text
        ))
        # Сохраняем ссылку на задачу, чтобы она не была удалена сборщиком мусора
        background_tasks.add(task)
        # Удаляем задачу из set после завершения
        task.add_done_callback(background_tasks.discard)
        
        logger.info(f"[REMINDER] Task created and tracked for chat {chat_id}")
        return True
    return False


async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str, username: str):
    """Обработка сообщения с генерацией ответа"""
    chat_id = update.effective_chat.id
    message = update.message
    user = message.from_user

    chat_history = history_manager.get_history(chat_id)[:-1]

    # 1. Проверка на смену личности
    if await handle_persona_change(message, user_text, chat_id):
        return

    # 2. Проверка на поведенческую инструкцию
    if await handle_behavioral_instruction(message, user_text, chat_id, user.id, username):
        return

    # 3. Проверка на запрос напоминания
    if await handle_reminder_request(message, context, user_text, chat_id, user.id, username):
        return

    # Если пользователь просит найти что-то в интернете - честно говорим что не умеем
    if needs_web_search(user_text):
        await message.reply_text(
            "😅 Слушай, я бы рад помочь, но пока не умею искать в интернете в реальном времени!\n\n"
            "Могу ответить только на основе своих знаний и того, что обсуждалось в этой беседе. "
            "Для свежей инфы лучше загугли! 🌐"
        )
        return

    # Сначала пробуем локальную AI для простых вопросов
    is_complex = is_complex_task(user_text)
    if not is_complex:
        local_response, confidence = smart_ai.generate_smart_response(user_text, user.id, username)
        if confidence > 0.8:
            history_manager.add_message(chat_id, "assistant", local_response, context.bot.username or "Assistant")
            # 🌍 Обновляем настроение на основе сентимента
            sentiment = smart_ai.detect_sentiment(user_text)
            mood_manager.update_mood(chat_id, sentiment)
            await message.reply_text(local_response)
            return

    knowledge_context = knowledge_manager.get_context_for_prompt(user_text)
    user_context = knowledge_manager.get_user_context(user.id)
    user_name = knowledge_manager.get_user_name(user.id)

    settings = settings_manager.get_chat_settings(chat_id)
    style = settings.get("response_style", "concise")

    style_instruction = ""
    if style == "concise":
        style_instruction = "\nПРАВИЛО: ОТВЕЧАЙ МАКСИМАЛЬНО КРАТКО (1-2 предложения, по существу)."
    elif style == "full":
        style_instruction = "\nПРАВИЛО: ОТВЕЧАЙ РАЗВЕРНУТО и подробно, делись деталями."

    custom_persona = settings.get("custom_persona")
    persona_instruction = ""
    if custom_persona:
        persona_instruction = f"\nТЕКУЩАЯ РОЛЬ: Тебе приказали быть: {custom_persona}. На время этого разговора твоя личность меняется. Веди себя, отвечай и шути именно как {custom_persona}."

    # 🌍 Добавляем контекст настроения и времени суток
    mood_context = mood_manager.get_mood_prompt_context(chat_id)
    time_context = get_time_context()
    
    # 🧠 Добавляем поведенческие правила
    behavioral_context = knowledge_manager.get_behavioral_context(chat_id)

    enhanced_prompt = SYSTEM_PROMPT + style_instruction + persona_instruction + "\n" + mood_context + "\n" + time_context + "\n" + behavioral_context + "\n" + user_context + "\n" + knowledge_context

    try:
        # Оптимизация контекста: отправляем только последние 10-12 сообщений для экономии токенов
        # Полная история хранится локально, но в AI отправляем только недавние
        recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history

        formatted_history = []
        for m in recent_history:
            role = m.get('role', 'user')
            content = m.get('content', '')
            sender = m.get('sender', 'Unknown')
            if role == 'user':
                formatted_history.append({"role": "user", "content": f"{sender}: {content}"})
            else:
                formatted_history.append({"role": "assistant", "content": content})

        response = await glm_client.chat_completion_with_history(
            user_message=f"{username}: {user_text}",
            chat_history=formatted_history,
            system_prompt=enhanced_prompt
        )

        if response:
            # 🌍 Обновляем настроение на основе сентимента
            sentiment = smart_ai.detect_sentiment(user_text)
            mood_manager.update_mood(chat_id, sentiment)

            # 🌍 Разбиваем на несколько сообщений если текст длинный
            messages_to_send = human_behavior.split_into_messages(str(response), max_length=200)

            history_manager.add_message(chat_id, "assistant", str(response), context.bot.username or "Assistant")
            await auto_learn_facts(message, user_text)

            # Отправляем сообщения по очереди
            last_sent_message = None
            for i, msg_part in enumerate(messages_to_send):
                # 🌍 Добавляем typing pause перед каждым сообщением
                await human_behavior.typing_pause(context, chat_id, len(msg_part))

                # 🌍 Добавляем опечатки только к последнему сообщению
                if i == len(messages_to_send) - 1:
                    msg_with_typos, needs_fix = human_behavior.add_typos(msg_part, typo_chance=0.05)
                    msg_with_typos = human_behavior.add_filler_words(msg_with_typos)
                else:
                    msg_with_typos = msg_part
                    needs_fix = False

                # Отправляем сообщение
                last_sent_message = await message.reply_text(msg_with_typos)

                # Небольшая пауза между сообщениями (1-2 сек)
                if i < len(messages_to_send) - 1:
                    await asyncio.sleep(random.uniform(1.0, 2.0))

            # 🌍 Редкое исправление (3% шанс) только для последнего сообщения
            if last_sent_message and needs_fix and human_behavior.should_fix_typo(needs_fix):
                await asyncio.sleep(random.uniform(1, 2))
                try:
                    await last_sent_message.edit_text(messages_to_send[-1] + " *исправил")
                except Exception:
                    pass  # Если сообщение нельзя редактировать, пропускаем

        else:
            # Если ответ None - используем fallback вместо ошибки
            fallback_responses = FALLBACK_RESPONSES.get('unknown', ["Не уверен... давай ещё раз? 🤔"])
            fallback = random.choice(fallback_responses)
            user_name = username or "дружище"
            fallback = fallback.format(name=user_name)

            # 🌍 Добавляем typing pause и для fallback
            await human_behavior.typing_pause(context, chat_id, len(fallback))
            await message.reply_text(fallback)
            history_manager.add_message(chat_id, "assistant", fallback, context.bot.username or "Assistant")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.reply_text("Что-то пошло не так...")

    params = settings_manager.get_intervention_params(chat_id)
    if history_manager.should_intervene(chat_id, probability=params['probability'], min_delay=params['min_delay']):
        # Дополнительная проверка: не спамим чаще чем каждые 5 минут
        if history_manager.can_send_proactive_message(chat_id, min_interval_seconds=300):
            history = history_manager.get_history(chat_id)
            opinion = smart_ai.generate_proactive_hook(history)
            if opinion:
                await context.bot.send_message(chat_id=chat_id, text=opinion)
                history_manager.add_message(chat_id, "assistant", opinion, context.bot.username or "Assistant")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений с системой очередей"""
    chat_id = update.effective_chat.id
    message = update.message
    user = message.from_user
    chat_type = update.effective_chat.type

    # Отслеживаем всех участников
    if user and not user.is_bot:
        await track_members(update, context)

    if not is_chat_allowed(chat_id):
        return

    username = user.username or user.first_name or f"User_{user.id}"
    user_text = message.text.strip()

    # Всегда добавляем сообщение в историю для контекста
    history_manager.add_message(chat_id, "user", user_text, username)
    daily_stats.add_message(chat_id)
    await auto_learn_facts(message, user_text)

    # Анализируем сообщение для рейтинга - простая 25% вероятность без API
    asyncio.create_task(evaluate_message(update, user_text, username, chat_id, user.id))

    # Проверяем просьбы о начислении очков (не блокирует дальнейший ответ)
    rating_request_processed = await check_rating_request(update, user_text, chat_id, user.id, username)

    # Определяем, нужно ли отвечать на сообщение
    should_respond = False

    # Проверяем, обращение ли это к боту с помощью word boundaries
    import re
    text_lower = user_text.lower()

    # Варианты обращения к боту
    bot_names = ['чупапи', 'чупа', 'чупик']

    # 1. В личке - отвечаем только @godstress
    if chat_type == 'private':
        if user.username and user.username.lower() == 'godstress':
            should_respond = True
        else:
            # Отправляем сообщение что общаться можно только в группе
            await message.reply_text(
                "Йоу! Я тут только в группах общаюсь 😎\n"
                "Добавь меня в беседу и там поболтаем!"
            )
            return

    # 2. Упоминание через @username
    elif context.bot.username and f"@{context.bot.username}" in text_lower:
        should_respond = True
        user_text = user_text.replace(f"@{context.bot.username}", "").strip()

    # 3. Обращение по имени - проверяем с word boundaries
    # Ищем имя в начале или с запятой/пробелом
    elif re.search(r'\b(чупапи|чупа|чупик)(?:\s|,|!|\?|:|$)', text_lower):
        should_respond = True
        # Удаляем обращение из начала текста
        for word in bot_names:
            user_text = re.sub(rf'\b{word}\b(?:\s+|,\s*)', '', user_text, flags=re.IGNORECASE).strip()

    # 4. Ответ на сообщение бота
    elif message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
        should_respond = True

    # Если не нужно отвечать напрямую, есть шанс случайно отреагировать
    if not should_respond:
        # В группах бот иногда реагирует на сообщения (15% шанс)
        if chat_type in ['group', 'supergroup'] and random.random() < 0.15:
            # Проверяем что сообщение достаточно содержательное (не короткое)
            if len(user_text.split()) >= 5:
                # Небольшая пауза перед реакцией (от 3 до 8 секунд)
                await asyncio.sleep(random.uniform(3, 8))

                # Анализируем настроение сообщения и реагируем
                await message.chat.send_action('typing')

                # Используем небольшую задержку для имитации "думания"
                pause_duration = await human_behavior.calculate_response_time(user_text)
                await asyncio.sleep(pause_duration)

                # Генерируем короткую реакцию через GLM
                recent_history = history_manager.get_history(chat_id, limit=5)
                messages = [{"role": "system", "content": SYSTEM_PERSONA + "\n\nТы случайно услышал разговор в чате и хочешь коротко прокомментировать или вставить свое слово. Будь естественным, дерзким и уместным. Ответь ОЧЕНЬ коротко (5-15 слов максимум), как будто просто вставляешь реплику в разговор."}]

                for msg in recent_history:
                    messages.append({"role": msg["role"], "content": msg["content"]})

                try:
                    response = await glm_client.chat_completion(messages, max_tokens=50, temperature=0.9)
                    if response:
                        # Применяем человеческое поведение к реакции
                        response = await human_behavior.apply_human_behavior(response, mood_manager.get_current_mood())

                        await message.reply_text(response)
                        history_manager.add_message(chat_id, "assistant", response, "Chupapi")
                        logger.info(f"Random reaction in chat {chat_id}: {response[:50]}...")
                except Exception as e:
                    logger.error(f"Error generating random reaction: {e}")
        return

    if not user_text:
        return

    # Используем блокировку для каждого чата чтобы обрабатывать запросы последовательно
    async with chat_locks[chat_id]:
        await message.chat.send_action('typing')
        await process_message(update, context, user_text, username)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню настроек"""
    chat_id = update.effective_chat.id
    if not is_chat_allowed(chat_id): return
    
    chat = update.effective_chat
    # Проверка на админа в группах
    if chat.type in ['group', 'supergroup']:
        user_id = update.effective_user.id
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status not in ['administrator', 'creator']:
                await update.message.reply_text("⛔ Только администраторы могут менять настройки бота в группе.")
                return
        except Exception as e:
            logger.error(f"Error checking admin: {e}")

    settings = settings_manager.get_chat_settings(chat_id)
    chat_title = chat.title if chat.title else "этот чат"

    # Формируем текст
    style = "Краткий" if settings.get("response_style") == "concise" else "Развернутый"
    level = settings.get("intervention_level", "medium")
    level_map = {"none": "Выкл", "low": "Низкий", "medium": "Средний", "high": "Высокий"}
    silence = "Вкл" if settings.get("silence_revival", True) else "Выкл"
    custom_persona = settings.get("custom_persona")
    persona_status = "🎭 Своя" if custom_persona else "😎 Чупапи"

    text = (
        f"⚙️ <b>Настройки Чупапи для:</b> <i>{chat_title}</i>\n\n"
        f"👤 Личность: <b>{persona_status}</b>\n"
        f"🎭 Стиль: <b>{style}</b>\n"
        f"⚡ Активность: <b>{level_map.get(level, level)}</b>\n"
        f"🤫 Самооживление: <b>{silence}</b>\n\n"
        "Выберите, что хотите изменить:"
    )

    # Кнопки
    keyboard = [
        [
            InlineKeyboardButton("👤 Личность", callback_data="set_persona_menu"),
            InlineKeyboardButton("🎭 Стиль", callback_data="set_style_menu")
        ],
        [
            InlineKeyboardButton("⚡ Активность", callback_data="set_activity_menu"),
            InlineKeyboardButton("🤫 Оживление", callback_data="set_silence_menu")
        ],
        [
            InlineKeyboardButton("✅ Готово", callback_data="set_close")
        ]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий в меню настроек"""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    data = query.data

    # Обрабатываем только settings callbacks
    if not data.startswith("set_"):
        return
    
    if data == "set_persona_menu":
        settings = settings_manager.get_chat_settings(chat_id)
        custom_persona = settings.get("custom_persona")
        current_status = f"<b>Текущая личность:</b> {custom_persona}" if custom_persona else "<b>Текущая личность:</b> Чупапи (по умолчанию)"

        text = (
            f"👤 <b>Настройка личности бота</b>\n\n"
            f"{current_status}\n\n"
            "Выберите действие:"
        )

        keyboard = [
            [InlineKeyboardButton("🎭 Задать свою личность", callback_data="set_persona_custom")],
            [InlineKeyboardButton("🔄 Сбросить на Чупапи", callback_data="set_persona_reset")],
            [InlineKeyboardButton("🔙 Назад", callback_data="set_main_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif data == "set_persona_reset":
        settings_manager.update_setting(chat_id, "custom_persona", None)
        history_manager.clear_history(chat_id)
        await query.answer("Личность сброшена на Чупапи! ✅")
        await settings_persona_menu(query, chat_id)

    elif data == "set_persona_custom":
        text = (
            "👤 <b>Задать свою личность</b>\n\n"
            "Отправьте сообщение в чат для смены личности бота.\n\n"
            "<b>Примеры команд:</b>\n"
            "• <code>будь строгим профессором</code>\n"
            "• <code>стань веселым пиратом</code>\n"
            "• <code>отвечай как мудрый философ</code>\n"
            "• <code>говори как дерзкий подросток</code>\n\n"
            "Чтобы вернуть обычную личность Чупапи:\n"
            "• <code>вернись в норму</code>\n"
            "• <code>стань собой</code>"
        )

        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="set_persona_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        await query.answer("Напишите описание личности в чат")

    elif data == "set_style_menu":
        keyboard = [
            [
                InlineKeyboardButton("🎯 Краткий", callback_data="set_style_concise"),
                InlineKeyboardButton("📝 Развернутый", callback_data="set_style_full")
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data="set_main_menu")]
        ]
        await query.edit_message_text("Выберите стиль ответов:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif data == "set_activity_menu":
        keyboard = [
            [
                InlineKeyboardButton("🔇 Выкл", callback_data="set_act_none"),
                InlineKeyboardButton("💤 Низкий", callback_data="set_act_low")
            ],
            [
                InlineKeyboardButton("🔔 Средний", callback_data="set_act_medium"),
                InlineKeyboardButton("🔥 Высокий", callback_data="set_act_high")
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data="set_main_menu")]
        ]
        await query.edit_message_text("Выберите уровень активности бота:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif data == "set_silence_menu":
        settings = settings_manager.get_chat_settings(chat_id)
        enabled = settings.get("silence_revival", True)
        status_text = "Включено" if enabled else "Выключено"
        btn_text = "❌ Выключить" if enabled else "✅ Включить"
        
        text = (
            f"<b>Оживление при молчании</b>\n\n"
            f"Текущий статус: <b>{status_text}</b>\n"
            "Если эта функция включена, бот сам начнет разговор, если в чате будет тихо дольше 30 минут."
        )
        
        keyboard = [
            [InlineKeyboardButton(btn_text, callback_data="toggle_silence")],
            [InlineKeyboardButton("🔙 Назад", callback_data="set_main_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        
    elif data == "toggle_silence":
        settings = settings_manager.get_chat_settings(chat_id)
        new_val = not settings.get("silence_revival", True)
        settings_manager.update_setting(chat_id, "silence_revival", new_val)
        await query.answer(f"Оживление {'включено' if new_val else 'выключено'}")
        await settings_silence_menu(query, chat_id)

    elif data.startswith("set_style_"):
        style = data.replace("set_style_", "")
        logger.info(f"DEBUG: Setting style to {style} for chat {chat_id}")
        try:
            settings_manager.update_setting(chat_id, "response_style", style)
            logger.info("DEBUG: Style settings updated successfully")
            
            await settings_main_menu(query, chat_id)
            await query.answer("Стиль изменен! ✅")
        except Exception as e:
            logger.error(f"DEBUG: Error updating style: {e}")
            await query.answer("Ошибка сохранения ❌")
        
    elif data.startswith("set_act_"):
        level = data.replace("set_act_", "")
        logger.info(f"DEBUG: Setting activity level to {level} for chat {chat_id}")
        
        try:
            settings_manager.update_setting(chat_id, "intervention_level", level)
            logger.info("DEBUG: Settings updated successfully")
            
            # Принудительно обновляем меню
            await settings_main_menu(query, chat_id)
            await query.answer("Настройки сохранены! ✅") 
            
        except Exception as e:
            logger.error(f"DEBUG: Error updating settings: {e}")
            await query.answer("Ошибка сохранения ❌")

    elif data == "set_main_menu":
        await settings_main_menu(query, chat_id)
        
    elif data == "set_close":
        try:
            await query.message.delete()
        except:
            pass


async def settings_persona_menu(query, chat_id):
    """Вспомогательная функция для отрисовки меню настройки персоны"""
    settings = settings_manager.get_chat_settings(chat_id)
    custom_persona = settings.get("custom_persona")
    current_status = f"<b>Текущая личность:</b> {custom_persona}" if custom_persona else "<b>Текущая личность:</b> Чупапи (по умолчанию)"

    text = (
        f"👤 <b>Настройка личности бота</b>\n\n"
        f"{current_status}\n\n"
        "Выберите действие:"
    )

    keyboard = [
        [InlineKeyboardButton("🎭 Задать свою личность", callback_data="set_persona_custom")],
        [InlineKeyboardButton("🔄 Сбросить на Чупапи", callback_data="set_persona_reset")],
        [InlineKeyboardButton("🔙 Назад", callback_data="set_main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


async def settings_main_menu(query, chat_id):
    """Отрисовка главного меню настроек"""
    settings = settings_manager.get_chat_settings(chat_id)

    # Получаем название чата
    try:
        chat = await query.get_bot().get_chat(chat_id)
        chat_title = chat.title if chat.title else "этот чат"
    except:
        chat_title = "этот чат"

    style = "Краткий" if settings.get("response_style") == "concise" else "Развернутый"
    level = settings.get("intervention_level", "medium")
    level_map = {"none": "Выкл", "low": "Низкий", "medium": "Средний", "high": "Высокий"}
    silence = "Вкл" if settings.get("silence_revival", True) else "Выкл"
    custom_persona = settings.get("custom_persona")
    persona_status = "🎭 Своя" if custom_persona else "😎 Чупапи"

    text = (
        f"⚙️ <b>Настройки Чупапи для:</b> <i>{chat_title}</i>\n\n"
        f"👤 Личность: <b>{persona_status}</b>\n"
        f"🎭 Стиль: <b>{style}</b>\n"
        f"⚡ Активность: <b>{level_map.get(level, level)}</b>\n"
        f"🤫 Самооживление: <b>{silence}</b>\n\n"
        "Выберите, что хотите изменить:"
    )

    keyboard = [
        [
            InlineKeyboardButton("👤 Личность", callback_data="set_persona_menu"),
            InlineKeyboardButton("🎭 Стиль", callback_data="set_style_menu")
        ],
        [
            InlineKeyboardButton("⚡ Активность", callback_data="set_activity_menu"),
            InlineKeyboardButton("🤫 Оживление", callback_data="set_silence_menu")
        ],
        [
            InlineKeyboardButton("✅ Готово", callback_data="set_close")
        ]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


async def settings_silence_menu(query, chat_id):
    """Вспомогательная функция для отрисовки меню настройки молчания"""
    settings = settings_manager.get_chat_settings(chat_id)
    enabled = settings.get("silence_revival", True)
    status_text = "Включено" if enabled else "Выключено"
    btn_text = "❌ Выключить" if enabled else "✅ Включить"

    text = (
        f"<b>Оживление при молчании</b>\n\n"
        f"Текущий статус: <b>{status_text}</b>\n"
        "Если эта функция включена, бот сам начнет разговор, если в чате будет тихо дольше 30 минут."
    )

    keyboard = [
        [InlineKeyboardButton(btn_text, callback_data="toggle_silence")],
        [InlineKeyboardButton("🔙 Назад", callback_data="set_main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


async def silence_checker_loop(application: Application):
    """Бесконечный цикл для проверки молчания в чатах"""
    logger.info("Silence checker loop started")
    while True:
        try:
            # Ждем минуту между проверками
            await asyncio.sleep(60)
            
            for chat_id_str in list(history_manager.chats.keys()):
                chat_id = int(chat_id_str)
                settings = settings_manager.get_chat_settings(chat_id)
                if not settings.get("silence_revival", True):
                    continue
                    
                timeout = settings.get("silence_timeout", 5)
                silence_duration = history_manager.get_silence_duration(chat_id)
                
                if silence_duration >= timeout:
                    logger.info(f"Silence timeout reached in chat {chat_id} ({silence_duration:.1f} min)")

                    # Генерируем хук для оживления через GLM
                    chat_history = history_manager.get_history(chat_id)
                    if not chat_history:
                        continue
                        
                    # Чтобы не спамить, сбрасываем время последней активности СЕЙЧАС
                    history_manager.last_interactions[chat_id] = datetime.now()
                    
                    # Формируем контекст для генерации (берем последние 15)
                    context_text = "\n".join([f"{m['sender']}: {m['content']}" for m in chat_history[-15:]])
                    
                    prompt = [
                        {"role": "system", "content": "Ты — веселый бот в чате. Сейчас в чате тишина. Твоя задача — придумать короткую реплику или вопрос, чтобы оживить беседу. Используй контекст переписки, но не повторяйся. Будь дерзким или смешным, в своем стиле. Не здоровайся заново."},
                        {"role": "user", "content": f"Вот последние сообщения в чате:\n{context_text}\n\nНикто не пишет уже {int(silence_duration)} минут. Придумай, как оживить диалог одной фразой."}
                    ]
                    
                    try:
                        hook = await glm_client.chat_completion(prompt, max_tokens=100, temperature=0.8)
                        if hook:
                            history_manager.add_message(chat_id, "assistant", hook, application.bot.username or "Assistant")
                            await application.bot.send_message(chat_id=chat_id, text=hook)
                    except Exception as e:
                        logger.error(f"Error sending silence hook: {e}")
        except Exception as e:
            logger.error(f"Error in silence loop: {e}")
            await asyncio.sleep(10)


async def morning_greeting_scheduler(application: Application):
    """Отправляет утреннее приветствие в 8:00 в стиле Чупапи"""
    logger.info("Morning greeting scheduler started")
    from datetime import timedelta

    while True:
        try:
            now = datetime.now()
            # Вычисляем время до следующих 8:00
            next_morning = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if now.hour >= 8:
                # Если уже прошло 8:00 сегодня, переносим на завтра
                next_morning = next_morning + timedelta(days=1)

            sleep_seconds = (next_morning - now).total_seconds()
            logger.info(f"Next morning greeting at: {next_morning} (in {sleep_seconds:.0f} seconds)")
            await asyncio.sleep(sleep_seconds)

            # Отправляем приветствие только в группы (не в личные сообщения)
            for chat_id_str in list(history_manager.chats.keys()):
                chat_id = int(chat_id_str)

                if not is_chat_allowed(chat_id):
                    continue

                # Проверяем тип чата - отправляем только в группы
                try:
                    chat = await application.bot.get_chat(chat_id)
                    if chat.type == 'private':
                        continue  # Пропускаем личные чаты
                except Exception as e:
                    logger.warning(f"Could not get chat info for {chat_id}: {e}")
                    continue

                # Генерируем утреннее приветствие через GLM в стиле Чупапи
                prompt = [
                    {"role": "system", "content": SYSTEM_PERSONA + "\n\nСейчас 8 утра. Ты только проснулся и хочешь поприветствовать людей в чате. Будь энергичным, позитивным, используй свой стиль общения. Напиши короткое (1-2 предложения) утреннее приветствие и пожелай хорошего дня. Используй эмодзи."},
                    {"role": "user", "content": "Напиши утреннее приветствие в своем стиле"}
                ]

                try:
                    greeting = await glm_client.chat_completion(prompt, max_tokens=100, temperature=0.9)

                    if greeting:
                        await application.bot.send_message(
                            chat_id=chat_id,
                            text=greeting
                        )
                        logger.info(f"Morning greeting sent to chat {chat_id}")
                    else:
                        # Fallback если GLM не ответил
                        fallback = "☀️ Доброе утро, пацаны! Выспались? Желаю вам сегодня всё порвать! 🔥"
                        await application.bot.send_message(
                            chat_id=chat_id,
                            text=fallback
                        )
                except Exception as e:
                    logger.error(f"Error sending morning greeting to chat {chat_id}: {e}")

        except Exception as e:
            logger.error(f"Error in morning greeting scheduler: {e}")
            await asyncio.sleep(60)


async def daily_stats_scheduler(application: Application):
    """Отправляет статистику в полночь и сбрасывает счетчики"""
    logger.info("Daily stats scheduler started")
    from datetime import timedelta

    while True:
        try:
            now = datetime.now()
            # Вычисляем время до следующей полночи
            next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            sleep_seconds = (next_midnight - now).total_seconds()

            logger.info(f"Next daily stats send at: {next_midnight} (in {sleep_seconds:.0f} seconds)")
            await asyncio.sleep(sleep_seconds)

            # Отправляем статистику только в группы (не в личные сообщения)
            # Отправляем статистику только в группы (не в личные сообщения)
            for chat_id_str in list(history_manager.chats.keys()):
                chat_id = int(chat_id_str)
                
                # Отключаем отправку статистики, только сбрасываем счетчики
                daily_stats.reset_today_stats(chat_id)

        except Exception as e:
            logger.error(f"Error in daily stats scheduler: {e}")
            await asyncio.sleep(60)


async def rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать рейтинг пользователей в чате"""
    chat_id = update.effective_chat.id
    logger.info(f"RATING command called in chat {chat_id}")

    if not is_chat_allowed(chat_id):
        return

    # Получаем статистику чата
    stats = rating_manager.get_chat_stats(chat_id)

    if stats['total_users'] == 0:
        await update.message.reply_text(
            "📊 Рейтинг в чате еще не начисляется.\n\n"
            "Пишите качественные сообщения! 🎯\n"
            "Я периодически оцениваю сообщения и добавляю очки за хорошие!"
        )
        return

    # Получаем топ 10 пользователей
    top_users = rating_manager.get_top_users(chat_id, limit=10)

    message = "🏆 <b>РЕЙТИНГ ЧАТА</b>\n\n"

    # Статистика
    message += f"📈 <b>Статистика:</b>\n"
    message += f"  Активных участников: {stats['total_users']}\n"
    message += f"  Всего очков выдано: {stats['total_points']}\n"
    message += f"  Среднее очков на человека: {stats['average_rating']}\n\n"

    # Лидер
    if stats['top_user']:
        message += f"👑 <b>Лидер:</b> {stats['top_user']} с {stats['top_user_rating']} очками!\n\n"

    # Топ пользователей
    message += "🥇 <b>Топ участников:</b>\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for idx, (user_id, rating, username) in enumerate(top_users):
        medal = medals[idx] if idx < len(medals) else "•"
        message += f"{medal} <b>{username}</b> — {rating} очков\n"

    message += "\n💡 Я оцениваю ваши сообщения автоматически:\n"
    message += "  ⭐⭐ = 2 очка (отличное сообщение)\n"
    message += "  ⭐ = 1 очко (хорошее сообщение)"

    await update.message.reply_text(message, parse_mode='HTML')


async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать уровень и прогресс пользователя"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or f"User_{user_id}"

    if not is_chat_allowed(chat_id):
        return

    rating = rating_manager.get_user_rating(chat_id, user_id)
    level_info = levels_manager.get_level_info(rating)
    progress_bar = levels_manager.get_level_progress_bar(rating)

    message = (
        f"🎮 <b>УРОВЕНЬ И ПРОГРЕСС</b>\n\n"
        f"👤 <b>Пользователь:</b> {username}\n"
        f"⭐ <b>Уровень:</b> {level_info['level']} - {level_info['level_name']}\n"
        f"💪 <b>Рейтинг:</b> {level_info['current_rating']} очков\n\n"
        f"📊 <b>Прогресс до следующего уровня:</b>\n"
        f"{progress_bar}\n"
        f"{level_info['progress']}/{level_info['needed']} очков\n\n"
        f"🎯 <b>Следующий уровень:</b> {level_info['next_level_name']}\n"
    )

    await update.message.reply_text(message, parse_mode='HTML')


async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать достижения пользователя"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or f"User_{user_id}"

    if not is_chat_allowed(chat_id):
        return

    achievements = achievements_manager.get_user_achievements(chat_id, user_id)
    total_achievements = len(achievements_manager.get_all_achievements_info())

    message = f"🏆 <b>ДОСТИЖЕНИЯ {username.upper()}</b>\n\n"

    if achievements:
        message += f"<b>Получено: {len(achievements)}/{total_achievements}</b>\n\n"
        for ach in achievements:
            message += f"{ach['icon']} <b>{ach['name']}</b>\n{ach['description']}\n\n"
    else:
        message += "Пока нет достижений. Начни писать качественные сообщения! 🎯\n\n"

    # Показываем несколько ближайших ачивок
    message += "<b>Ближайшие достижения:</b>\n"
    rating = rating_manager.get_user_rating(chat_id, user_id)

    if not achievements_manager.has_achievement(chat_id, user_id, "ten_points") and rating < 10:
        message += f"⏳ Собрать 10 очков ({rating}/10)\n"
    if not achievements_manager.has_achievement(chat_id, user_id, "fifty_points") and rating < 50:
        message += f"⏳ Собрать 50 очков ({rating}/50)\n"
    if not achievements_manager.has_achievement(chat_id, user_id, "hundred_points") and rating < 100:
        message += f"⏳ Собрать 100 очков ({rating}/100)\n"

    await update.message.reply_text(message, parse_mode='HTML')


async def roast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подколоть участника чата"""
    chat_id = update.effective_chat.id
    logger.info(f"ROAST command called in chat {chat_id}")

    if not is_chat_allowed(chat_id):
        logger.info("ROAST: Chat not allowed")
        return

    chat = update.effective_chat
    logger.info(f"ROAST: Chat type = {chat.type}")

    # Работаем только в группах
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("🔥 Эта команда работает только в группах!")
        return

    try:
        # Получаем список участников
        members = members_manager.get_members_list(chat_id)
        logger.info(f"ROAST: Got {len(members) if members else 0} members")

        if not members:
            await update.message.reply_text("😶 В этом чате ещё никто не писал. Некого подкалывать!")
            return

        # Создаём клавиатуру с участниками
        keyboard = []
        for member in members[:20]:  # Максимум 20 участников
            # Формируем отображаемое имя
            first = member.get('first_name', '')
            last = member.get('last_name', '')
            username = member.get('username', '')
            user_id = member.get('id')

            if username:
                name = f"@{username}"
            elif first and last:
                name = f"{first} {last}"
            elif first:
                name = first
            else:
                name = "Аноним"

            keyboard.append([InlineKeyboardButton(name, callback_data=f"roast_{user_id}")])

        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="roast_cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🔥 <b>Кого подколоть?</b>\n\nВыбери жертву:",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error in roast_command: {e}")
        await update.message.reply_text("😵 Ошибка при получении списка участников.")


async def roast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора пользователя для подкола"""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    data = query.data

    # Проверяем что это наш callback
    if not data or not data.startswith("roast_"):
        return

    if data == "roast_cancel":
        await query.edit_message_text("😏 Ладно, в другой раз тогда...")
        return

    # Extract user_id from callback data
    try:
        target_user_id = int(data.split("_")[1])
    except (ValueError, IndexError):
        await query.edit_message_text("😐 Ошибка выбора пользователя.")
        return

    try:
        # Получаем информацию о цели
        member_info = members_manager.get_user_info(target_user_id)
        if not member_info:
            await query.edit_message_text("😐 Не нашёл инфу об этом чел...")
            return

        # Формируем имя
        first = member_info.get('first_name', '')
        last = member_info.get('last_name', '')
        username = member_info.get('username', '')

        if username:
            target_name = f"@{username}"
        elif first and last:
            target_name = f"{first} {last}"
        elif first:
            target_name = first
        else:
            target_name = "этого чела"

        # Генерируем подкол через GLM с полным стилем Чупапи
        roast_prompt = f"""ТЫ - Чупапи! Ты - живой, харизматичный собеседник с характером. Твоя задача - БЕЗЖАЛОСТНО подколоть {target_name}.

ТВОЙ СТИЛЬ:
- Адаптируйся под вайб: если пацаны - пацан, если нет - просто по-пацански
- Используй мат, сленг,.Expressions - это твоё естество. Не стесняйся!
- Будь дерзким, но без реальной злобы
- Больше сарказма, иронии, самоиронии
- Коротко, 2-3 предложения, но в точку!

ПРИМЕРЫ: "Эй Вася, ты че такой серьезный? Разслабся совсем, блин 😂", "Слушай, ты вообще awe? Смешной же чел 🤦", "Ты кринжовый, но мы тебя любим 😏"

Давай, подколи {target_name} в своём стиле!"""

        response = await glm_client.chat_completion_with_history(
            user_message="Подколи этого чела!",
            system_prompt=roast_prompt
        )

        if response:
            await query.edit_message_text(f"🔥 <b>Подкол для {target_name}:</b>\n\n{response}")
        else:
            # Фоллбэк если API недоступен
            fallbacks = [
                f"Эй, {target_name}! Ты такой {random.choice(['медленный', 'странный', 'весёлый', 'интересный'])}, что даже нейросети тормозят 😏",
                f"{target_name}, слушай... ты вообще нормальный? 😂",
                f"Ой, {target_name}... ну ты понимаешь 😄"
            ]
            await query.edit_message_text(f"🔥 <b>Подкол для {target_name}:</b>\n\n{random.choice(fallbacks)}")

    except Exception as e:
        logger.error(f"Error in roast_callback: {e}")
        await query.edit_message_text("😵 Что-то пошло не так, но знай - ты всё равно кринж! 😂")


async def roulette_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сыграть в рулетку"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or f"User_{user_id}"

    if not is_chat_allowed(chat_id):
        return

    # Проверяем аргументы
    if not context.args:
        await update.message.reply_text(
            "🎰 <b>Казино-рулетка</b>\n\n"
            "Использование: /roulette <ставка> [множитель]\n"
            f"Минимальная ставка: {casino_manager.MIN_BET} очко\n"
            "Максимальная ставка: весь твой рейтинг!\n\n"
            "<b>Режим 1: Случайный множитель</b>\n"
            "/roulette 100 - ставка 100 очков\n"
            "💥 x0 (проигрыш) - 40%\n"
            "🎉 x2 (удвоение) - 35%\n"
            "🔥 x3 (утроение) - 15%\n"
            "💎 x5 - 7%\n"
            "🌟 x10 - 3%\n\n"
            "<b>Режим 2: Выбор множителя</b>\n"
            "/roulette 100 2 - ставка 100 на x2 (45% шанс)\n"
            "/roulette 100 3 - ставка 100 на x3 (30% шанс)\n"
            "/roulette 100 5 - ставка 100 на x5 (15% шанс)\n"
            "/roulette 100 10 - ставка 100 на x10 (5% шанс)\n\n"
            "Посмотреть статистику: /casinostats",
            parse_mode='HTML'
        )
        return

    # Парсим ставку
    try:
        bet = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Укажи ставку числом! Например: /roulette 10")
        return
    
    # Проверяем, указан ли множитель
    target_multiplier = None
    if len(context.args) >= 2:
        try:
            target_multiplier = int(context.args[1])
        except ValueError:
            await update.message.reply_text("⚠️ Множитель должен быть числом! Доступны: 2, 3, 5, 10")
            return

    # Получаем текущий рейтинг
    user_rating = rating_manager.get_user_rating(chat_id, user_id)

    if user_rating == 0:
        await update.message.reply_text(
            "😔 У тебя 0 очков рейтинга!\n"
            "Сначала заработай очки, отправляя сообщения в чат."
        )
        return

    # Играем!
    if target_multiplier:
        # Игра с выбранным множителем
        success, multiplier, result, message = casino_manager.play_with_multiplier(
            chat_id, user_id, bet, user_rating, target_multiplier
        )
    else:
        # Обычная игра со случайным множителем
        success, multiplier, result, message = casino_manager.play(
            chat_id, user_id, bet, user_rating
        )

    if not success:
        # Ошибка (кулдаун, недостаточно очков и т.д.)
        await update.message.reply_text(message, parse_mode='HTML')
        return

    # Обновляем рейтинг
    rating_manager.add_rating(
        chat_id, user_id, username,
        points=result,
        reason=f"Рулетка: ставка {bet}, множитель x{multiplier}"
    )

    new_rating = rating_manager.get_user_rating(chat_id, user_id)

    # Формируем ответ с анимацией
    animation = " ".join(casino_manager.SPIN_ANIMATION)
    mode_text = f"(целевой x{target_multiplier})" if target_multiplier else "(случайный)"
    full_message = (
        f"🎰 <b>РУЛЕТКА</b>\n\n"
        f"👤 {username}\n"
        f"💰 Ставка: <b>{bet}</b> очков {mode_text}\n\n"
        f"{animation}\n\n"
        f"{message}\n\n"
        f"⭐ Новый рейтинг: <b>{new_rating}</b> очков"
    )

    await update.message.reply_text(full_message, parse_mode='HTML')

    # Проверяем достижения
    old_rating = new_rating - result
    asyncio.create_task(check_and_unlock_achievements(
        chat_id, user_id, username, old_rating, new_rating
    ))


async def casinostats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику казино"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_chat_allowed(chat_id):
        return
    
    # Проверяем, запрашивается ли глобальная статистика
    show_global = len(context.args) > 0 and context.args[0].lower() in ['global', 'общая', 'all']
    
    if show_global:
        # Показываем глобальную статистику
        message = casino_manager.format_global_stats()
    else:
        # Показываем личную статистику
        stats = casino_manager.get_stats(chat_id, user_id)
        personal_message = casino_manager.format_stats(stats)
        
        # Добавляем подсказку про глобальную статистику
        message = personal_message + "\n\n💡 Глобальная статистика: /casinostats global"

    await update.message.reply_text(message, parse_mode='HTML')


async def post_init(application: Application):
    """Действия после инициализации бота (регистрация команд)"""
    # Запускаем фоновую задачу проверки молчания (manual loop)
    asyncio.create_task(silence_checker_loop(application))
    # Запускаем планировщик ежедневной статистики
    # Запускаем планировщик ежедневной статистики
    asyncio.create_task(daily_stats_scheduler(application))
    # Запускаем планировщик утреннего приветствия (ОТКЛЮЧЕНО)
    # asyncio.create_task(morning_greeting_scheduler(application))


    commands = [
        BotCommand("start", "Начать работу 🚀"),
        BotCommand("help", "Показать справку 📚"),
        BotCommand("settings", "Настройки (стиль, личность) ⚙️"),
        BotCommand("clear", "Очистить историю 🗑"),
        BotCommand("learn", "Обучить бота 🧠"),
        BotCommand("facts", "Что бот запомнил 📋"),
        BotCommand("myinfo", "Что бот знает о вас 👤"),
        BotCommand("rules", "Поведенческие правила 📜"),
        BotCommand("forget_rule", "Удалить правило 🗑️"),
        BotCommand("members", "Список участников 👥"),
        BotCommand("stats", "Статистика активности 📈"),
        BotCommand("rating", "Рейтинг пользователей 🏆"),
        BotCommand("level", "Мой уровень и прогресс 🎮"),
        BotCommand("achievements", "Мои достижения 🏅"),
        BotCommand("roulette", "Казино-рулетка 🎰"),
        BotCommand("casinostats", "Статистика казино 📊"),
        BotCommand("roast", "Подколоть 🔥"),
    ]
    await application.bot.set_my_commands(commands)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")


async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие новых участников"""
    if not update.message or not update.message.new_chat_members:
        return
        
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await update.message.reply_text("Всем ку! Я Чупапи, ваш новый цифровой кент. 😎\nПишите, если что! 🤙")
            continue
            
        mention = f"@{member.username}" if member.username else member.first_name
        welcome_texts = [
            f"О, свежая кровь! {mention}, добро пожаловать в нашу тусовку! 🥳",
            f"Салют, {mention}! Располагайся, чувствуй себя как дома. 🏡",
            f"Эй, {mention}! Надеюсь, ты принес хорошее настроение? 😉"
        ]
        import random
        await update.message.reply_text(random.choice(welcome_texts))

def main():
    """Запуск бота"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Не указан TELEGRAM_BOT_TOKEN в .env файле")
        return

    if not GLM_API_KEY:
        print("❌ Не указан GLM_API_KEY в .env файле")
        return

    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("members", members_command))
    application.add_handler(CommandHandler("userinfo", userinfo_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("learn", learn_command))
    application.add_handler(CommandHandler("forget", forget_command))
    application.add_handler(CommandHandler("facts", facts_command))
    application.add_handler(CommandHandler("myinfo", myinfo_command))
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("forget_rule", forget_rule_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("rating", rating_command))
    application.add_handler(CommandHandler("level", level_command))
    application.add_handler(CommandHandler("achievements", achievements_command))
    application.add_handler(CommandHandler("roast", roast_command))
    application.add_handler(CommandHandler("roulette", roulette_command))
    application.add_handler(CommandHandler("casino", roulette_command))  # Алиас
    application.add_handler(CommandHandler("casinostats", casinostats_command))

    # Обработчики callback'ов с фильтрами по паттернам
    application.add_handler(CallbackQueryHandler(roast_callback, pattern='^roast_'))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern='^(set_|toggle_)'))

    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Приветствие новых участников
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))

    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем бота
    print("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
