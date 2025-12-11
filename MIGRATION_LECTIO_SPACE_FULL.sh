#!/bin/bash
# 🌐 ПОЛНАЯ ИНСТРУКЦИЯ ДЛЯ МИГРАЦИИ НА lectio.space
# Выполняй команды в указанном порядке на СЕРВЕРЕ

# ============================================================
# ЭТАП 1: SSL СЕРТИФИКАТ (Let's Encrypt)
# ============================================================
echo "📝 ЭТАП 1: Установка SSL сертификата"
echo "=========================================="

# Если certbot не установлен:
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# Получить сертификат
sudo certbot certonly --standalone -d lectio.space -d www.lectio.space

# Ответить на вопросы:
# - Enter email: твой email
# - Согласиться с terms: Y
# - Share email (опционально): N или Y

echo "✅ SSL сертификат установлен!"
echo "   Путь: /etc/letsencrypt/live/lectio.space/"
echo ""

# ============================================================
# ЭТАП 2: ПОДГОТОВКА ФАЙЛОВ
# ============================================================
echo "📝 ЭТАП 2: Копирование конфиг файлов"
echo "=========================================="

# Копируем файлы с локальной машины на сервер:
# scp -r /path/to/nat/lectio_space_nginx.conf user@server:/tmp/
# scp -r /path/to/nat/.env.production user@server:/tmp/

echo "⚠️  ВЫПОЛНИ НА ЛОКАЛЬНОЙ МАШИНЕ:"
echo "  scp lectio_space_nginx.conf user@YOUR_SERVER_IP:/tmp/"
echo "  scp .env.production user@YOUR_SERVER_IP:/tmp/"
echo ""
echo "Затем продолжи на сервере..."
echo ""

# ============================================================
# ЭТАП 3: ОБНОВЛЕНИЕ КОНФИГОВ И ДЕПЛОЙ
# ============================================================
echo "📝 ЭТАП 3: Главный деплой"
echo "=========================================="

# Войди на сервер по SSH и выполни:

cd /var/www/teaching_panel

# Обновить код
sudo -u www-data git pull origin main

# Обновить .env
sudo -u www-data cp /tmp/.env.production teaching_panel/.env

# Активировать окружение
source ../venv/bin/activate

# Генерировать SECRET_KEY
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
echo "SECRET_KEY=$SECRET_KEY" >> teaching_panel/.env

# Установить зависимости
pip install -r teaching_panel/requirements.txt --quiet

# Миграции
cd teaching_panel
python manage.py migrate --noinput

# Collectstatic
python manage.py collectstatic --noinput --clear

# Обновить Nginx конфиг
cd /var/www/teaching_panel
sudo cp /tmp/lectio_space_nginx.conf /etc/nginx/sites-available/lectio.space
sudo ln -sf /etc/nginx/sites-available/lectio.space /etc/nginx/sites-enabled/lectio.space
sudo rm -f /etc/nginx/sites-enabled/default

# Проверить синтаксис Nginx
sudo nginx -t

# Перезапустить сервисы
sudo systemctl restart teaching_panel
sudo systemctl restart nginx

echo "✅ ДЕПЛОЙ ЗАВЕРШЕН!"
echo ""

# ============================================================
# ЭТАП 4: ПРОВЕРКА
# ============================================================
echo "📝 ЭТАП 4: Проверка"
echo "=========================================="

# Проверить статус сервисов
sudo systemctl status teaching_panel --no-pager | head -10
sudo systemctl status nginx --no-pager | head -10

# Проверить логи
echo ""
echo "📋 Последние логи Django:"
sudo journalctl -u teaching_panel -n 20 --no-pager

# Проверить доступность
curl -I https://lectio.space
echo ""
echo "🌍 Сайт должен быть доступен по: https://lectio.space"
echo ""

# ============================================================
# ДОПОЛНИТЕЛЬНО: Auto-renewal SSL
# ============================================================
echo "📝 ЭТАП 5 (опционально): Auto-renewal SSL"
echo "=========================================="
echo "Сертификат автоматически обновляется через certbot timer"
echo "Проверить: sudo systemctl status certbot.timer"
echo ""
