# Push Telegram monitoring config to production without storing secrets in repo.
# Prompts for TELEGRAM_BOT_TOKEN securely and reuses ADMIN_PAYMENT_TELEGRAM_CHAT_ID from prod.

$ErrorActionPreference = 'Stop'

function Get-PlainTextFromSecureString([Security.SecureString]$Secure) {
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

Write-Host "Configuring Telegram monitoring on prod (tp)..."

$secureToken = Read-Host "Enter TELEGRAM_BOT_TOKEN (input hidden)" -AsSecureString
$token = Get-PlainTextFromSecureString $secureToken
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "TELEGRAM_BOT_TOKEN is empty"
}

# Fetch admin chat id from prod service env (do not print value)
$adminChatId = (ssh tp "systemctl show teaching_panel -p Environment --no-pager | sed 's/^Environment=//' | tr ' ' '\n' | grep '^ADMIN_PAYMENT_TELEGRAM_CHAT_ID=' | head -1 | cut -d= -f2-" ).Trim()
if ([string]::IsNullOrWhiteSpace($adminChatId)) {
    throw "ADMIN_PAYMENT_TELEGRAM_CHAT_ID not found on prod (teaching_panel env)"
}

$config = @(
    '# Managed by scripts/push_monitoring_telegram.ps1'
    "TELEGRAM_BOT_TOKEN=`"$token`""
    "TELEGRAM_CHAT_ID=`"$adminChatId`""
    ''
    'SITE_URL="https://lectio.tw1.ru"'
    'API_URL="https://lectio.tw1.ru/api/health/"'
    'PROJECT_ROOT="/var/www/teaching_panel"'
    'FRONTEND_BUILD="/var/www/teaching_panel/frontend/build"'
    'BACKEND_SERVICE="teaching_panel"'
    'NGINX_SERVICE="nginx"'
    'LOG_DIR="/var/log/lectio-monitor"'
) -join "`n"

# Send config via stdin (token not present in command line)
$config | ssh tp "sudo tee /opt/lectio-monitor/config.env >/dev/null"
ssh tp "sudo chown root:root /opt/lectio-monitor/config.env && sudo chmod 600 /opt/lectio-monitor/config.env"

# Test alert and show last log lines (no secrets)
ssh tp "sudo /opt/lectio-monitor/health_check.sh --test-alert >/dev/null 2>&1 || true; tail -10 /var/log/lectio-monitor/health.log"

Write-Host "Done. If you did not receive a Telegram message, check bot permissions and that the chat_id is correct."