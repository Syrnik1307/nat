#!/bin/bash
# =============================================================================
# EMERGENCY MEMORY FIX - Снижаем потребление RAM
# =============================================================================
# ПРИЧИНА: OOM Killer убивает Gunicorn workers, сайт недоступен
# ТЕКУЩЕЕ СОСТОЯНИЕ: ~700MB Python процессы на 2GB сервере
# =============================================================================

set -e

echo "=== STEP 1: Проверяем текущую память ==="
free -h
echo ""

echo "=== STEP 2: Останавливаем natbot (сторонний бот, не нужен для LMS) ==="
systemctl stop natbot.service || true
systemctl disable natbot.service || true

echo "=== STEP 3: Увеличиваем лимит памяти для teaching_panel ==="
# Создаём override если нет
mkdir -p /etc/systemd/system/teaching_panel.service.d/

cat > /etc/systemd/system/teaching_panel.service.d/memory_fix.conf << 'EOF'
[Service]
# EMERGENCY FIX 2026-02-02: Увеличиваем лимиты
MemoryMax=600M
MemoryHigh=450M
MemorySwapMax=256M
EOF

echo "=== STEP 4: Перезагружаем systemd ==="
systemctl daemon-reload

echo "=== STEP 5: Перезапускаем сервисы ==="
systemctl restart teaching_panel
sleep 3

echo "=== STEP 6: Проверяем health ==="
curl -s -m 5 http://127.0.0.1:8000/api/health/ && echo "" || echo "STILL DOWN!"

echo ""
echo "=== РЕЗУЛЬТАТ: Новое потребление памяти ==="
free -h
echo ""
ps aux | grep python | grep -v grep | awk '{sum+=$6} END {print "Python processes total: " sum/1024 " MB"}'
