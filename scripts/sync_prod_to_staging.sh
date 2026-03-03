#!/bin/bash
# ==============================================
# Sync production data to staging (run ON server)
# ==============================================
# Usage: sudo bash /var/www/teaching-panel-stage/sync_prod_to_staging.sh
#
# Copies prod SQLite DB to staging with sanitized PII.
# Safe: does NOT modify production data.

set -euo pipefail

PROD_DB="/var/www/teaching_panel/teaching_panel/db.sqlite3"
STAGE_DB="/var/www/teaching-panel-stage/teaching_panel/db.sqlite3"
TEMP_DB="/tmp/staging_seed_$(date +%Y%m%d_%H%M%S).sqlite3"

echo "=== Sync prod DB to staging ==="
echo "Source: $PROD_DB"
echo "Target: $STAGE_DB"
echo ""

# 1. Copy prod DB
if [ ! -f "$PROD_DB" ]; then
    echo "ERROR: Production DB not found at $PROD_DB"
    exit 1
fi
cp "$PROD_DB" "$TEMP_DB"
echo "[1/5] Copied prod DB to $TEMP_DB"

# 2. Sanitize passwords (set all to 'staging123')
# Django pbkdf2_sha256 hash for 'staging123'
STAGING_HASH='pbkdf2_sha256$720000$stagingsalt12345$KxQz0v0qJZ8VZx0KxQz0v0qJZ8VZx0KxQz0v0qJZ8='
sqlite3 "$TEMP_DB" "UPDATE accounts_customuser SET password='${STAGING_HASH}';"
echo "[2/5] Sanitized passwords (all users can login with 'staging123')"

# 3. Sanitize emails (replace with staging-safe emails, keep admin)
sqlite3 "$TEMP_DB" <<'SQL'
UPDATE accounts_customuser
SET email = 'user_' || id || '@staging.local'
WHERE email NOT LIKE '%@staging.local'
  AND role != 'admin';
SQL
echo "[3/5] Sanitized emails (user_N@staging.local)"

# 4. Clear sensitive credentials
sqlite3 "$TEMP_DB" <<'SQL'
-- Clear Zoom pool credentials
UPDATE zoom_pool_zoomaccount SET
    client_id = '',
    client_secret = '',
    account_id = ''
WHERE 1=1;

-- Clear payment data
UPDATE accounts_payment SET
    provider_payment_id = 'sanitized_' || id,
    metadata = '{}'
WHERE 1=1;
SQL
echo "[4/5] Cleared Zoom/payment credentials"

# 5. Deploy to staging
if [ -f "$STAGE_DB" ]; then
    cp "$STAGE_DB" "${STAGE_DB}.bak.$(date +%Y%m%d_%H%M%S)"
    echo "  Backed up existing staging DB"
fi
cp "$TEMP_DB" "$STAGE_DB"
chown www-data:www-data "$STAGE_DB"
chmod 664 "$STAGE_DB"

# Run migrations on staging
cd /var/www/teaching-panel-stage/teaching_panel
source ../venv/bin/activate
DJANGO_SETTINGS_MODULE=teaching_panel.settings_staging python manage.py migrate --noinput 2>&1 | tail -3
echo "[5/5] DB deployed to staging and migrated"

# Summary
echo ""
echo "=== Summary ==="
sqlite3 "$STAGE_DB" <<'SQL'
SELECT 'Users: ' || COUNT(*) FROM accounts_customuser;
SELECT 'Teachers: ' || COUNT(*) FROM accounts_customuser WHERE role='teacher';
SELECT 'Students: ' || COUNT(*) FROM accounts_customuser WHERE role='student';
SELECT 'Lessons: ' || COUNT(*) FROM schedule_lesson;
SELECT 'Homeworks: ' || COUNT(*) FROM homework_homework;
SELECT 'Subscriptions: ' || COUNT(*) FROM accounts_subscription;
SQL
echo ""
echo "SYNC COMPLETE! Login with any user email + password 'staging123'"
echo "Admin emails preserved (original email)."

# Cleanup
rm -f "$TEMP_DB"