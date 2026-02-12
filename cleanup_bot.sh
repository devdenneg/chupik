#!/usr/bin/expect -f

set timeout 60

# Upload file using SCP
spawn scp -o StrictHostKeyChecking=no bot_updated.tar.gz root@155.212.209.24:/root/

expect {
    "password:" {
        send "dftTjv&Y5t1U\r"
    }
}

expect eof

# SSH and deploy
spawn ssh root@155.212.209.24

expect {
    "password:" {
        send "dftTjv&Y5t1U\r"
    }
}

expect "# "
send "cd /root/bot\r"

expect "# "
send "systemctl stop telegram-bot.service\r"

expect "# "
send "sleep 2\r"

expect "# "
send "tar -xzf /root/bot_updated.tar.gz\r"

expect "# "
send "rm -f image_generator.py\r"

expect "# "
send "grep -n 'image_generator\\|send_image' bot.py\r"

expect "# "
send "systemctl start telegram-bot.service\r"

expect "# "
send "sleep 5\r"

expect "# "
send "ps aux | grep bot.py | grep -v grep\r"

expect "# "
send "tail -20 /root/bot/bot.log\r"

expect "# "
send "exit\r"

expect eof
