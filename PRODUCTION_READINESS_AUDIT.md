# 🚀 PRODUCTION READINESS AUDIT - Lectio LMS

> **Дата аудита:** 22 января 2026  
> **Статус:** ⚠️ ТРЕБУЮТСЯ ДЕЙСТВИЯ ПЕРЕД ЗАПУСКОМ  
> **Критических проблем:** 5  
> **Важных улучшений:** 7  

---

## 📊 СВОДКА ТЕКУЩЕГО СОСТОЯНИЯ

| Компонент | Статус | Комментарий |
|-----------|--------|-------------|
| Мониторинг | ⚠️ Частично | Скрипты установлены, **Telegram НЕ настроен** |
| Бэкапы БД | ⚠️ Устарели | Последний бэкап: 30.11.2025 (почти 2 месяца!) |
| Автовосстановление | ✅ Готово | systemd Restart=always, WatchdogSec=60 |
| SSL сертификат | ✅ Готово | Истекает 29.03.2026 (авто-обновление Let's Encrypt) |
| Health checks | ✅ Готово | Cron каждую минуту |
| Firewall | 🔴 КРИТИЧНО | UFW ОТКЛЮЧЕН! |
| Rate Limiting | 🔴 КРИТИЧНО | НЕ НАСТРОЕН в Nginx |
| Fail2Ban | 🔴 КРИТИЧНО | НЕ УСТАНОВЛЕН |
| Django DEBUG | ✅ Готово | DEBUG=False |
| Gunicorn | ✅ Готово | 3 workers, unix socket |
| Диск | ✅ Готово | 42% занято (17GB свободно) |
| RAM | ✅ Готово | 2GB, использовано ~300MB |

---

## 🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ (Исправить ДО запуска!)

### 1. ⚠️ Telegram алерты НЕ работают

**Проблема:** В `/opt/lectio-monitor/config.env` остались placeholder'ы:
```
TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID="YOUR_CHAT_ID_HERE"
```

**Риск:** Ты НЕ узнаешь, если сайт упадёт ночью/на выходных!

**Решение:**
```bash
# 1. Создай бота через @BotFather в Telegram
# 2. Получи chat_id: отправь боту сообщение, затем открой:
#    https://api.telegram.org/bot<TOKEN>/getUpdates
# 3. Обнови конфиг:
ssh tp "sudo nano /opt/lectio-monitor/config.env"
# Замени:
# TELEGRAM_BOT_TOKEN="1234567890:ABC..."
# TELEGRAM_CHAT_ID="-1001234567890"  (если группа, с минусом!)

# 4. Проверь:
ssh tp "/opt/lectio-monitor/health_check.sh"
```

---

### 2. 🔴 Бэкапы БД НЕ создаются

**Проблема:** Последний бэкап от 30 ноября 2025! Cron не работает.

**Риск:** Потеря ВСЕХ данных при сбое диска!

**Решение:**
```bash
# Проверь cron:
ssh tp "cat /var/backups/teaching_panel/cron.log | tail -20"

# Вручную запусти бэкап:
ssh tp "/var/www/teaching_panel/teaching_panel/backup_db.sh"

# Исправь cron (если нужно):
ssh tp "crontab -e"
# Убедись есть строка:
# 0 3 * * * /var/www/teaching_panel/teaching_panel/backup_db.sh >> /var/backups/teaching_panel/cron.log 2>&1
```

---

### 3. 🔴 Firewall (UFW) ОТКЛЮЧЕН

**Проблема:** `Status: inactive` - сервер открыт для всех атак!

**Риск:** Любой может сканировать порты, Redis доступен извне если неверно настроен.

**Решение:**
```bash
ssh tp "
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow 10050/tcp  # Zabbix agent
sudo ufw --force enable
sudo ufw status
"
```

---

### 4. 🔴 Нет Rate Limiting в Nginx

**Проблема:** Нет защиты от DDoS и брутфорса.

**Риск:** Один злоумышленник может положить сайт или перебрать пароли.

**Решение:** Добавь в Nginx конфиг:

```nginx
# В /etc/nginx/nginx.conf в блоке http {}:
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=1r/s;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

# В /etc/nginx/sites-available/lectio (внутри server {}):
# Для API:
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    limit_conn conn_limit 10;
    # ... остальное
}

# Для логина (усиленная защита):
location /api/jwt/token/ {
    limit_req zone=login_limit burst=5 nodelay;
    # ... остальное
}
```

---

### 5. 🔴 Fail2Ban НЕ установлен

**Проблема:** Нет защиты от брутфорса SSH и приложения.

**Риск:** Подбор паролей SSH, множественные попытки логина.

**Решение:**
```bash
ssh tp "
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
"

# Создай конфиг для Django:
ssh tp "sudo tee /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled = true
maxretry = 5
bantime = 3600

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
logpath = /var/log/nginx/error.log
EOF"

ssh tp "sudo systemctl restart fail2ban"
```

---

## ⚠️ ВАЖНЫЕ УЛУЧШЕНИЯ (Рекомендуется до запуска)

### 6. ALLOWED_HOSTS не включает lectio.tw1.ru

**Текущее:**
```
ALLOWED_HOSTS=lectio.space,www.lectio.space,72.56.81.163,127.0.0.1,localhost
```

**Проблема:** `lectio.tw1.ru` отсутствует, хотя сайт на нём работает!

**Решение:**
```bash
ssh tp "sed -i 's/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=lectio.space,www.lectio.space,lectio.tw1.ru,72.56.81.163,127.0.0.1,localhost/' /var/www/teaching_panel/teaching_panel/.env"
ssh tp "sudo systemctl restart teaching_panel"
```

---

### 7. Zoom и YooKassa НЕ настроены

**Проблема:** Переменные окружения пустые.

**Если нужны до запуска:**
```bash
ssh tp "nano /var/www/teaching_panel/teaching_panel/.env"
# Добавить:
# ZOOM_ACCOUNT_ID=...
# ZOOM_CLIENT_ID=...
# ZOOM_CLIENT_SECRET=...
# YOOKASSA_ACCOUNT_ID=...
# YOOKASSA_SECRET_KEY=...
```

---

### 8. Добавить offsite бэкапы

**Проблема:** Бэкапы хранятся на том же сервере. При поломке диска - потеряешь всё!

**Решение:** Добавь в `backup_db.sh`:
```bash
# В конец скрипта, после создания бэкапа:
# Отправка на удалённый сервер/облако
# Вариант 1: rclone в Google Drive/S3
# rclone copy "${BACKUP_FILE}.gz" remote:teaching_panel_backups/

# Вариант 2: rsync на другой сервер
# rsync -avz "${BACKUP_FILE}.gz" backup@backup-server:/backups/
```

---

### 9. Настроить systemd OnFailure уведомления

**Текущее:** OnFailure не настроен (закомментирован).

**Решение:**
```bash
ssh tp "
# Обнови teaching_panel.service:
sudo sed -i '/\[Unit\]/a OnFailure=failure-notifier@%n.service' /etc/systemd/system/teaching_panel.service
sudo systemctl daemon-reload
"
```

---

### 10. Логирование ошибок Django

Проверь что ошибки пишутся в файл:
```python
# В settings.py должен быть LOGGING:
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/teaching_panel/django_error.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
        },
    },
}
```

---

### 11. Мониторинг дискового пространства

Health check уже проверяет диск, но добавь алерт при 80%:
```bash
# Уже есть в health_check.sh, убедись что MIN_FREE_DISK_PERCENT=10 
# означает алерт при > 90% занято
```

---

### 12. Google Drive токен может истечь

**Проблема:** `gdrive_token.json` имеет refresh_token, но он может быть отозван.

**Рекомендация:** Создай процедуру ручного обновления токена и задокументируй.

---

## 📋 ЧЕКЛИСТ ПЕРЕД ЗАПУСКОМ

```
[ ] 1. Настроить Telegram бота и обновить config.env
[ ] 2. Запустить бэкап вручную и проверить cron
[ ] 3. Включить UFW firewall
[ ] 4. Добавить rate limiting в Nginx
[ ] 5. Установить и настроить Fail2Ban
[ ] 6. Добавить lectio.tw1.ru в ALLOWED_HOSTS
[ ] 7. Настроить Zoom/YooKassa (если нужны)
[ ] 8. Настроить offsite бэкапы (Google Drive/S3)
[ ] 9. Протестировать автовосстановление:
      ssh tp "sudo systemctl stop teaching_panel && sleep 10 && systemctl is-active teaching_panel"
[ ] 10. Протестировать Telegram алерты:
      ssh tp "/opt/lectio-monitor/health_check.sh --test-alert"
```

---

## 🔧 АВТОМАТИЗАЦИЯ: ЧТО УЖЕ РАБОТАЕТ

✅ **Автоперезапуск сервиса** - systemd Restart=always + WatchdogSec=60  
✅ **Health checks** - cron каждую минуту, проверяет HTTP, сервисы, диск  
✅ **Ротация логов** - logrotate настроен для lectio-monitor  
✅ **Auto-updates** - unattended-upgrades включен  
✅ **SSL авто-обновление** - Let's Encrypt certbot  

---

## 🚨 RUNBOOK: ЧТО ДЕЛАТЬ ЕСЛИ ВСЁ СЛОМАЛОСЬ

### Сайт не открывается

```bash
# 1. Проверь сервисы:
ssh tp "systemctl status teaching_panel nginx"

# 2. Перезапусти:
ssh tp "sudo systemctl restart teaching_panel nginx"

# 3. Проверь логи:
ssh tp "sudo journalctl -u teaching_panel -n 50"
ssh tp "sudo tail -50 /var/log/nginx/error.log"
```

### База данных повреждена

```bash
# 1. Останови сервис:
ssh tp "sudo systemctl stop teaching_panel"

# 2. Найди последний бэкап:
ssh tp "ls -la /var/backups/teaching_panel/"

# 3. Восстанови:
ssh tp "
cd /var/www/teaching_panel/teaching_panel
cp db.sqlite3 db.sqlite3.broken
gunzip -c /var/backups/teaching_panel/db_backup_YYYYMMDD_HHMMSS.sqlite3.gz > db.sqlite3
sudo systemctl start teaching_panel
"
```

### Диск заполнен

```bash
# 1. Найди что занимает место:
ssh tp "du -sh /var/www/teaching_panel/* | sort -h"

# 2. Очисти логи:
ssh tp "sudo journalctl --vacuum-size=100M"

# 3. Удали старые бэкапы:
ssh tp "find /var/backups -name '*.gz' -mtime +7 -delete"
```

### SSL сертификат истёк

```bash
ssh tp "sudo certbot renew --force-renewal && sudo systemctl restart nginx"
```

---

## 📞 КОНТАКТЫ НА СЛУЧАЙ ЧП

| Проблема | Куда обращаться |
|----------|-----------------|
| Хостинг | [Твой хостер - добавить контакты] |
| Домен | [Регистратор домена] |
| Zoom API | https://marketplace.zoom.us/support |
| YooKassa | https://yookassa.ru/support |

---

## 🎯 ПОСЛЕ ЭТИХ ИСПРАВЛЕНИЙ

Система будет:
- ✅ Автоматически восстанавливаться после падений
- ✅ Слать тебе Telegram при любых проблемах
- ✅ Защищена от DDoS и брутфорса
- ✅ Иметь бэкапы каждый день
- ✅ Работать без твоего участия 99% времени

**Время на исправления:** ~2-3 часа

---

*Последнее обновление: 22 января 2026*
