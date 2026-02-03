# ============================================================
# 🚀 ONE-LINER для деплоя (копируй и вставь в SSH на сервер)
# ============================================================

# ВАРИАНТ 1: Через tmux (самый надежный)
ssh user@YOUR_SERVER_IP << 'DEPLOY_END'
set -e
echo "🚀 Начинаю деплой lectiospace.ru..."

# 1. Git pull
cd /var/www/teaching_panel && sudo -u www-data git pull origin main

# 2. Обновить .env
cat > teaching_panel/.env << 'ENV_END'
DEBUG=False
ALLOWED_HOSTS=lectiospace.ru,www.lectiospace.ru,127.0.0.1
CORS_EXTRA=https://lectiospace.ru,https://www.lectiospace.ru
FRONTEND_URL=https://lectiospace.ru
GDRIVE_ROOT_FOLDER_ID=1u1V9O-enN0tAYj98zy40yinB84yyi8IB
USE_GDRIVE_STORAGE=1
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
ENV_END

# 3. Генерировать SECRET_KEY
source ../venv/bin/activate
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
echo "SECRET_KEY=$SECRET_KEY" >> teaching_panel/.env

# 4. Pip install + Миграции + Collectstatic
cd teaching_panel && pip install -r requirements.txt --quiet && python manage.py migrate --noinput && python manage.py collectstatic --noinput --clear

# 5. Nginx
cd .. && sudo cp /tmp/lectio_space_nginx.conf /etc/nginx/sites-available/lectiospace.ru 2>/dev/null || sudo tee /etc/nginx/sites-available/lectiospace.ru > /dev/null << 'NGINX_END'
upstream django { server 127.0.0.1:8000; }
server { listen 80; server_name lectiospace.ru www.lectiospace.ru; return 301 https://$server_name$request_uri; }
server {
  listen 443 ssl http2; server_name lectiospace.ru www.lectiospace.ru;
  ssl_certificate /etc/letsencrypt/live/lectiospace.ru/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/lectiospace.ru/privkey.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  client_max_body_size 500M;
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  location /static/ { alias /var/www/teaching_panel/teaching_panel/staticfiles/; expires 30d; }
  location /media/ { alias /var/www/teaching_panel/teaching_panel/media/; expires 7d; }
  location / {
    proxy_pass http://django;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 60s;
    proxy_read_timeout 300s;
  }
}
NGINX_END

sudo ln -sf /etc/nginx/sites-available/lectiospace.ru /etc/nginx/sites-enabled/lectiospace.ru
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t

# 6. Restart services
sudo systemctl restart teaching_panel nginx

echo "✅ ДЕПЛОЙ ЗАВЕРШЕН!"
echo "🌍 Проверь: https://lectiospace.ru"
DEPLOY_END


# ============================================================
# ВАРИАНТ 2: Стандартная SSH команда (если Вариант 1 не работает)
# ============================================================

ssh user@YOUR_SERVER_IP "cd /var/www/teaching_panel && \
sudo -u www-data git pull origin main && \
cd teaching_panel && \
source ../venv/bin/activate && \
pip install -r requirements.txt --quiet && \
python manage.py migrate --noinput && \
python manage.py collectstatic --noinput --clear && \
cd .. && \
sudo systemctl restart teaching_panel nginx && \
echo '✅ Деплой завершен!'"


# ============================================================
# ЧТО НУЖНО СДЕЛАТЬ ПЕРЕД ЭТИМ:
# ============================================================

# 1. Скопировать конфиги с локальной машины
# (выполни НА ЛОКАЛЬНОЙ МАШИНЕ):
scp lectio_space_nginx.conf user@YOUR_SERVER_IP:/tmp/
scp .env.production user@YOUR_SERVER_IP:/tmp/

# 2. На сервере установить SSL сертификат (ONE-TIME):
ssh user@YOUR_SERVER_IP << 'SSL_END'
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot certonly --standalone -d lectiospace.ru -d www.lectiospace.ru
SSL_END

# 3. Ответить на вопросы certbot:
#    - Email: твой email
#    - Agree to terms: Y
#    - Share email: N (опционально)

# ============================================================
# ПОСЛЕ ДЕПЛОЯ - ПРОВЕРКА
# ============================================================

# Проверить статус
ssh user@YOUR_SERVER_IP "sudo systemctl status teaching_panel nginx --no-pager"

# Посмотреть логи
ssh user@YOUR_SERVER_IP "sudo journalctl -u teaching_panel -f"

# Открыть в браузере
# https://lectiospace.ru
