#!/bin/bash
# Скрипт автоматического развертывания бота на VPS

echo "🚀 Начинаем развертывание бота на VPS..."

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Переменные
VPS_HOST="155.212.209.24"
VPS_USER="root"
VPS_PASSWORD="dftTjv&Y5t1U"
BOT_DIR="/root/bot"

echo -e "${YELLOW}1. Подключение к VPS...${NC}"

# Создаем временный expect скрипт
cat > /tmp/deploy_bot.exp << 'EXPECT_EOF'
#!/usr/bin/expect -f
set timeout 300
set host [lindex $argv 0]
set user [lindex $argv 1]
set password [lindex $argv 2]
set bot_dir [lindex $argv 3]

spawn ssh -o StrictHostKeyChecking=no $user@$host

expect {
    "password:" {
        send "$password\r"
        exp_continue
    }
    "# " {
        send "echo '✅ Подключено к VPS'\r"
        expect "# "

        # Проверка и установка Python
        send "python3 --version\r"
        expect "# "

        send "which pip3 || (apt update && apt install -y python3-pip)\r"
        expect "# "

        # Создание директории для бота
        send "mkdir -p $bot_dir\r"
        expect "# "

        send "cd $bot_dir\r"
        expect "# "

        send "echo '✅ Директория создана: $bot_dir'\r"
        expect "# "

        send "pwd\r"
        expect "# "

        send "exit\r"
    }
    timeout {
        puts "Timeout!"
        exit 1
    }
    eof {
        puts "Connection closed"
        exit 0
    }
}

expect eof
EXPECT_EOF

chmod +x /tmp/deploy_bot.exp

# Выполняем expect скрипт
if command -v expect &> /dev/null; then
    /tmp/deploy_bot.exp "$VPS_HOST" "$VPS_USER" "$VPS_PASSWORD" "$BOT_DIR"
else
    echo -e "${RED}❌ expect не установлен. Устанавливаю...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install expect 2>/dev/null || echo "Установите expect: brew install expect"
    else
        apt-get install -y expect 2>/dev/null || yum install -y expect 2>/dev/null
    fi
fi

echo -e "${YELLOW}2. Копирование файлов на VPS...${NC}"

# Создаем скрипт для SCP с expect
cat > /tmp/scp_files.exp << 'EXPECT_EOF'
#!/usr/bin/expect -f
set timeout 300
set host [lindex $argv 0]
set user [lindex $argv 1]
set password [lindex $argv 2]
set local_file [lindex $argv 3]
set remote_path [lindex $argv 4]

spawn scp -o StrictHostKeyChecking=no $local_file $user@$host:$remote_path

expect {
    "password:" {
        send "$password\r"
        expect eof
    }
    timeout {
        puts "Timeout!"
        exit 1
    }
}
EXPECT_EOF

chmod +x /tmp/scp_files.exp

# Копируем архив
/tmp/scp_files.exp "$VPS_HOST" "$VPS_USER" "$VPS_PASSWORD" \
    "./bot_deploy.tar.gz" "$BOT_DIR/bot_deploy.tar.gz"

echo -e "${YELLOW}3. Распаковка и установка зависимостей...${NC}"

# Создаем скрипт установки на сервере
cat > /tmp/install_bot.exp << 'EXPECT_EOF'
#!/usr/bin/expect -f
set timeout 300
set host [lindex $argv 0]
set user [lindex $argv 1]
set password [lindex $argv 2]
set bot_dir [lindex $argv 3]

spawn ssh -o StrictHostKeyChecking=no $user@$host

expect {
    "password:" {
        send "$password\r"
        exp_continue
    }
    "# " {
        send "cd $bot_dir\r"
        expect "# "

        send "tar -xzf bot_deploy.tar.gz\r"
        expect "# "

        send "echo '✅ Файлы распакованы'\r"
        expect "# "

        send "pip3 install -r requirements.txt\r"
        expect "# "

        send "echo '✅ Зависимости установлены'\r"
        expect "# "

        # Создаем systemd service
        send "cat > /etc/systemd/system/telegram-bot.service << 'SERVICE_EOF'\n"
        send "\[Unit\]\n"
        send "Description=Telegram Bot Chupapi\n"
        send "After=network.target\n\n"
        send "\[Service\]\n"
        send "Type=simple\n"
        send "User=root\n"
        send "WorkingDirectory=$bot_dir\n"
        send "ExecStart=/usr/bin/python3 $bot_dir/bot.py\n"
        send "Restart=always\n"
        send "RestartSec=10\n\n"
        send "\[Install\]\n"
        send "WantedBy=multi-user.target\n"
        send "SERVICE_EOF\n"
        expect "# "

        send "systemctl daemon-reload\r"
        expect "# "

        send "systemctl enable telegram-bot\r"
        expect "# "

        send "systemctl start telegram-bot\r"
        expect "# "

        send "sleep 2\r"
        expect "# "

        send "systemctl status telegram-bot --no-pager\r"
        expect "# "

        send "echo '✅ Бот запущен как systemd служба'\r"
        expect "# "

        send "echo '📊 Команды для управления ботом:'\r"
        expect "# "
        send "echo '  systemctl status telegram-bot  - статус'\r"
        expect "# "
        send "echo '  systemctl restart telegram-bot - перезапуск'\r"
        expect "# "
        send "echo '  systemctl stop telegram-bot    - остановка'\r"
        expect "# "
        send "echo '  journalctl -u telegram-bot -f  - логи'\r"
        expect "# "

        send "exit\r"
    }
    timeout {
        puts "Timeout!"
        exit 1
    }
}

expect eof
EXPECT_EOF

chmod +x /tmp/install_bot.exp
/tmp/install_bot.exp "$VPS_HOST" "$VPS_USER" "$VPS_PASSWORD" "$BOT_DIR"

echo -e "${GREEN}✅ Развертывание завершено!${NC}"
echo -e "${YELLOW}Бот работает на VPS: $VPS_HOST${NC}"
echo ""
echo "📋 Полезные команды:"
echo "  ssh root@$VPS_HOST"
echo "  systemctl status telegram-bot"
echo "  journalctl -u telegram-bot -f"

# Очистка временных файлов
rm -f /tmp/deploy_bot.exp /tmp/scp_files.exp /tmp/install_bot.exp
