#!/bin/bash
# Скрипт развертывания обновления очеловечивания на VPS

set -e

VPS_IP="155.212.209.24"
VPS_USER="root"
VPS_BOT_PATH="/root/bot"
ARCHIVE="bot_humanization_update.tar.gz"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   Развертывание обновления очеловечивания бота на VPS         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Проверяем наличие архива
if [ ! -f "$ARCHIVE" ]; then
    echo "❌ Архив $ARCHIVE не найден!"
    echo "Создаю архив..."
    tar -czf "$ARCHIVE" \
        mood_manager.py \
        human_behavior.py \
        bot.py \
        persona.py \
        mood_state.json \
        HUMANIZATION_GUIDE.md \
        IMPLEMENTATION_REPORT.md
    echo "✅ Архив создан"
fi

echo "📦 Копирую файлы на VPS..."
scp "$ARCHIVE" ${VPS_USER}@${VPS_IP}:${VPS_BOT_PATH}/

echo ""
echo "📂 Распаковываю на VPS и перезапускаю бота..."
ssh ${VPS_USER}@${VPS_IP} << 'ENDSSH'
cd /root/bot

# Останавливаем бота
echo "🛑 Останавливаю бота..."
pkill -f "python3 bot.py" || true
sleep 2

# Создаем backup
echo "💾 Создаю backup старых файлов..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp bot.py persona.py "$BACKUP_DIR/" 2>/dev/null || true

# Распаковываем
echo "📦 Распаковываю новые файлы..."
tar -xzf bot_humanization_update.tar.gz

# Проверяем синтаксис
echo "🔍 Проверяю синтаксис..."
python3 -m py_compile mood_manager.py
python3 -m py_compile human_behavior.py
python3 -m py_compile bot.py
python3 -m py_compile persona.py

echo "✅ Синтаксис корректен"

# Запускаем бота
echo "🚀 Запускаю бота..."
nohup python3 bot.py > bot.log 2>&1 &
sleep 3

# Проверяем что запустился
if pgrep -f "python3 bot.py" > /dev/null; then
    echo "✅ Бот успешно запущен!"
    echo "📊 PID: $(pgrep -f 'python3 bot.py')"
else
    echo "❌ Ошибка запуска бота. Смотрите bot.log"
    tail -20 bot.log
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              ✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Проверьте логи: tail -f /root/bot/bot.log"
echo "📊 Статус бота: ps aux | grep bot.py"
echo ""
echo "Новые функции:"
echo "  ✅ Система настроения (mood_manager.py)"
echo "  ✅ Контекст времени суток (persona.py)"
echo "  ✅ Естественные паузы перед ответом"
echo "  ✅ Опечатки и словесные паразиты"
echo ""
ENDSSH

echo ""
echo "✅ Развертывание завершено!"
echo ""
