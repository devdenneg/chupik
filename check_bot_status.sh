#!/usr/bin/expect -f

set timeout 30

spawn ssh root@155.212.209.24

expect {
    "password:" {
        send "dftTjv&Y5t1U\r"
    }
}

expect "# "
send "cd /root/bot\r"

expect "# "
send "ps aux | grep bot.py | grep -v grep\r"

expect "# "
send "sleep 5\r"

expect "# "
send "tail -30 bot.log\r"

expect "# "
send "python3 -c 'import sys; sys.path.insert(0, \"/root/bot\"); from image_generator import image_generator; print(\"Image generator module loaded successfully\")'\r"

expect "# "
send "exit\r"

expect eof
