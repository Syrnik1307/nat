#!/bin/bash
# =============================================================================
# migrate_to_5000_users.sh - Скрипт миграции для масштабирования до 5000 users
# =============================================================================
# Использование: 
#   chmod +x migrate_to_5000_users.sh
#   sudo ./migrate_to_5000_users.sh
# =============================================================================

set -e  # Выход при ошибке

echo "=============================================="
echo "  Teaching Panel - Migration to 5000+ Users  "
echo "=============================================="

# Проверка root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите с sudo: sudo ./migrate_to_5000_users.sh"
    exit 1
fi

PROJECT_DIR="/var/www/teaching_panel"
VENV_DIR="$PROJECT_DIR/venv"
DJANGO_DIR="$PROJECT_DIR/teaching_panel"
ENV_FILE="$PROJECT_DIR/.env"

# =============================================================================
# STEP 1: Install PostgreSQL
# =============================================================================
echo ""
echo "📦 Step 1: Installing PostgreSQL..."

if ! command -v psql &> /dev/null; then
    apt update
    apt install -y postgresql postgresql-contrib python3-dev libpq-dev
    systemctl enable postgresql
    systemctl start postgresql
    echo "✅ PostgreSQL installed"
else
    echo "✅ PostgreSQL already installed"
fi

# =============================================================================
# STEP 2: Create PostgreSQL Database
# =============================================================================
echo ""
echo "🗄️ Step 2: Creating PostgreSQL database..."

# Генерируем безопасный пароль
DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)

sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='teaching_panel'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER teaching_panel WITH PASSWORD '$DB_PASSWORD';"

sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname='teaching_panel'" | grep -q 1 || \
    sudo -u postgres createdb teaching_panel -O teaching_panel

echo "✅ PostgreSQL database created"
echo "   User: teaching_panel"
echo "   Password: $DB_PASSWORD"

# =============================================================================
# STEP 3: Install Redis
# =============================================================================
echo ""
echo "📦 Step 3: Installing Redis..."

if ! command -v redis-cli &> /dev/null; then
    apt install -y redis-server
    systemctl enable redis-server
    systemctl start redis-server
    echo "✅ Redis installed"
else
    echo "✅ Redis already installed"
fi

# Проверка Redis
redis-cli ping > /dev/null && echo "✅ Redis is running" || echo "❌ Redis not responding"

# =============================================================================
# STEP 4: Install Python dependencies
# =============================================================================
echo ""
echo "📦 Step 4: Installing Python dependencies..."

source "$VENV_DIR/bin/activate"
pip install psycopg2-binary redis django-redis celery --quiet
echo "✅ Python dependencies installed"

# =============================================================================
# STEP 5: Backup SQLite
# =============================================================================
echo ""
echo "💾 Step 5: Backing up SQLite database..."

BACKUP_DIR="$PROJECT_DIR/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).json"
SQLITE_BACKUP="$BACKUP_DIR/db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)"

if [ -f "$DJANGO_DIR/db.sqlite3" ]; then
    cp "$DJANGO_DIR/db.sqlite3" "$SQLITE_BACKUP"
    echo "✅ SQLite file backed up to: $SQLITE_BACKUP"
    
    cd "$DJANGO_DIR"
    python manage.py dumpdata --natural-foreign --natural-primary -o "$BACKUP_FILE"
    echo "✅ Data exported to: $BACKUP_FILE"
else
    echo "⚠️ No SQLite database found"
fi

# =============================================================================
# STEP 6: Update .env
# =============================================================================
echo ""
echo "⚙️ Step 6: Updating .env configuration..."

# Backup .env
cp "$ENV_FILE" "$ENV_FILE.backup_$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true

# Добавляем новые переменные если их нет
grep -q "DATABASE_URL" "$ENV_FILE" || echo "DATABASE_URL=postgres://teaching_panel:$DB_PASSWORD@localhost:5432/teaching_panel" >> "$ENV_FILE"
grep -q "REDIS_URL" "$ENV_FILE" || echo "REDIS_URL=redis://127.0.0.1:6379/1" >> "$ENV_FILE"
grep -q "CELERY_BROKER_URL" "$ENV_FILE" || echo "CELERY_BROKER_URL=redis://127.0.0.1:6379/0" >> "$ENV_FILE"

echo "✅ .env updated"

# =============================================================================
# STEP 7: Run migrations
# =============================================================================
echo ""
echo "🔄 Step 7: Running database migrations..."

cd "$DJANGO_DIR"
source "$VENV_DIR/bin/activate"
python manage.py migrate

