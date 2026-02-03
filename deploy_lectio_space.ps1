# 🚀 PowerShell скрипт для деплоя lectiospace.ru
# Запусти ЭТУ команду на Windows PowerShell

param(
    [string]$ServerIp = "YOUR_SERVER_IP",
    [string]$ServerUser = "deploy_user"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "⏳ $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

Write-Host "🚀 Начинаю миграцию на lectiospace.ru..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

# 1. Копировать конфиги
Write-Step "Копирую конфиги на сервер..."
scp lectio_space_nginx.conf "${ServerUser}@${ServerIp}:/tmp/" 2>$null
scp .env.production "${ServerUser}@${ServerIp}:/tmp/" 2>$null
Write-Success "Конфиги скопированы"

# 2. Установить SSL (если еще нет)
Write-Step "Проверяю SSL сертификат..."
$sslCheck = ssh "${ServerUser}@${ServerIp}" "test -f /etc/letsencrypt/live/lectiospace.ru/fullchain.pem && echo 'exists' || echo 'missing'"
if ($sslCheck -like "*missing*") {
    Write-Host "⚠️  SSL сертификат не найден!" -ForegroundColor Yellow
    Write-Host "Установи вручную:" -ForegroundColor Yellow
    Write-Host "  ssh user@$ServerIp" -ForegroundColor Cyan
    Write-Host "  sudo certbot certonly --standalone -d lectiospace.ru -d www.lectiospace.ru" -ForegroundColor Cyan
    Read-Host "Нажми Enter когда SSL установлен..."
}
Write-Success "SSL готов"

# 3. Главный деплой
Write-Step "Выполняю деплой..."

$deployScript = @'
set -e
cd /var/www/teaching_panel
sudo -u www-data git pull origin main
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

source ../venv/bin/activate
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
echo "SECRET_KEY=$SECRET_KEY" >> teaching_panel/.env
cd teaching_panel
pip install -r requirements.txt --quiet
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
cd ..
sudo cp /tmp/lectio_space_nginx.conf /etc/nginx/sites-available/lectiospace.ru
sudo ln -sf /etc/nginx/sites-available/lectiospace.ru /etc/nginx/sites-enabled/lectiospace.ru
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart teaching_panel nginx
echo "✅ Деплой завершен!"
'@

ssh "${ServerUser}@${ServerIp}" $deployScript
Write-Success "Деплой завершен!"

# 4. Проверка
Write-Step "Проверяю статус сервисов..."
ssh "${ServerUser}@${ServerIp}" "sudo systemctl status teaching_panel nginx --no-pager | head -20"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ ВСЕ ГОТОВО!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "🌍 Открой браузер: https://lectiospace.ru" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Команды для проверки:" -ForegroundColor Yellow
Write-Host "  ssh ${ServerUser}@${ServerIp} 'sudo systemctl status teaching_panel'" -ForegroundColor Gray
Write-Host "  ssh ${ServerUser}@${ServerIp} 'sudo journalctl -u teaching_panel -f'" -ForegroundColor Gray
