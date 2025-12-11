#!/bin/bash
# 🚀 Production Deployment Script для lectio.space
# Это скрипт для запуска на СЕРВЕРЕ (не локально!)

set -e  # Exit on error

echo "🚀 Начинаю миграцию на lectio.space..."
echo "=================================================="

# Переменные
PROJECT_DIR="/var/www/teaching_panel"
VENV_DIR="$PROJECT_DIR/../venv"
DJANGO_DIR="$PROJECT_DIR/teaching_panel"

# 1️⃣ Git pull
echo "📥 Обновляю код из репозитория..."
cd $PROJECT_DIR
sudo -u www-data git pull origin main
echo "✅ Код обновлен"

# 2️⃣ Обновляю .env файл с новыми переменными
echo "🔧 Обновляю .env файл..."
cat > $DJANGO_DIR/.env << 'EOF'
DEBUG=False
ALLOWED_HOSTS=lectio.space,www.lectio.space,127.0.0.1
CORS_EXTRA=https://lectio.space,https://www.lectio.space
FRONTEND_URL=https://lectio.space
GDRIVE_ROOT_FOLDER_ID=1u1V9O-enN0tAYj98zy40yinB84yyi8IB
USE_GDRIVE_STORAGE=1
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
EOF

# Генерирую новый SECRET_KEY
echo "🔐 Генерирую SECRET_KEY..."
source $VENV_DIR/bin/activate
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
echo "SECRET_KEY=$SECRET_KEY" >> $DJANGO_DIR/.env
echo "✅ SECRET_KEY добавлен в .env"

# 3️⃣ Pip install
echo "📦 Устанавливаю зависимости..."
cd $DJANGO_DIR
pip install -r requirements.txt --quiet
echo "✅ Зависимости установлены"

# 4️⃣ Миграции БД
echo "🗄️  Применяю миграции БД..."
python manage.py migrate --noinput
echo "✅ Миграции готовы"

# 5️⃣ Collectstatic
echo "📂 Собираю статические файлы..."
python manage.py collectstatic --noinput --clear
echo "✅ Static собраны"

# 6️⃣ Копирую Nginx конфиг
echo "⚙️  Обновляю Nginx конфиг..."
sudo cp /tmp/lectio_space_nginx.conf /etc/nginx/sites-available/lectio.space
sudo ln -sf /etc/nginx/sites-available/lectio.space /etc/nginx/sites-enabled/lectio.space
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t  # Проверяю синтаксис
echo "✅ Nginx конфиг обновлен"

# 7️⃣ Перезапускаю сервисы
echo "🔄 Перезапускаю сервисы..."
sudo systemctl restart teaching_panel
sudo systemctl restart nginx
echo "✅ Сервисы перезапущены"

# 8️⃣ Проверяю статус
echo ""
echo "=================================================="
echo "✅ ДЕПЛОЙ ЗАВЕРШЕН УСПЕШНО!"
echo "=================================================="
echo ""
echo "📊 Статус сервисов:"
sudo systemctl status teaching_panel nginx --no-pager | head -20
echo ""
echo "🌍 Проверь: https://lectio.space"
echo "📝 Логи: sudo journalctl -u teaching_panel -f"
