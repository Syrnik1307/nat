# ============================================================
# Push Errors Bot Config to Production
# ============================================================
# Настраивает отдельный бот для уведомлений об ошибках сайта,
# падениях и восстановлениях
# ============================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$ChatId,

    [Parameter(Mandatory=$false)]
    [string]$BotToken
)

Write-Host "=== Настройка бота ошибок сайта ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Этот бот будет отправлять уведомления о:" -ForegroundColor Yellow
Write-Host "  - Падениях сайта" -ForegroundColor White
Write-Host "  - Восстановлениях сайта" -ForegroundColor White
Write-Host "  - Ошибках при деплое" -ForegroundColor White
Write-Host "  - Проблемах с сервисами" -ForegroundColor White
Write-Host ""

# Токен бота НЕ храним в репозитории. Передавайте через -BotToken или переменную окружения.
$ErrorsBotToken = ($BotToken ?? $env:TP_ERRORS_BOT_TOKEN)

if (-not $ErrorsBotToken) {
    $secureToken = Read-Host "Введите ERRORS_BOT_TOKEN (ввод скрыт)" -AsSecureString
    $ErrorsBotToken = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
    )
}

if (-not $ErrorsBotToken) {
    Write-Host "ERRORS_BOT_TOKEN обязателен!" -ForegroundColor Red
    exit 1
}

# Получаем chat_id если не передан
if (-not $ChatId) {
    Write-Host "Для получения CHAT_ID:" -ForegroundColor Yellow
    Write-Host "1. Напишите боту /start в Telegram" -ForegroundColor White
    Write-Host "2. Или добавьте бота в группу" -ForegroundColor White
    Write-Host ""
    
    # Пробуем получить chat_id автоматически
    Write-Host "Пробуем получить chat_id автоматически..." -ForegroundColor Cyan
    try {
        $updates = Invoke-RestMethod -Uri "https://api.telegram.org/bot$ErrorsBotToken/getUpdates" -Method Get
        if ($updates.ok -and $updates.result.Count -gt 0) {
            $lastUpdate = $updates.result[-1]
            if ($lastUpdate.message) {
                $ChatId = $lastUpdate.message.chat.id.ToString()
                $chatType = $lastUpdate.message.chat.type
                $chatTitle = if ($lastUpdate.message.chat.title) { $lastUpdate.message.chat.title } else { $lastUpdate.message.chat.first_name }
                Write-Host "Найден чат: $chatTitle (тип: $chatType)" -ForegroundColor Green
                Write-Host "Chat ID: $ChatId" -ForegroundColor Green
            }
        }
    } catch {
        Write-Host "Не удалось получить chat_id автоматически" -ForegroundColor Yellow
    }
    
    if (-not $ChatId) {
        $ChatId = Read-Host "Введите CHAT_ID вручную"
    }
}

if (-not $ChatId) {
    Write-Host "CHAT_ID обязателен!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Конфигурация:" -ForegroundColor Cyan
Write-Host "  Bot Token: $($ErrorsBotToken.Substring(0, 10))..." -ForegroundColor White
Write-Host "  Chat ID: $ChatId" -ForegroundColor White
Write-Host ""

# Тестируем отправку
Write-Host "Тестируем отправку..." -ForegroundColor Cyan
$testMessage = @"
🔧 LECTIO ERRORS BOT

Бот ошибок успешно настроен!

Этот бот будет отправлять:
• Уведомления о падениях сайта
• Уведомления о восстановлениях
• Ошибки деплоя
• Проблемы с сервисами

🕐 $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@

try {
    $response = Invoke-RestMethod -Uri "https://api.telegram.org/bot$ErrorsBotToken/sendMessage" -Method Post -Body @{
        chat_id = $ChatId
        text = $testMessage
        parse_mode = "HTML"
    }
    
    if ($response.ok) {
        Write-Host "Тестовое сообщение отправлено!" -ForegroundColor Green
    } else {
        Write-Host "Ошибка отправки: $($response | ConvertTo-Json)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Ошибка: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Обновляем конфигурацию на сервере..." -ForegroundColor Cyan

# Команда для обновления config.env на сервере
$sshCommand = @"
# Проверяем существование файла конфигурации
CONFIG_FILE='/opt/lectio-monitor/config.env'
if [ ! -f `$CONFIG_FILE ]; then
    echo 'Создаём config.env...'
    sudo cp /opt/lectio-monitor/config.env.example `$CONFIG_FILE 2>/dev/null || sudo touch `$CONFIG_FILE
fi

# Обновляем или добавляем ERRORS_BOT_TOKEN
if grep -q '^ERRORS_BOT_TOKEN=' `$CONFIG_FILE; then
    sudo sed -i 's|^ERRORS_BOT_TOKEN=.*|ERRORS_BOT_TOKEN="$ErrorsBotToken"|' `$CONFIG_FILE
else
    echo 'ERRORS_BOT_TOKEN="$ErrorsBotToken"' | sudo tee -a `$CONFIG_FILE > /dev/null
fi

# Обновляем или добавляем ERRORS_CHAT_ID
if grep -q '^ERRORS_CHAT_ID=' `$CONFIG_FILE; then
    sudo sed -i 's|^ERRORS_CHAT_ID=.*|ERRORS_CHAT_ID="$ChatId"|' `$CONFIG_FILE
else
    echo 'ERRORS_CHAT_ID="$ChatId"' | sudo tee -a `$CONFIG_FILE > /dev/null
fi

# Проверяем результат
echo ''
echo '=== Текущая конфигурация ==='
grep -E '^(ERRORS_|TELEGRAM_)' `$CONFIG_FILE | head -10

# Тестируем health_check.sh
echo ''
echo '=== Тест health_check.sh ==='
if [ -x /opt/lectio-monitor/health_check.sh ]; then
    source `$CONFIG_FILE
    echo "ERRORS_BOT_TOKEN: `${ERRORS_BOT_TOKEN:0:15}..."
    echo "ERRORS_CHAT_ID: `$ERRORS_CHAT_ID"
else
    echo 'health_check.sh не найден или не исполняемый'
fi
"@

try {
    $result = ssh tp $sshCommand
    Write-Host $result
    Write-Host ""
    Write-Host "=== Готово! ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Бот ошибок настроен. Теперь при падении сайта вы получите уведомление в Telegram." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Для проверки можно запустить:" -ForegroundColor Yellow
    Write-Host "  ssh tp 'sudo /opt/lectio-monitor/health_check.sh'" -ForegroundColor White
} catch {
    Write-Host "Ошибка SSH: $_" -ForegroundColor Red
    exit 1
}
