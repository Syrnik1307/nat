#!/bin/bash
# =============================================================================
# Deploy Script for Stage C (Scale)
# Target: 1,500 teachers / 15,000 students
# Server: 8 vCPU / 16 GB RAM (or 2x4 vCPU / 8 GB with LB)
# REQUIRES: PgBouncer + Consider managed PostgreSQL
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE_DIR="$SCRIPT_DIR/stage-c"

echo "======================================"
echo "  Deploying Stage C Configuration"
echo "  (1,500 teachers / 15,000 students)"
echo "======================================"
echo ""
echo "⚠️  IMPORTANT: Stage C is for high-load scenarios."
echo "   Consider:"
echo "   - Managed PostgreSQL (RDS/Cloud SQL) with read replicas"
echo "   - Separate Celery worker server for video processing"
echo "   - Redis Cluster for Celery broker"
echo ""
read -p "Continue with deployment? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (sudo)"
   exit 1
fi

# Check PgBouncer
if ! command -v pgbouncer &> /dev/null; then
    echo ""
    echo "❌ PgBouncer is REQUIRED for Stage C!"
    echo "   Install with: apt install pgbouncer"
    exit 1
fi

# Backup existing configs
BACKUP_DIR="/tmp/tp-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "[1/6] Backing up current configurations..."
cp /etc/systemd/system/teaching_panel.service "$BACKUP_DIR/" 2>/dev/null || true
cp /etc/systemd/system/celery*.service "$BACKUP_DIR/" 2>/dev/null || true

echo "[2/6] Installing systemd services..."
cp "$STAGE_DIR/teaching_panel.service" /etc/systemd/system/
cp "$STAGE_DIR/celery-default.service" /etc/systemd/system/
cp "$STAGE_DIR/celery-heavy.service" /etc/systemd/system/

# Remove old services if exists
rm -f /etc/systemd/system/celery.service 2>/dev/null || true

echo "[3/6] Reloading systemd..."
systemctl daemon-reload

echo "[4/6] Restarting services..."
systemctl restart pgbouncer
sleep 2

systemctl restart teaching_panel
systemctl restart celery-default
systemctl restart celery-heavy
systemctl restart celery-beat

# Enable services
systemctl enable celery-default
systemctl enable celery-heavy

echo "[5/6] Verifying services..."
sleep 3
systemctl status teaching_panel --no-pager || true
systemctl status celery-default --no-pager || true
systemctl status celery-heavy --no-pager || true
systemctl status pgbouncer --no-pager || true

echo "[6/6] Health check..."
curl -s http://127.0.0.1:8000/api/health/ || echo "Health check failed!"

echo ""
echo "======================================"
echo "  Stage C Deployment Complete!"
echo "======================================"
echo ""
echo "Backup saved to: $BACKUP_DIR"
echo ""
echo "⚠️  CRITICAL: Review these items:"
echo ""
echo "1. PostgreSQL tuning (APPLY CAREFULLY):"
echo "   Review: cat $STAGE_DIR/postgresql.conf"
echo "   Test on staging first!"
echo ""
echo "2. Consider moving heavy Celery workers to separate server:"
echo "   scp $STAGE_DIR/celery-heavy.service worker-server:/etc/systemd/system/"
echo ""
echo "3. Monitor these metrics:"
echo "   - PostgreSQL connections: SELECT count(*) FROM pg_stat_activity;"
echo "   - Memory usage: free -h"
echo "   - CPU load: top -bn1 | head -5"
echo ""
echo "To rollback:"
echo "  cp $BACKUP_DIR/*.service /etc/systemd/system/"
echo "  systemctl daemon-reload && systemctl restart teaching_panel celery-default celery-heavy celery-beat"
