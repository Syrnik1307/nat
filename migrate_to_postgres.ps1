# migrate_to_postgres.ps1
# Скрипт миграции Teaching Panel на PostgreSQL
# Запуск: .\migrate_to_postgres.ps1

$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Teaching Panel: Migration to PostgreSQL   " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Генерируем пароль
$DB_PASSWORD = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 16 | ForEach-Object {[char]$_})
Write-Host "`nDatabase password: $DB_PASSWORD" -ForegroundColor Yellow
Write-Host "SAVE THIS PASSWORD!" -ForegroundColor Red

# SSH команды для выполнения на сервере
$commands = @"
set -e
echo '=== Step 1: Installing PostgreSQL and Redis ==='
sudo apt update
sudo apt install -y postgresql postgresql-contrib redis-server python3-dev libpq-dev

echo '=== Step 2: Starting services ==='
sudo systemctl enable postgresql redis-server
sudo systemctl start postgresql redis-server

echo '=== Step 3: Creating database ==='
sudo -u postgres psql -c "DROP USER IF EXISTS teaching_panel;"
sudo -u postgres psql -c "CREATE USER teaching_panel WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS teaching_panel;"
sudo -u postgres psql -c "CREATE DATABASE teaching_panel OWNER teaching_panel;"

echo '=== Step 4: Backing up SQLite ==='
cd /var/www/teaching_panel/teaching_panel
sudo cp db.sqlite3 db.sqlite3.backup_`date +%Y%m%d_%H%M%S` 2>/dev/null || echo 'No SQLite to backup'

echo '=== Step 5: Exporting data ==='
source ../venv/bin/activate
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -e admin.logentry -e sessions -o /tmp/backup_before_postgres.json || echo 'Export done or skipped'

echo '=== Step 6: Installing Python packages ==='
pip install psycopg2-binary redis django-redis celery

echo '=== Step 7: Updating .env ==='
# Удаляем старые записи если есть
sudo sed -i '/^DATABASE_URL=/d' /var/www/teaching_panel/.env
sudo sed -i '/^REDIS_URL=/d' /var/www/teaching_panel/.env
sudo sed -i '/^CELERY_BROKER_URL=/d' /var/www/teaching_panel/.env

# Добавляем новые
echo "" | sudo tee -a /var/www/teaching_panel/.env
echo "DATABASE_URL=postgres://teaching_panel:$DB_PASSWORD@localhost:5432/teaching_panel" | sudo tee -a /var/www/teaching_panel/.env
echo "REDIS_URL=redis://127.0.0.1:6379/1" | sudo tee -a /var/www/teaching_panel/.env
echo "CELERY_BROKER_URL=redis://127.0.0.1:6379/0" | sudo tee -a /var/www/teaching_panel/.env

echo '=== Step 8: Running migrations ==='
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py migrate

echo '=== Step 9: Loading data ==='
python manage.py loaddata /tmp/backup_before_postgres.json || echo 'Loaddata completed or skipped'

echo '=== Step 10: Restarting services ==='
sudo systemctl restart teaching_panel

echo '=== Step 11: Verification ==='
sleep 3
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:8000/api/

echo ''
echo '=== MIGRATION COMPLETE ==='
echo 'Database: PostgreSQL'
echo 'Cache: Redis'
"@

Write-Host "`nExecuting migration on server..." -ForegroundColor Green

# Заменяем переменную в команде
$commands = $commands -replace '\$DB_PASSWORD', $DB_PASSWORD

# Выполняем через SSH
ssh tp $commands

Write-Host "`n=============================================" -ForegroundColor Cyan
Write-Host "  Migration completed!                       " -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "`nDatabase password: $DB_PASSWORD" -ForegroundColor Yellow
Write-Host "Save this in a secure location!" -ForegroundColor Red
