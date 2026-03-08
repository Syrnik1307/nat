#!/bin/bash
#
# PostgreSQL backup for Teaching Panel (LectioSpace)
# Runs daily via cron at 3:00 AM
#
# Creates: pg_backup_YYYYMMDD_HHMMSS.sql.gz
# Verifies: restore to temp DB, row counts, gzip integrity
# Cleans: backups older than RETENTION_DAYS
#

set -o pipefail

# --- Configuration ---
DB_NAME="teaching_panel"
DB_USER="teaching_panel"
DB_HOST="localhost"
DB_PORT="5432"
BACKUP_DIR="/var/backups/teaching_panel"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/pg_backup_${DATE}.sql.gz"
LOGFILE="$BACKUP_DIR/backup.log"
VERIFY_DB="_backup_verify_${DATE}"

# Telegram alerts (from monitoring config)
CONFIG="/opt/lectio-monitor/config.env"
[[ -f "$CONFIG" ]] && source "$CONFIG"
ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

mkdir -p "$BACKUP_DIR"

# --- Helpers ---
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

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

cleanup_verify_db() {
    sudo -u postgres dropdb --if-exists "$VERIFY_DB" 2>/dev/null || true
}

fail() {
    log "FATAL: $1"
    cleanup_verify_db
    send_alert "<b>DB Backup FAILED</b>

$1

<i>$(date '+%Y-%m-%d %H:%M:%S')</i>"
    exit 1
}

# --- Step 1: pg_dump ---
log "=== PostgreSQL backup started ==="
log "Database: $DB_NAME, Host: $DB_HOST"

if ! command -v pg_dump &>/dev/null; then
    fail "pg_dump not found"
fi

# Get pre-backup row counts for verification
PRE_USERS=$(sudo -u postgres psql -d "$DB_NAME" -t -c "SELECT count(*) FROM accounts_customuser;" 2>/dev/null | tr -d ' ')
PRE_TABLES=$(sudo -u postgres psql -d "$DB_NAME" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')
PRE_LESSONS=$(sudo -u postgres psql -d "$DB_NAME" -t -c "SELECT count(*) FROM schedule_lesson;" 2>/dev/null | tr -d ' ' || echo "0")
log "Pre-backup counts: ${PRE_TABLES} tables, ${PRE_USERS} users, ${PRE_LESSONS} lessons"

# Dump with pg_dump (custom format is better but sql.gz is more portable)
log "Running pg_dump..."
sudo -u postgres pg_dump \
    --dbname="$DB_NAME" \
    --no-owner \
    --no-privileges \
    --format=plain \
    --verbose \
    2>>"$LOGFILE" | gzip -9 > "$BACKUP_FILE"

if [[ $? -ne 0 || ! -s "$BACKUP_FILE" ]]; then
    fail "pg_dump failed or produced empty file"
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
BACKUP_BYTES=$(stat -c %s "$BACKUP_FILE" 2>/dev/null || echo 0)
log "Dump created: $BACKUP_FILE ($BACKUP_SIZE)"

# --- Step 2: gzip integrity ---
log "Verifying gzip integrity..."
if ! gunzip -t "$BACKUP_FILE" 2>/dev/null; then
    fail "gzip integrity check failed for $BACKUP_FILE"
fi
log "gzip integrity: OK"

# --- Step 3: Check SQL content ---
log "Checking SQL content..."
SQL_TABLES=$(gunzip -c "$BACKUP_FILE" | grep -c "^CREATE TABLE" || echo 0)
SQL_HAS_DATA=$(gunzip -c "$BACKUP_FILE" | grep -c "^COPY " || echo 0)
if [[ "$SQL_TABLES" -lt 10 ]]; then
    fail "Dump has only $SQL_TABLES CREATE TABLE statements (expected 100+)"
fi
if [[ "$SQL_HAS_DATA" -lt 10 ]]; then
    fail "Dump has only $SQL_HAS_DATA COPY statements (no data?)"
fi
log "SQL content: $SQL_TABLES tables, $SQL_HAS_DATA data sections"

# --- Step 4: Restore to temporary DB ---
log "Restoring to temp DB '$VERIFY_DB' for verification..."
cleanup_verify_db

if ! sudo -u postgres createdb "$VERIFY_DB" 2>>"$LOGFILE"; then
    fail "Could not create verification DB '$VERIFY_DB'"
fi

RESTORE_OUTPUT=$(gunzip -c "$BACKUP_FILE" | sudo -u postgres psql -d "$VERIFY_DB" 2>&1)
RESTORE_ERRORS=$(echo "$RESTORE_OUTPUT" | grep -ci "error" || true)
RESTORE_ERRORS=${RESTORE_ERRORS:-0}
if [[ "$RESTORE_ERRORS" -gt 5 ]]; then
    log "WARNING: $RESTORE_ERRORS errors during restore (some are OK for roles/grants)"
fi

# --- Step 5: Verify row counts in restored DB ---
log "Verifying data in restored DB..."
POST_USERS=$(sudo -u postgres psql -d "$VERIFY_DB" -t -c "SELECT count(*) FROM accounts_customuser;" 2>/dev/null | tr -d ' ')
POST_TABLES=$(sudo -u postgres psql -d "$VERIFY_DB" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')
POST_LESSONS=$(sudo -u postgres psql -d "$VERIFY_DB" -t -c "SELECT count(*) FROM schedule_lesson;" 2>/dev/null | tr -d ' ' || echo "0")

log "Restored counts: ${POST_TABLES} tables, ${POST_USERS} users, ${POST_LESSONS} lessons"

# Verify counts match
VERIFIED=true
if [[ "$POST_USERS" != "$PRE_USERS" ]]; then
    log "MISMATCH: users $PRE_USERS (live) vs $POST_USERS (backup)"
    VERIFIED=false
fi
if [[ "$POST_TABLES" != "$PRE_TABLES" ]]; then
    log "MISMATCH: tables $PRE_TABLES (live) vs $POST_TABLES (backup)"
    VERIFIED=false
fi
if [[ "$POST_LESSONS" != "$PRE_LESSONS" ]]; then
    log "MISMATCH: lessons $PRE_LESSONS (live) vs $POST_LESSONS (backup)"
    VERIFIED=false
fi

# Cleanup temp DB
cleanup_verify_db

if [[ "$VERIFIED" != "true" ]]; then
    fail "Data verification failed! Row counts don't match between live and backup."
fi
log "Data verification: PASSED (all counts match)"

# --- Step 6: Cleanup old backups ---
log "Cleaning backups older than $RETENTION_DAYS days..."
# Clean old pg backups
find "$BACKUP_DIR" -name "pg_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null

# --- Step 7: Summary ---
PG_COUNT=$(ls -1 "$BACKUP_DIR"/pg_backup_*.sql.gz 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
log "Total backups: $PG_COUNT pg_dump files, dir size: $TOTAL_SIZE"
log "=== Backup completed successfully ==="
log ""

exit 0
exit 0
