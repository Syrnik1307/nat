#!/bin/bash
# Создаёт ops_bot.env из существующего config.env
BTOKEN=$(grep ERRORS_BOT_TOKEN /opt/lectio-monitor/config.env | cut -d'"' -f2)
CHATID=$(grep ERRORS_CHAT_ID /opt/lectio-monitor/config.env | cut -d'"' -f2)

cat > /opt/lectio-monitor/ops_bot.env << EOF
OPS_BOT_TOKEN="${BTOKEN}"
ADMIN_CHAT_IDS="${CHATID}"
EOF

chmod 600 /opt/lectio-monitor/ops_bot.env

# Обновляем systemd service чтобы использовал новый ops_bot.py
cat > /etc/systemd/system/lectio-ops-bot.service << 'SVCEOF'
[Unit]
Description=Lectio OPS Bot (Telegram site management)
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/lectio-monitor
ExecStart=/var/www/teaching_panel/venv/bin/python3 /opt/lectio-monitor/ops_bot.py
EnvironmentFile=/opt/lectio-monitor/ops_bot.env
Restart=always
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=lectio-ops-bot

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl restart lectio-ops-bot
sleep 3

STATUS=$(systemctl is-active lectio-ops-bot)
echo "STATUS=$STATUS"
echo "CONFIG_OK: token_len=${#BTOKEN} chat_id=$CHATID"
journalctl -u lectio-ops-bot -n 5 --no-pager 2>/dev/null
