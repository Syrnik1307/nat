#!/bin/bash
# ============================================================
# Offsite DB Backup — загрузка бэкапа на Google Drive
# ============================================================
# Использует уже настроенную GDrive интеграцию проекта.
# Хранит последние 14 бэкапов на GDrive, остальные удаляет.
#
# Установка:
#   scp offsite_backup.sh tp:/opt/lectio-monitor/
#   chmod +x /opt/lectio-monitor/offsite_backup.sh
#   Добавить в cron: 30 3 * * * /opt/lectio-monitor/offsite_backup.sh
#
# ============================================================

set -uo pipefail

CONFIG="/opt/lectio-monitor/config.env"
[[ -f "$CONFIG" ]] && source "$CONFIG"

PROJECT_ROOT="${PROJECT_ROOT:-/var/www/teaching_panel}"
BACKUP_DIR="/var/backups/teaching_panel"
LOG_FILE="/var/log/lectio-monitor/offsite_backup.log"
ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"
KEEP_REMOTE=14  # Хранить последние N бэкапов на GDrive

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(timestamp)] $1" >> "$LOG_FILE"; }

send_alert() {
    local msg="$1"
    if [[ -n "$ERRORS_BOT_TOKEN" && -n "$ERRORS_CHAT_ID" ]]; then
        curl -s --max-time 10 \
            "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${ERRORS_CHAT_ID}" \
            -d "text=${msg}" \
            -d "parse_mode=HTML" > /dev/null 2>&1 || true
    fi
}

# Найти свежий бэкап (создаётся cron в 3:00)
# Поддерживаем оба формата: pg_backup_*.sql.gz (PostgreSQL) и db_backup_*.sqlite3.gz (legacy SQLite)
LATEST_BACKUP=$(find "$BACKUP_DIR" \( -name "pg_backup_*.sql.gz" -o -name "db_backup_*.sqlite3.gz" \) -mtime -1 2>/dev/null | sort -r | head -1)

if [[ -z "$LATEST_BACKUP" ]]; then
    log "ERROR: Свежий бэкап не найден в $BACKUP_DIR"
    send_alert "<b>Offsite Backup FAILED</b>

Свежий бэкап БД не найден!
Проверь cron backup_db.sh

<i>$(timestamp)</i>"
    exit 1
fi

BACKUP_NAME=$(basename "$LATEST_BACKUP")
BACKUP_SIZE=$(stat -c %s "$LATEST_BACKUP" 2>/dev/null || echo 0)
BACKUP_SIZE_HUMAN=$(numfmt --to=iec-i --suffix=B "$BACKUP_SIZE" 2>/dev/null || echo "${BACKUP_SIZE} bytes")

log "Uploading $BACKUP_NAME ($BACKUP_SIZE_HUMAN)..."

# Загрузить через Python + GDrive API (используем уже настроенный токен)
export BACKUP_FILE="$LATEST_BACKUP"
export KEEP_REMOTE
UPLOAD_RESULT=$(cd "$PROJECT_ROOT/teaching_panel" && source ../venv/bin/activate && python3 << 'PYEOF'
import os, sys, json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django.conf import settings

BACKUP_FILE = os.environ.get('BACKUP_FILE', '')
KEEP_REMOTE = int(os.environ.get('KEEP_REMOTE', '14'))

if not BACKUP_FILE:
    print('ERROR: BACKUP_FILE not set')
    sys.exit(1)

try:
    token_path = getattr(settings, 'GDRIVE_TOKEN_FILE', 'gdrive_token.json')
    with open(token_path) as f:
        token_data = json.load(f)
    
    creds = Credentials(
        token=token_data['token'],
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret'),
        scopes=token_data.get('scopes', ['https://www.googleapis.com/auth/drive.file'])
    )
    
    service = build('drive', 'v3', credentials=creds)
    
    # Найти или создать папку DB_Backups
    ROOT_FOLDER = getattr(settings, 'GDRIVE_ROOT_FOLDER_ID', None) or \
                  getattr(settings, 'GDRIVE_RECORDINGS_FOLDER_ID', None)
    
    query = f"name='DB_Backups' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if ROOT_FOLDER:
        query += f" and '{ROOT_FOLDER}' in parents"
    
    results = service.files().list(q=query, fields='files(id,name)', spaces='drive').execute()
    files = results.get('files', [])
    
    if files:
        folder_id = files[0]['id']
    else:
        meta = {
            'name': 'DB_Backups',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if ROOT_FOLDER:
            meta['parents'] = [ROOT_FOLDER]
        folder = service.files().create(body=meta, fields='id').execute()
        folder_id = folder['id']
        print(f'CREATED_FOLDER:{folder_id}')
    
    # Загрузить бэкап
    file_name = os.path.basename(BACKUP_FILE)
    media = MediaFileUpload(BACKUP_FILE, mimetype='application/gzip', resumable=True)
    file_meta = {
        'name': file_name,
        'parents': [folder_id]
    }
    uploaded = service.files().create(body=file_meta, media_body=media, fields='id,name,size').execute()
    print(f'UPLOADED:{uploaded["name"]}:{uploaded.get("size","?")}')
    
    # Удалить старые (оставить последние KEEP_REMOTE)
    all_backups = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields='files(id,name,createdTime)',
        orderBy='createdTime desc',
        pageSize=100
    ).execute().get('files', [])
    
    deleted = 0
    for old_file in all_backups[KEEP_REMOTE:]:
        service.files().delete(fileId=old_file['id']).execute()
        deleted += 1
    
    if deleted:
        print(f'CLEANED:{deleted}')
    
    print('OK')

except Exception as e:
    print(f'ERROR:{e}')
    sys.exit(1)
PYEOF
)

UPLOAD_STATUS=$?

log "Result: $UPLOAD_RESULT"

if echo "$UPLOAD_RESULT" | grep -q "^OK$"; then
    UPLOADED_LINE=$(echo "$UPLOAD_RESULT" | grep "^UPLOADED:" | head -1)
    CLEANED_LINE=$(echo "$UPLOAD_RESULT" | grep "^CLEANED:" | head -1)
    log "SUCCESS: $BACKUP_NAME uploaded to GDrive. ${CLEANED_LINE:-no cleanup needed}"
else
    log "FAILED: $UPLOAD_RESULT"
    send_alert "<b>Offsite Backup FAILED</b>

Файл: $BACKUP_NAME ($BACKUP_SIZE_HUMAN)
Ошибка: $(echo "$UPLOAD_RESULT" | tail -3)

<i>$(timestamp)</i>"
    exit 1
fi
