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
send "ls -lh bot.log\r"

expect "# "
send "tail -100 bot.log | head -50\r"

expect "# "
send "echo '--- Testing image_generator import ---'\r"

expect "# "
send "grep -A 2 'from image_generator' bot.py\r"

expect "# "
send "exit\r"

expect eof
