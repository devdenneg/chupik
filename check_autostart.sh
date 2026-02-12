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
send "crontab -l | grep bot\r"

expect "# "
send "systemctl list-units --type=service | grep bot\r"

expect "# "
send "ls -la /etc/systemd/system/ | grep bot\r"

expect "# "
send "find /etc -name '*bot*' 2>/dev/null\r"

expect "# "
send "ps aux | grep bot\r"

expect "# "
send "exit\r"

expect eof
