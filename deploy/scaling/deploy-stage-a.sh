#!/bin/bash
# =============================================================================
# Deploy Script for Stage A (MVP)
# Target: 300 teachers / 3,000 students
# Server: 2 vCPU / 4 GB RAM
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE_DIR="$SCRIPT_DIR/stage-a"

echo "======================================"
echo "  Deploying Stage A Configuration"
echo "  (300 teachers / 3,000 students)"
echo "======================================"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (sudo)"
   exit 1
fi

# Backup existing configs
BACKUP_DIR="/tmp/tp-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "[1/5] Backing up current configurations..."
cp /etc/systemd/system/teaching_panel.service "$BACKUP_DIR/" 2>/dev/null || true
cp /etc/systemd/system/celery.service "$BACKUP_DIR/" 2>/dev/null || true
cp /etc/systemd/system/celery-beat.service "$BACKUP_DIR/" 2>/dev/null || true

echo "[2/5] Installing systemd services..."
cp "$STAGE_DIR/teaching_panel.service" /etc/systemd/system/
cp "$STAGE_DIR/celery.service" /etc/systemd/system/
cp "$STAGE_DIR/celery-beat.service" /etc/systemd/system/

echo "[3/5] Reloading systemd..."
systemctl daemon-reload

echo "[4/5] Restarting services..."
systemctl restart teaching_panel
systemctl restart celery
systemctl restart celery-beat

echo "[5/5] Verifying services..."
sleep 3
systemctl status teaching_panel --no-pager || true
systemctl status celery --no-pager || true
systemctl status celery-beat --no-pager || true

echo ""
echo "======================================"
echo "  Stage A Deployment Complete!"
echo "======================================"
echo ""
echo "Backup saved to: $BACKUP_DIR"
echo ""
echo "PostgreSQL tuning (apply manually):"
echo "  cat $STAGE_DIR/postgresql.conf"
echo ""
echo "To rollback:"
echo "  cp $BACKUP_DIR/*.service /etc/systemd/system/"
echo "  systemctl daemon-reload && systemctl restart teaching_panel celery celery-beat"
