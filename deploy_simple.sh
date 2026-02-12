#!/bin/bash
# Простой скрипт развертывания (для копирования на сервер)

echo "🚀 Установка бота на VPS..."

# Обновление системы
apt update
apt install -y python3 python3-pip

# Создание директории
mkdir -p /root/bot
cd /root/bot

# Установка зависимостей Python
cat > requirements.txt << 'EOF'
python-telegram-bot
httpx
python-dotenv
EOF

pip3 install -r requirements.txt

# Создание systemd service
cat > /etc/systemd/system/telegram-bot.service << 'EOF'
[Unit]
Description=Telegram Bot Chupapi
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/bot
ExecStart=/usr/bin/python3 /root/bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Активация и запуск службы
systemctl daemon-reload
systemctl enable telegram-bot
systemctl start telegram-bot

echo "✅ Бот установлен и запущен!"
echo ""
echo "📊 Команды для управления:"
echo "  systemctl status telegram-bot  - статус"
echo "  systemctl restart telegram-bot - перезапуск"
echo "  systemctl stop telegram-bot    - остановка"
echo "  journalctl -u telegram-bot -f  - логи"
