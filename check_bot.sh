#!/usr/bin/expect -f

set timeout 30

spawn ssh root@155.212.209.24

expect {
    "password:" {
        send "dftTjv&Y5t1U\r"
    }
    "yes/no" {
        send "yes\r"
        exp_continue
    }
}

expect "# "
send "find /root -name \"bot.py\" -type f 2>/dev/null\r"

expect "# "
send "find /root -name \"image_generator.py\" -type f 2>/dev/null\r"

expect "# "
send "ps aux | grep python\r"

expect "# "
send "ps aux | grep bot.py\r"

expect "# "
send "cd /root/bot && ls -la\r"

expect "# "
send "cat /root/bot/image_generator.py 2>/dev/null || echo 'File not found'\r"

expect "# "
send "exit\r"

expect eof
