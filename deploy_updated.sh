#!/usr/bin/expect -f

set timeout 300

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
send "cp bot_settings.json bot_settings.json.bak\r"

expect "# "
send "tar -xzf /root/bot_with_images.tar.gz\r"

# Stop current bot
expect "# "
send "pkill -f bot.py\r"

expect "# "
send "sleep 2\r"

# Update balances
expect "# "
send "venv/bin/python update_balance.py --force\r"

expect "# "
send "sleep 2\r"

# Start bot
expect "# "
send "nohup venv/bin/python bot.py > /dev/null 2>&1 &\r"

expect "# "
send "sleep 3\r"

expect "# "
send "ps aux | grep bot.py | grep -v grep\r"

expect "# "
send "exit\r"

expect eof
