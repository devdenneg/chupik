#!/usr/bin/expect -f

set timeout 30

spawn ssh root@155.212.209.24

expect {
    "password:" {
        send "dftTjv&Y5t1U\r"
    }
}

expect "# "
send "ps aux | grep bot.py | grep -v grep\r"

expect "# "
send "cd /root/bot && tail -40 bot.log | grep -v 'getUpdates'\r"

expect "# "
send "journalctl -u telegram-bot.service -n 20 --no-pager\r"

expect "# "
send "python3 -c 'import sys; sys.path.insert(0, \"/root/bot\"); from image_generator import image_generator; print(\"✓ Image generator available\"); print(f\"✓ URL: {image_generator.BASE_URL}\")'\r"

expect "# "
send "exit\r"

expect eof
