#!/bin/bash
# Скрипт для добавления Google Meet credentials на сервер
# Запустите: ssh tp 'bash -s' < setup_google_meet.sh

set -e

echo "=== Настройка Google Meet Integration ==="
echo ""

# Запросить credentials
read -p "GOOGLE_MEET_CLIENT_ID: " CLIENT_ID
read -p "GOOGLE_MEET_CLIENT_SECRET: " CLIENT_SECRET

REDIRECT_URI="https://lectiospace.ru/api/integrations/google-meet/callback/"

# Проверить что override.conf существует
OVERRIDE_FILE="/etc/systemd/system/teaching_panel.service.d/override.conf"
if [ ! -f "$OVERRIDE_FILE" ]; then
    echo "Creating override directory..."
    sudo mkdir -p /etc/systemd/system/teaching_panel.service.d
    echo "[Service]" | sudo tee "$OVERRIDE_FILE" > /dev/null
fi

# Проверить есть ли уже GOOGLE_MEET переменные
if grep -q "GOOGLE_MEET_ENABLED" "$OVERRIDE_FILE"; then
    echo "Google Meet variables already exist in $OVERRIDE_FILE"
    echo "Updating..."
    sudo sed -i '/GOOGLE_MEET/d' "$OVERRIDE_FILE"
fi

# Добавить переменные
echo "Adding Google Meet environment variables..."
{
    echo "Environment=\"GOOGLE_MEET_ENABLED=1\""
    echo "Environment=\"GOOGLE_MEET_CLIENT_ID=$CLIENT_ID\""
    echo "Environment=\"GOOGLE_MEET_CLIENT_SECRET=$CLIENT_SECRET\""
    echo "Environment=\"GOOGLE_MEET_REDIRECT_URI=$REDIRECT_URI\""
} | sudo tee -a "$OVERRIDE_FILE" > /dev/null

echo ""
echo "=== Environment variables added ==="
cat "$OVERRIDE_FILE"
echo ""

# Перезапустить сервис
echo "Reloading systemd and restarting service..."
sudo systemctl daemon-reload
sudo systemctl restart teaching_panel

echo ""
echo "=== Done! ==="
echo "Google Meet integration is now enabled."
echo "Check status: sudo systemctl status teaching_panel"
echo ""
echo "Users can now connect Google Meet at:"
echo "https://lectiospace.ru/profile?tab=platforms"
