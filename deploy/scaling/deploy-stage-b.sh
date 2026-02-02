#!/bin/bash
# =============================================================================
# Deploy Script for Stage B (Growth)
# Target: 750 teachers / 7,500 students
# Server: 4 vCPU / 8 GB RAM
# REQUIRES: PgBouncer installation
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE_DIR="$SCRIPT_DIR/stage-b"
PGBOUNCER_DIR="$SCRIPT_DIR/pgbouncer"

echo "======================================"
echo "  Deploying Stage B Configuration"
echo "  (750 teachers / 7,500 students)"
echo "======================================"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (sudo)"
   exit 1
fi

# Check PgBouncer
if ! command -v pgbouncer &> /dev/null; then
    echo ""
    echo "⚠️  PgBouncer not installed!"
    echo "   Install with: apt install pgbouncer"
    echo ""
    read -p "Continue without PgBouncer? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Backup existing configs
BACKUP_DIR="/tmp/tp-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "[1/7] Backing up current configurations..."
cp /etc/systemd/system/teaching_panel.service "$BACKUP_DIR/" 2>/dev/null || true
cp /etc/systemd/system/celery*.service "$BACKUP_DIR/" 2>/dev/null || true
cp /etc/pgbouncer/pgbouncer.ini "$BACKUP_DIR/" 2>/dev/null || true

echo "[2/7] Installing systemd services..."
cp "$STAGE_DIR/teaching_panel.service" /etc/systemd/system/
cp "$STAGE_DIR/celery-default.service" /etc/systemd/system/
cp "$STAGE_DIR/celery-heavy.service" /etc/systemd/system/

# Remove old single celery service if exists
rm -f /etc/systemd/system/celery.service

echo "[3/7] Installing PgBouncer configuration..."
if [ -f /etc/pgbouncer/pgbouncer.ini ]; then
    echo "⚠️  PgBouncer config exists. Update manually from:"
    echo "   $PGBOUNCER_DIR/pgbouncer.ini"
else
    cp "$PGBOUNCER_DIR/pgbouncer.ini" /etc/pgbouncer/
fi

echo "[4/7] Creating userlist.txt template..."
if [ ! -f /etc/pgbouncer/userlist.txt ]; then
    echo '# Add your database user here' > /etc/pgbouncer/userlist.txt
    echo '# Format: "username" "md5password"' >> /etc/pgbouncer/userlist.txt
    echo "⚠️  Edit /etc/pgbouncer/userlist.txt with your credentials"
fi

echo "[5/7] Reloading systemd..."
systemctl daemon-reload

echo "[6/7] Restarting services..."
# Start PgBouncer first if available
systemctl restart pgbouncer 2>/dev/null || echo "PgBouncer not configured"
sleep 2

systemctl restart teaching_panel
systemctl restart celery-default
systemctl restart celery-heavy
systemctl restart celery-beat

# Enable new services
systemctl enable celery-default
systemctl enable celery-heavy

echo "[7/7] Verifying services..."
sleep 3
systemctl status teaching_panel --no-pager || true
systemctl status celery-default --no-pager || true
systemctl status celery-heavy --no-pager || true
systemctl status pgbouncer --no-pager || true

echo ""
echo "======================================"
echo "  Stage B Deployment Complete!"
echo "======================================"
echo ""
echo "Backup saved to: $BACKUP_DIR"
echo ""
echo "⚠️  Manual steps required:"
echo ""
echo "1. Update DATABASE_URL in .env to use PgBouncer:"
echo "   DATABASE_URL=postgresql://user:pass@127.0.0.1:6432/teaching_panel"
echo ""
echo "2. Configure PgBouncer userlist:"
echo "   Edit /etc/pgbouncer/userlist.txt"
echo ""
echo "3. Apply PostgreSQL tuning:"
echo "   cat $STAGE_DIR/postgresql.conf >> /etc/postgresql/*/main/conf.d/99-tuning.conf"
echo "   systemctl restart postgresql"
echo ""
echo "To rollback:"
echo "  cp $BACKUP_DIR/*.service /etc/systemd/system/"
echo "  systemctl daemon-reload && systemctl restart teaching_panel celery celery-beat"
