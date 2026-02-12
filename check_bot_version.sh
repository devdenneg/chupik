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
send "cd /root/bot && grep -n 'image_generator' bot.py\r"

expect "# "
send "cd /root/bot && grep -n 'ImageGenerator' bot.py\r"

expect "# "
send "cd /root/bot && grep -n 'send_image' bot.py\r"

expect "# "
send "exit\r"

expect eof
