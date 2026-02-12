#!/usr/bin/expect -f

set timeout 30

spawn ssh root@155.212.209.24

expect {
    "password:" {
        send "dftTjv&Y5t1U\r"
    }
}

expect "# "
send "pkill -9 -f bot.py\r"

expect "# "
send "sleep 3\r"

expect "# "
send "ps aux | grep bot.py | grep -v grep\r"

expect "# "
send "cd /root/bot && nohup venv/bin/python bot.py > bot.log 2>&1 &\r"

expect "# "
send "sleep 5\r"

expect "# "
send "ps aux | grep bot.py | grep -v grep\r"

expect "# "
send "tail -50 bot.log | grep -E '(Running|ERROR|image_generator|Бот запущен)'\r"

expect "# "
send "exit\r"

expect eof
