#!/usr/bin/expect -f

set timeout 30

spawn ssh root@155.212.209.24

expect {
    "password:" {
        send "dftTjv&Y5t1U\r"
    }
}

expect "# "
send "cat /etc/systemd/system/telegram-bot.service\r"

expect "# "
send "systemctl stop telegram-bot.service\r"

expect "# "
send "sleep 2\r"

expect "# "
send "ps aux | grep bot.py | grep -v grep\r"

expect "# "
send "cd /root/bot && ls -la image_generator.py bot.py\r"

expect "# "
send "systemctl start telegram-bot.service\r"

expect "# "
send "sleep 5\r"

expect "# "
send "systemctl status telegram-bot.service\r"

expect "# "
send "ps aux | grep bot.py | grep -v grep\r"

expect "# "
send "tail -30 /root/bot/bot.log\r"

expect "# "
send "exit\r"

expect eof
