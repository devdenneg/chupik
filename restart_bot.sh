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
send "cd /root\r"

expect "# "
send "ls -la\r"

expect "# "
send "pm2 list\r"

expect "# "
send "pm2 restart all\r"

expect "# "
send "pm2 logs\r"

expect eof
