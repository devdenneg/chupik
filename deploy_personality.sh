#!/usr/bin/expect -f

set timeout 60

spawn scp -o StrictHostKeyChecking=no bot_personality_messages.tar.gz root@155.212.209.24:/root/bot/

expect {
    "password:" {
        send "dftTjv&Y5t1U\r"
    }
}

expect eof

spawn ssh root@155.212.209.24

expect {
    "password:" {
        send "dftTjv&Y5t1U\r"
    }
}

expect "# "
send "cd /root/bot && pkill -f 'python.*bot.py' && sleep 2\r"

expect "# "
send "tar -xzf bot_personality_messages.tar.gz\r"

expect "# "
send "python3 -m py_compile bot.py && echo 'Syntax OK'\r"

expect "# "
send "nohup python3 bot.py > bot.log 2>&1 &\r"

expect "# "
send "sleep 3 && ps aux | grep 'python.*bot.py' | grep -v grep\r"

expect "# "
send "echo ''\r"

expect "# "
send "echo '✅ ОБНОВЛЕНО: Утро и вечер теперь в стиле Чупапи!'\r"

expect "# "
send "tail -10 bot.log\r"

expect "# "
send "exit\r"

expect eof
