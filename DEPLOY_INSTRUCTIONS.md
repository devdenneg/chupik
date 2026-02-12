# 🚀 Инструкция по развертыванию бота на VPS

## Вариант 1: Автоматическое развертывание (рекомендуется)

### Требования:
- `expect` должен быть установлен на вашем компьютере

### Установка expect:
```bash
# macOS
brew install expect

# Ubuntu/Debian
sudo apt-get install expect

# CentOS/RHEL
sudo yum install expect
```

### Запуск автоматического развертывания:
```bash
cd /Users/negodyaev-dn/Documents/bot
./deploy.sh
```

Скрипт автоматически:
1. Подключится к VPS
2. Создаст директорию `/root/bot`
3. Скопирует все файлы
4. Установит зависимости
5. Настроит systemd службу
6. Запустит бота

---

## Вариант 2: Ручное развертывание

### Шаг 1: Подключение к VPS
```bash
ssh root@155.212.209.24
# Пароль: dftTjv&Y5t1U
```

### Шаг 2: Установка Python и зависимостей
```bash
apt update
apt install -y python3 python3-pip
```

### Шаг 3: Создание директории для бота
```bash
mkdir -p /root/bot
cd /root/bot
```

### Шаг 4: Копирование файлов

**На вашем компьютере (в новом терминале):**
```bash
cd /Users/negodyaev-dn/Documents/bot
scp bot_deploy.tar.gz root@155.212.209.24:/root/bot/
# Введите пароль: dftTjv&Y5t1U
```

**Вернитесь в SSH сессию на VPS:**
```bash
cd /root/bot
tar -xzf bot_deploy.tar.gz
```

### Шаг 5: Установка Python зависимостей
```bash
pip3 install -r requirements.txt
```

### Шаг 6: Создание systemd службы
```bash
cat > /etc/systemd/system/telegram-bot.service << 'EOF'
[Unit]
Description=Telegram Bot Chupapi
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/bot
ExecStart=/usr/bin/python3 /root/bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### Шаг 7: Запуск бота
```bash
systemctl daemon-reload
systemctl enable telegram-bot
systemctl start telegram-bot
```

### Шаг 8: Проверка статуса
```bash
systemctl status telegram-bot
```

---

## Управление ботом на VPS

### Просмотр статуса:
```bash
systemctl status telegram-bot
```

### Просмотр логов в реальном времени:
```bash
journalctl -u telegram-bot -f
```

### Перезапуск бота:
```bash
systemctl restart telegram-bot
```

### Остановка бота:
```bash
systemctl stop telegram-bot
```

### Запуск бота:
```bash
systemctl start telegram-bot
```

### Отключение автозапуска:
```bash
systemctl disable telegram-bot
```

---

## Обновление бота

### Вариант 1: Через архив
```bash
# На вашем компьютере
cd /Users/negodyaev-dn/Documents/bot
tar -czf bot_update.tar.gz bot.py config.py *.py .env

# Копирование на VPS
scp bot_update.tar.gz root@155.212.209.24:/root/bot/

# На VPS
ssh root@155.212.209.24
cd /root/bot
tar -xzf bot_update.tar.gz
systemctl restart telegram-bot
```

### Вариант 2: Через git (если настроен)
```bash
ssh root@155.212.209.24
cd /root/bot
git pull
systemctl restart telegram-bot
```

---

## Полезные команды

### Проверка портов:
```bash
netstat -tuln | grep LISTEN
```

### Проверка процессов Python:
```bash
ps aux | grep python
```

### Освобождение места:
```bash
apt autoremove
apt clean
journalctl --vacuum-time=7d
```

### Мониторинг ресурсов:
```bash
htop
# или
top
```

---

## Решение проблем

### Бот не запускается:
```bash
# Проверьте логи
journalctl -u telegram-bot -n 50

# Проверьте конфигурацию
cat /root/bot/.env

# Проверьте права на файлы
ls -la /root/bot/
```

### Ошибки зависимостей:
```bash
pip3 install --upgrade -r requirements.txt
```

### Проблемы с памятью:
```bash
# Проверка памяти
free -h

# Перезапуск бота
systemctl restart telegram-bot
```

---

## Информация о VPS

**IP:** 155.212.209.24
**Пользователь:** root
**Пароль:** dftTjv&Y5t1U
**Директория бота:** /root/bot
**Служба systemd:** telegram-bot

---

## Безопасность

### Рекомендуется:
1. Сменить пароль root после первого входа
2. Настроить SSH ключи вместо пароля
3. Настроить firewall (ufw)
4. Регулярно обновлять систему

### Смена пароля root:
```bash
passwd
```

### Настройка firewall:
```bash
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```
