#!/usr/bin/expect -f

set timeout 60

# Upload file using SCP
spawn scp -o StrictHostKeyChecking=no bot_with_images.tar.gz root@155.212.209.24:/root/

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
send "tar -xzf /root/bot_with_images.tar.gz\r"

expect "# "
send "ls -la image_generator.py\r"

expect "# "
send "grep -n 'image_generator' bot.py | head -5\r"

expect "# "
send "pkill -f bot.py\r"

expect "# "
send "sleep 2\r"

expect "# "
send "cd /root/bot && nohup venv/bin/python bot.py > /dev/null 2>&1 &\r"

expect "# "
send "sleep 3\r"

expect "# "
send "ps aux | grep bot.py | grep -v grep\r"

expect "# "
send "tail -20 bot.log\r"

expect "# "
send "exit\r"

expect eof
