#!/usr/bin/expect -f

set timeout 60

# Upload file using SCP
spawn scp -o StrictHostKeyChecking=no bot_humanization_update.tar.gz root@155.212.209.24:/root/bot/

expect {
    "password:" {
        send "dftTjv&Y5t1U\r"
    }
}

expect eof

# Now SSH and deploy
spawn ssh root@155.212.209.24

expect {
    "password:" {
        send "dftTjv&Y5t1U\r"
    }
}

expect "# "
send "cd /root/bot\r"

expect "# "
send "echo '🛑 Останавливаю бота...'\r"

expect "# "
send "pkill -f 'python.*bot.py'\r"

expect "# "
send "sleep 2\r"

expect "# "
send "echo '💾 Создаю backup...'\r"

expect "# "
send "mkdir -p backup_\$(date +%Y%m%d_%H%M%S)\r"

expect "# "
send "cp bot.py persona.py backup_*/ 2>/dev/null || true\r"

expect "# "
send "echo '📦 Распаковываю обновление...'\r"

expect "# "
send "tar -xzf bot_humanization_update.tar.gz\r"

expect "# "
send "echo '✅ Файлы распакованы, проверяю:'\r"

expect "# "
send "ls -lh mood_manager.py human_behavior.py\r"

expect "# "
send "echo '🔍 Проверяю синтаксис...'\r"

expect "# "
send "python3 -m py_compile mood_manager.py && python3 -m py_compile human_behavior.py && echo '✅ Синтаксис OK'\r"

expect "# "
send "echo '🚀 Запускаю бота...'\r"

expect "# "
send "cd /root/bot && nohup python3 bot.py > bot.log 2>&1 &\r"

expect "# "
send "sleep 3\r"

expect "# "
send "echo '📊 Проверяю процесс:'\r"

expect "# "
send "ps aux | grep 'python.*bot.py' | grep -v grep\r"

expect "# "
send "echo ''\r"

expect "# "
send "echo '═══════════════════════════════════════════════'\r"

expect "# "
send "echo '✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!'\r"

expect "# "
send "echo '═══════════════════════════════════════════════'\r"

expect "# "
send "echo 'Новые функции:'\r"

expect "# "
send "echo '  ✅ Система настроения (mood_manager.py)'\r"

expect "# "
send "echo '  ✅ Контекст времени суток'\r"

expect "# "
send "echo '  ✅ Естественные паузы'\r"

expect "# "
send "echo '  ✅ Опечатки и паразиты'\r"

expect "# "
send "echo ''\r"

expect "# "
send "echo '📝 Последние 15 строк лога:'\r"

expect "# "
send "tail -15 bot.log\r"

expect "# "
send "exit\r"

expect eof