echo "✅ Migrations applied"

# =============================================================================
# STEP 8: Load data
# =============================================================================
echo ""
echo "📥 Step 8: Loading data into PostgreSQL..."

if [ -f "$BACKUP_FILE" ]; then
    python manage.py loaddata "$BACKUP_FILE"
    echo "✅ Data loaded successfully"
else
    echo "⚠️ No backup file to load"
fi

# =============================================================================
# STEP 9: Create Celery systemd service
# =============================================================================
echo ""
echo "⚙️ Step 9: Creating Celery systemd service..."

cat > /etc/systemd/system/celery.service << 'EOF'
[Unit]
Description=Celery Service for Teaching Panel
After=network.target redis-server.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/teaching_panel/teaching_panel
EnvironmentFile=/var/www/teaching_panel/.env
ExecStart=/var/www/teaching_panel/venv/bin/celery -A teaching_panel multi start worker \
    --pidfile=/run/celery/%n.pid \
    --logfile=/var/log/celery/%n%I.log \
    --loglevel=INFO \
    --concurrency=4

ExecStop=/var/www/teaching_panel/venv/bin/celery -A teaching_panel multi stopwait worker \
    --pidfile=/run/celery/%n.pid

ExecReload=/var/www/teaching_panel/venv/bin/celery -A teaching_panel multi restart worker \
    --pidfile=/run/celery/%n.pid \
    --logfile=/var/log/celery/%n%I.log \
    --loglevel=INFO \
    --concurrency=4

Restart=always
RuntimeDirectory=celery
RuntimeDirectoryMode=755

[Install]
WantedBy=multi-user.target
EOF

mkdir -p /run/celery /var/log/celery
chown www-data:www-data /run/celery /var/log/celery

systemctl daemon-reload
systemctl enable celery
systemctl start celery

echo "✅ Celery service created and started"

# =============================================================================
# STEP 10: Update Gunicorn configuration
# =============================================================================
echo ""
echo "⚙️ Step 10: Updating Gunicorn for higher load..."

# Создаём override для systemd
mkdir -p /etc/systemd/system/teaching_panel.service.d/

cat > /etc/systemd/system/teaching_panel.service.d/scale.conf << 'EOF'
[Service]
ExecStart=
ExecStart=/var/www/teaching_panel/venv/bin/gunicorn teaching_panel.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 9 \
    --threads 4 \
    --worker-class gthread \
    --timeout 120 \
    --graceful-timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
EOF

systemctl daemon-reload
systemctl restart teaching_panel

echo "✅ Gunicorn updated (9 workers, 4 threads each)"

# =============================================================================
# STEP 11: Verify services
# =============================================================================
echo ""
echo "🔍 Step 11: Verifying all services..."

echo -n "PostgreSQL: "
systemctl is-active postgresql && echo "✅" || echo "❌"

echo -n "Redis: "
systemctl is-active redis-server && echo "✅" || echo "❌"

echo -n "Celery: "
systemctl is-active celery && echo "✅" || echo "❌"

echo -n "Gunicorn: "
systemctl is-active teaching_panel && echo "✅" || echo "❌"

echo -n "Nginx: "
systemctl is-active nginx && echo "✅" || echo "❌"

# =============================================================================
# STEP 12: Test API
# =============================================================================
echo ""
echo "🧪 Step 12: Testing API..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/ 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "401" ]; then
    echo "✅ API responding (HTTP $HTTP_CODE)"
else
    echo "⚠️ API returned HTTP $HTTP_CODE"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "=============================================="
echo "  Migration Complete!                        "
echo "=============================================="
echo ""
echo "📊 New Configuration:"
echo "   - Database: PostgreSQL"
echo "   - Cache: Redis"
echo "   - Workers: 9 Gunicorn + 4 threads each"
echo "   - Task Queue: Celery"
echo ""
echo "📁 Backup files:"
echo "   - SQLite: $SQLITE_BACKUP"
echo "   - JSON: $BACKUP_FILE"
echo ""
echo "🔐 Database credentials (save securely!):"
echo "   - User: teaching_panel"
echo "   - Password: $DB_PASSWORD"
echo "   - Connection: postgres://teaching_panel:***@localhost:5432/teaching_panel"
echo ""
echo "📝 Next steps:"
echo "   1. Test all functionality manually"
echo "   2. Run load test: locust -f locustfile.py --host=https://lectio.space"
echo "   3. Monitor logs: journalctl -u teaching_panel -f"
echo ""
echo "=============================================="
