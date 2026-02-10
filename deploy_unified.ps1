# ============================================================
# Teaching Panel - Единый надежный скрипт деплоя
# ============================================================
# Версия: 3.0
# Дата: 7 февраля 2026
# Требования: PowerShell 7+, SSH доступ (алиас 'tp')
# ============================================================
# Фичи:
#   - Полный/backend/frontend/quick деплой
#   - Поддержка production + staging
#   - Telegram уведомления (начало, успех, ошибка)
#   - Расширенный мониторинг (disk, memory, CPU, uptime)
#   - Автоматический бэкап + откат
#   - Атомарный frontend deploy
#   - Health checks + smoke tests
# ============================================================

param(
    [ValidateSet('menu', 'full', 'backend', 'frontend', 'quick', 'rollback', 'status', 'monitor')]
    [string]$Action = 'menu',
    
    [ValidateSet('production', 'staging')]
    [string]$Environment = 'production',
    
    [switch]$SkipHealthCheck,
    [switch]$SkipBackup,
    [switch]$SkipTelegram,
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# ============================================================
# КОНФИГУРАЦИЯ ENVIRONMENTS
# ============================================================

$ENVIRONMENTS = @{
    production = @{
        # SSH
        SERVER = "tp"
        
        # Пути (ПРАВИЛЬНЫЕ ИМЕНА - с подчеркиванием!)
        REMOTE_DIR = "/var/www/teaching_panel"
        BACKEND_DIR = "/var/www/teaching_panel/teaching_panel"
        FRONTEND_DIR = "/var/www/teaching_panel/frontend"
        VENV_PATH = "/var/www/teaching_panel/venv"
        GIT_BRANCH = "main"
        
        # Systemd сервисы (ПРАВИЛЬНЫЕ ИМЕНА!)
        SERVICE_NAME = "teaching_panel"           # Production с подчеркиванием
        NGINX_SERVICE = "nginx"
        CELERY_WORKER = "celery-worker"
        CELERY_BEAT = "celery-beat"
        
        # URLs
        SITE_URL = "https://lectiospace.ru"
        HEALTH_ENDPOINT = "https://lectiospace.ru/api/health/"
        
        # Labels
        LABEL = "PRODUCTION"
        EMOJI = "🚀"
        COLOR = "Red"
    }
    staging = @{
        # SSH (тот же сервер)
        SERVER = "tp"
        
        # Пути staging (с дефисом - так на сервере)
        REMOTE_DIR = "/var/www/teaching-panel-stage"
        BACKEND_DIR = "/var/www/teaching-panel-stage/teaching_panel"
        FRONTEND_DIR = "/var/www/teaching-panel-stage/frontend"
        VENV_PATH = "/var/www/teaching-panel-stage/venv"
        GIT_BRANCH = "staging"
        
        # Systemd сервисы staging
        SERVICE_NAME = "teaching-panel-stage"     # Staging с дефисом
        NGINX_SERVICE = "nginx"
        CELERY_WORKER = ""                        # Нет на staging
        CELERY_BEAT = ""
        
        # URLs
        SITE_URL = "https://stage.lectiospace.ru"
        HEALTH_ENDPOINT = "https://stage.lectiospace.ru/api/health/"
        
        # Labels
        LABEL = "STAGING"
        EMOJI = "🧪"
        COLOR = "Yellow"
    }
}

# Выбираем конфиг для текущего окружения
$CONFIG = $ENVIRONMENTS[$Environment]

# Общие настройки
$CONFIG.BACKUP_ENABLED = $true
$CONFIG.BACKUP_DIR = "/tmp"
$CONFIG.HEALTH_CHECK_RETRIES = 5
$CONFIG.HEALTH_CHECK_DELAY = 3
$CONFIG.HEALTH_CHECK_TIMEOUT = 10

# Telegram настройки (используем ERRORS бот - он же уведомляет о деплое)
$TELEGRAM = @{
    ENABLED = (-not $SkipTelegram)
    BOT_TOKEN = ""      # Берём с сервера
    CHAT_ID = ""        # Берём с сервера
}

# Переопределение из параметров
if ($SkipBackup) { $CONFIG.BACKUP_ENABLED = $false }

# ============================================================
# ЦВЕТА И ОФОРМЛЕНИЕ
# ============================================================

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([int]$Num, [int]$Total, [string]$Message)
    Write-Host "[$Num/$Total] $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Err {
    param([string]$Message)
    Write-Host "  [FAIL] $Message" -ForegroundColor Red
}

function Write-Warn {
    param([string]$Message)
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "  [..] $Message" -ForegroundColor Gray
}

# ============================================================
# TELEGRAM УВЕДОМЛЕНИЯ
# ============================================================

function Initialize-Telegram {
    if (-not $TELEGRAM.ENABLED) { return }
    
    # Получаем токены с сервера из .env
    try {
        $envData = ssh $CONFIG.SERVER "grep -E '^ERRORS_BOT_TOKEN=|^ERRORS_CHAT_ID=' $($CONFIG.REMOTE_DIR)/.env 2>/dev/null"
        foreach ($line in $envData) {
            if ($line -match '^ERRORS_BOT_TOKEN=(.+)$') {
                $TELEGRAM.BOT_TOKEN = $Matches[1].Trim()
            }
            if ($line -match '^ERRORS_CHAT_ID=(.+)$') {
                $TELEGRAM.CHAT_ID = $Matches[1].Trim()
            }
        }
        
        if (-not $TELEGRAM.BOT_TOKEN -or -not $TELEGRAM.CHAT_ID) {
            Write-Warn "Telegram токены не найдены в .env, уведомления отключены"
            $TELEGRAM.ENABLED = $false
        }
    } catch {
        Write-Warn "Не удалось получить Telegram конфиг: $_"
        $TELEGRAM.ENABLED = $false
    }
}

function Send-TelegramMessage {
    param(
        [string]$Message,
        [ValidateSet('info', 'success', 'error', 'warning')]
        [string]$Level = 'info'
    )
    
    if (-not $TELEGRAM.ENABLED -or $DryRun) { return }
    
    $icon = switch ($Level) {
        'info'    { "ℹ️" }
        'success' { "✅" }
        'error'   { "🔴" }
        'warning' { "⚠️" }
    }
    
    $envLabel = $CONFIG.LABEL
    $fullMessage = "$icon [$envLabel] $Message"
    
    try {
        $body = @{
            chat_id = $TELEGRAM.CHAT_ID
            text = $fullMessage
            parse_mode = "HTML"
            disable_web_page_preview = $true
        } | ConvertTo-Json -Compress
        
        Invoke-RestMethod -Uri "https://api.telegram.org/bot$($TELEGRAM.BOT_TOKEN)/sendMessage" `
            -Method Post -Body $body -ContentType "application/json; charset=utf-8" `
            -TimeoutSec 5 -ErrorAction SilentlyContinue | Out-Null
    } catch {
        # Telegram ошибки не должны блокировать деплой
    }
}

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

function Test-SSHConnection {
    Write-Info "Проверка SSH подключения к $($CONFIG.SERVER)..."
    try {
        $result = ssh $CONFIG.SERVER "echo 'OK'" 2>&1
        if ($LASTEXITCODE -eq 0 -and $result -eq "OK") {
            Write-Success "SSH подключение работает"
            return $true
        }
    } catch {}
    
    Write-Err "Не удалось подключиться к серверу через SSH"
    Write-Host ""
    Write-Host "Проверьте:" -ForegroundColor Yellow
    Write-Host "  1. SSH алиас '$($CONFIG.SERVER)' настроен в ~/.ssh/config" -ForegroundColor Gray
    Write-Host "  2. SSH ключи работают: ssh $($CONFIG.SERVER) 'echo OK'" -ForegroundColor Gray
    Write-Host "  3. Сервер доступен" -ForegroundColor Gray
    return $false
}

function Test-SiteHealth {
    param(
        [int]$Retries = $CONFIG.HEALTH_CHECK_RETRIES,
        [int]$Delay = $CONFIG.HEALTH_CHECK_DELAY,
        [string]$Url = $CONFIG.HEALTH_ENDPOINT,
        [switch]$Silent
    )
    
    if ($SkipHealthCheck) {
        Write-Warn "Health check пропущен (флаг -SkipHealthCheck)"
        return $true
    }
    
    if (-not $Silent) {
        Write-Info "Проверка работоспособности: $Url"
    }
    
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $CONFIG.HEALTH_CHECK_TIMEOUT -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                if (-not $Silent) {
                    Write-Success "Health check пройден (попытка $i/$Retries)"
                }
                return $true
            }
        } catch {
            $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { "timeout" }
            if (-not $Silent) {
                Write-Warn "Health check failed: HTTP $statusCode (попытка $i/$Retries)"
            }
        }
        
        if ($i -lt $Retries) {
            Start-Sleep -Seconds $Delay
        }
    }
    
    Write-Err "Health check провален после $Retries попыток"
    return $false
}

function Invoke-RemoteCommand {
    param(
        [string]$Command,
        [string]$Description = "",
        [switch]$IgnoreErrors
    )
    
    if ($Description) {
        Write-Info $Description
    }
    
    if ($DryRun) {
        Write-Host "  [DRY-RUN] $Command" -ForegroundColor Gray
        return $true
    }
    
    try {
        $output = ssh $CONFIG.SERVER $Command 2>&1
        if ($LASTEXITCODE -eq 0 -or $IgnoreErrors) {
            return $true
        } else {
            Write-Err "Команда завершилась с ошибкой (exit code: $LASTEXITCODE)"
            Write-Host $output -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Err "Исключение при выполнении команды: $_"
        return $false
    }
}

# ============================================================
# РАСШИРЕННЫЙ МОНИТОРИНГ
# ============================================================

function Show-FullMonitoring {
    Write-Header "$($CONFIG.EMOJI) МОНИТОРИНГ [$($CONFIG.LABEL)]"
    
    $monitorData = ssh $CONFIG.SERVER @"
echo '=== SERVICES ==='
for svc in $($CONFIG.SERVICE_NAME) nginx $(if ($CONFIG.CELERY_WORKER) { $CONFIG.CELERY_WORKER }) $(if ($CONFIG.CELERY_BEAT) { $CONFIG.CELERY_BEAT }) redis-server; do
    status=\$(systemctl is-active \$svc 2>/dev/null || echo 'not-found')
    if [ "\$status" = "active" ]; then
        uptime=\$(systemctl show \$svc --property=ActiveEnterTimestamp --value 2>/dev/null)
        echo "\$svc|active|\$uptime"
    else
        echo "\$svc|\$status|"
    fi
done

echo '=== DISK ==='
df -h / | tail -1 | awk '{print \$2"|"\$3"|"\$4"|"\$5}'

echo '=== MEMORY ==='
free -m | grep Mem | awk '{printf "%d|%d|%d|%.1f\n", \$2, \$3, \$7, \$3/\$2*100}'

echo '=== CPU ==='
uptime | sed 's/.*load average: //'

echo '=== GUNICORN ==='
pgrep -c gunicorn 2>/dev/null || echo '0'

echo '=== DB_SIZE ==='
stat -c '%s' $($CONFIG.BACKEND_DIR)/db.sqlite3 2>/dev/null || echo '0'

echo '=== GIT ==='
cd $($CONFIG.REMOTE_DIR) && git log -1 --format='%h|%s|%ar' 2>/dev/null || echo 'unknown'

echo '=== ERRORS ==='
tail -20 /var/log/teaching_panel/error.log 2>/dev/null | grep -c 'ERROR\|CRITICAL' || echo '0'

echo '=== CONNECTIONS ==='
ss -tuln 2>/dev/null | grep -c ':8000\b\|:8001\b' || echo '0'

echo '=== LAST_RESTART ==='
systemctl show $($CONFIG.SERVICE_NAME) --property=ActiveEnterTimestamp --value 2>/dev/null || echo 'unknown'
"@

    $section = ""
    foreach ($line in $monitorData) {
        $line = $line.Trim()
        
        if ($line -match '^=== (\w+) ===$') {
            $section = $Matches[1]
            continue
        }
        
        switch ($section) {
            "SERVICES" {
                if ($line) {
                    $parts = $line -split '\|'
                    $svcName = $parts[0]
                    $svcStatus = $parts[1]
                    $svcUptime = if ($parts.Count -gt 2) { $parts[2] } else { "" }
                    
                    $color = switch ($svcStatus) {
                        "active" { "Green" }
                        "not-found" { "DarkGray" }
                        default { "Red" }
                    }
                    
                    $uptimeStr = ""
                    if ($svcUptime -and $svcStatus -eq "active") {
                        try {
                            $startTime = [DateTime]::Parse($svcUptime)
                            $duration = (Get-Date) - $startTime
                            $uptimeStr = " (uptime: $([math]::Floor($duration.TotalHours))h $($duration.Minutes)m)"
                        } catch {
                            $uptimeStr = ""
                        }
                    }
                    
                    Write-Host "  $svcName : " -NoNewline -ForegroundColor White
                    Write-Host "$svcStatus$uptimeStr" -ForegroundColor $color
                }
            }
            "DISK" {
                if ($line) {
                    $parts = $line -split '\|'
                    $usedPct = $parts[3] -replace '%', ''
                    $diskColor = if ([int]$usedPct -gt 90) { "Red" } elseif ([int]$usedPct -gt 75) { "Yellow" } else { "Green" }
                    Write-Host ""
                    Write-Host "  Диск: " -NoNewline -ForegroundColor White
                    Write-Host "$($parts[1]) / $($parts[0]) ($($parts[3]) использовано)" -ForegroundColor $diskColor
                }
            }
            "MEMORY" {
                if ($line) {
                    $parts = $line -split '\|'
                    $memPct = [double]$parts[3]
                    $memColor = if ($memPct -gt 90) { "Red" } elseif ($memPct -gt 75) { "Yellow" } else { "Green" }
                    Write-Host "  RAM:  " -NoNewline -ForegroundColor White
                    Write-Host "$($parts[1])MB / $($parts[0])MB ($([math]::Round($memPct))% использовано, свободно $($parts[2])MB)" -ForegroundColor $memColor
                }
            }
            "CPU" {
                if ($line) {
                    $loads = $line.Trim() -split ',\s*'
                    $load1 = [double]$loads[0]
                    $cpuColor = if ($load1 -gt 4) { "Red" } elseif ($load1 -gt 2) { "Yellow" } else { "Green" }
                    Write-Host "  CPU:  " -NoNewline -ForegroundColor White
                    Write-Host "Load: $($loads[0]) (1m), $($loads[1]) (5m), $($loads[2]) (15m)" -ForegroundColor $cpuColor
                }
            }
            "GUNICORN" {
                Write-Host "  Gunicorn workers: " -NoNewline -ForegroundColor White
                Write-Host $line.Trim() -ForegroundColor Cyan
            }
            "DB_SIZE" {
                if ($line -and $line -ne '0') {
                    $dbSizeMB = [math]::Round([long]$line.Trim() / 1MB, 1)
                    Write-Host "  БД SQLite: " -NoNewline -ForegroundColor White
                    Write-Host "${dbSizeMB} MB" -ForegroundColor Cyan
                }
            }
            "GIT" {
                if ($line -and $line -ne 'unknown') {
                    $parts = $line -split '\|'
                    Write-Host ""
                    Write-Host "  Git:  " -NoNewline -ForegroundColor White
                    Write-Host "$($parts[0]) - $($parts[1]) ($($parts[2]))" -ForegroundColor Gray
                }
            }
            "ERRORS" {
                $errCount = [int]$line.Trim()
                $errColor = if ($errCount -gt 5) { "Red" } elseif ($errCount -gt 0) { "Yellow" } else { "Green" }
                Write-Host "  Ошибки (последние 20 строк лога): " -NoNewline -ForegroundColor White
                Write-Host $errCount -ForegroundColor $errColor
            }
            "CONNECTIONS" {
                Write-Host "  Активные порты (8000/8001): " -NoNewline -ForegroundColor White
                Write-Host $line.Trim() -ForegroundColor Cyan
            }
            "LAST_RESTART" {
                if ($line -and $line -ne 'unknown') {
                    Write-Host "  Последний рестарт: " -NoNewline -ForegroundColor White
                    Write-Host $line.Trim() -ForegroundColor Gray
                }
            }
        }
    }
    
    Write-Host ""
    
    # Health check
    Write-Info "Health endpoint..."
    if (Test-SiteHealth -Silent) {
        Write-Success "Сайт отвечает нормально"
    } else {
        Write-Err "Сайт не отвечает!"
    }
    
    Write-Host ""
}

# ============================================================
# БЭКАП И ОТКАТ
# ============================================================

$script:backupName = $null
$script:currentCommit = $null
$script:codeChanged = $false
$script:deployStartTime = $null

function Backup-Database {
    if (-not $CONFIG.BACKUP_ENABLED) {
        Write-Warn "Бэкап отключен (флаг -SkipBackup)"
        return $true
    }
    
    Write-Info "Создание бэкапа БД..."
    
    $script:backupName = "deploy_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    
    if ($DryRun) {
        Write-Host "  [DRY-RUN] Бэкап был бы создан: $($CONFIG.BACKUP_DIR)/$script:backupName.sqlite3" -ForegroundColor Gray
        return $true
    }
    
    # Копируем SQLite файл
    $backupResult = ssh $CONFIG.SERVER "cd $($CONFIG.REMOTE_DIR) && sudo cp teaching_panel/db.sqlite3 $($CONFIG.BACKUP_DIR)/$script:backupName.sqlite3 2>&1 && stat -c '%s' $($CONFIG.BACKUP_DIR)/$script:backupName.sqlite3 2>/dev/null"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Не удалось создать бэкап БД"
        return $false
    }
    
    $backupSize = ($backupResult | Select-Object -First 1)
    if ([int]$backupSize -le 0) {
        Write-Err "Бэкап БД выглядит пустым (0 bytes)"
        return $false
    }
    
    # Проверка целостности
    $integrityCheck = ssh $CONFIG.SERVER "sqlite3 $($CONFIG.BACKUP_DIR)/$script:backupName.sqlite3 'PRAGMA integrity_check;' 2>&1"
    if ($integrityCheck -ne "ok") {
        Write-Err "Бэкап повреждён! integrity_check: $integrityCheck"
        return $false
    }
    
    $sizeReadable = ssh $CONFIG.SERVER "numfmt --to=iec-i --suffix=B $backupSize 2>/dev/null || echo '${backupSize} bytes'"
    Write-Success "БД забэкаплена: $($CONFIG.BACKUP_DIR)/$script:backupName.sqlite3 ($sizeReadable)"
    return $true
}

function Backup-Code {
    Write-Info "Сохранение текущего коммита..."
    
    $script:currentCommit = ssh $CONFIG.SERVER "cd $($CONFIG.REMOTE_DIR) && git rev-parse --short HEAD 2>/dev/null"
    
    if ($script:currentCommit) {
        Write-Success "Текущий коммит: $script:currentCommit"
        return $true
    } else {
        Write-Warn "Не удалось определить текущий коммит"
        return $false
    }
}

function Invoke-Rollback {
    param([string]$Reason = "")
    
    Write-Host ""
    Write-Err "=== ОТКАТ ИЗМЕНЕНИЙ ==="
    if ($Reason) {
        Write-Host "  Причина: $Reason" -ForegroundColor Yellow
    }
    Write-Host ""
    
    Send-TelegramMessage -Message "ОТКАТ на $($CONFIG.LABEL)!`nПричина: $Reason`nКоммит: $($script:currentCommit)" -Level error
    
    if ($script:currentCommit -and $script:codeChanged) {
        Write-Info "Откат кода к коммиту $script:currentCommit..."
        ssh $CONFIG.SERVER "cd $($CONFIG.REMOTE_DIR) && sudo git reset --hard $script:currentCommit"
    }
    
    Write-Info "Перезапуск сервисов..."
    ssh $CONFIG.SERVER "sudo systemctl restart $($CONFIG.SERVICE_NAME) $($CONFIG.NGINX_SERVICE)"
    Start-Sleep -Seconds 5
    
    if (Test-SiteHealth -Silent) {
        Write-Success "Откат выполнен успешно"
        Send-TelegramMessage -Message "Откат успешен, сайт работает" -Level warning
        return $true
    } else {
        Write-Err "КРИТИЧЕСКАЯ ОШИБКА: Откат не помог!"
        Send-TelegramMessage -Message "КРИТИЧНО: Откат НЕ помог! Требуется ручное вмешательство!" -Level error
        Write-Host ""
        Write-Host "РУЧНОЕ ВОССТАНОВЛЕНИЕ:" -ForegroundColor Red
        Write-Host "  1. ssh $($CONFIG.SERVER)" -ForegroundColor White
        Write-Host "  2. cd $($CONFIG.REMOTE_DIR)" -ForegroundColor White
        Write-Host "  3. sudo git reset --hard $script:currentCommit" -ForegroundColor White
        Write-Host "  4. sudo systemctl restart $($CONFIG.SERVICE_NAME)" -ForegroundColor White
        if ($script:backupName) {
            Write-Host "  5. Восстановить БД: sudo cp $($CONFIG.BACKUP_DIR)/$script:backupName.sqlite3 teaching_panel/db.sqlite3" -ForegroundColor White
        }
        return $false
    }
}

# ============================================================
# ДЕПЛОЙ ФУНКЦИИ
# ============================================================

function Deploy-Backend {
    Write-Header "$($CONFIG.EMOJI) ДЕПЛОЙ BACKEND [$($CONFIG.LABEL)]"
    
    $script:deployStartTime = Get-Date
    $steps = 8
    $currentStep = 0
    
    Send-TelegramMessage -Message "Начинаю деплой backend на $($CONFIG.LABEL)..." -Level info
    
    # Шаг 1: Бэкап
    $currentStep++
    Write-Step $currentStep $steps "Создание бэкапа..."
    if (-not (Backup-Database)) {
        Send-TelegramMessage -Message "Деплой отменён: ошибка бэкапа" -Level error
        return $false
    }
    if (-not (Backup-Code)) {
        return $false
    }
    
    # Шаг 2: Git pull
    $currentStep++
    Write-Step $currentStep $steps "Получение изменений из Git..."
    
    $branch = $CONFIG.GIT_BRANCH
    ssh $CONFIG.SERVER "cd $($CONFIG.REMOTE_DIR) && sudo git fetch origin $branch 2>/dev/null" | Out-Null
    $remoteCommit = ssh $CONFIG.SERVER "cd $($CONFIG.REMOTE_DIR) && git rev-parse --short origin/$branch"
    
    if ($script:currentCommit -eq $remoteCommit) {
        Write-Success "Код уже актуален"
    } else {
        Write-Info "Обновление: $script:currentCommit -> $remoteCommit"
        
        # Показать что изменилось
        $changedFiles = ssh $CONFIG.SERVER "cd $($CONFIG.REMOTE_DIR) && git diff --stat $($script:currentCommit)..origin/$branch 2>/dev/null | tail -5"
        if ($changedFiles) {
            Write-Host $changedFiles -ForegroundColor Gray
        }
        
        if (-not $Force -and -not $DryRun) {
            $confirm = Read-Host "  Применить изменения? (y/n)"
            if ($confirm -ne "y") {
                Write-Warn "Отменено пользователем"
                return $false
            }
        }
        
        if (-not $DryRun) {
            ssh $CONFIG.SERVER "cd $($CONFIG.REMOTE_DIR) && sudo git reset --hard origin/$branch"
            $script:codeChanged = $true
            Write-Success "Код обновлён"
        }
    }
    
    # Шаг 3: Requirements
    $currentStep++
    Write-Step $currentStep $steps "Проверка Python зависимостей..."
    
    if ($script:codeChanged) {
        $reqChanged = ssh $CONFIG.SERVER "cd $($CONFIG.REMOTE_DIR) && git diff $script:currentCommit HEAD --name-only 2>/dev/null | grep -E 'requirements.*\.txt$' || true"
        
        if ($reqChanged) {
            Write-Info "requirements.txt изменился, обновляем пакеты..."
            if (-not $DryRun) {
                $result = Invoke-RemoteCommand -Command "cd $($CONFIG.REMOTE_DIR) && sudo -u www-data $($CONFIG.VENV_PATH)/bin/pip install -r teaching_panel/requirements.txt --no-input -q 2>&1"
                if (-not $result) {
                    Invoke-Rollback -Reason "pip install провалился"
                    return $false
                }
                Write-Success "Пакеты Python обновлены"
            }
        } else {
            Write-Success "requirements.txt не изменился"
        }
    } else {
        Write-Success "Изменений нет, пропускаем"
    }
    
    # Шаг 4: Миграции
    $currentStep++
    Write-Step $currentStep $steps "Проверка миграций БД..."
    
    $migrations = ssh $CONFIG.SERVER "cd $($CONFIG.BACKEND_DIR) && sudo -u www-data $($CONFIG.VENV_PATH)/bin/python manage.py migrate --plan 2>&1"
    
    if ($migrations -match "No planned migration operations") {
        Write-Success "Новых миграций нет"
    } else {
        Write-Warn "Обнаружены миграции БД!"
        Write-Host $migrations -ForegroundColor Yellow
        
        Send-TelegramMessage -Message "Внимание: обнаружены миграции БД на $($CONFIG.LABEL)" -Level warning
        
        if (-not $Force -and -not $DryRun) {
            Write-Host ""
            $confirmMigrate = Read-Host "  Применить миграции? (введите 'MIGRATE' для подтверждения)"
            if ($confirmMigrate -ne "MIGRATE") {
                Write-Warn "Миграции отменены"
                Invoke-Rollback -Reason "Миграции отклонены пользователем"
                return $false
            }
        }
        
        if (-not $DryRun) {
            $migrateResult = ssh $CONFIG.SERVER "cd $($CONFIG.BACKEND_DIR) && sudo -u www-data $($CONFIG.VENV_PATH)/bin/python manage.py migrate --noinput 2>&1"
            if ($LASTEXITCODE -ne 0 -or $migrateResult -match "Error|Exception|Traceback") {
                Write-Err "Миграция провалилась!"
                Write-Host $migrateResult -ForegroundColor Red
                Invoke-Rollback -Reason "Ошибка миграции"
                return $false
            }
            Write-Success "Миграции применены"
        }
    }
    
    # Шаг 5: Collectstatic
    $currentStep++
    Write-Step $currentStep $steps "Сборка статических файлов..."
    
    if (-not $DryRun) {
        ssh $CONFIG.SERVER "cd $($CONFIG.BACKEND_DIR) && sudo -u www-data $($CONFIG.VENV_PATH)/bin/python manage.py collectstatic --noinput --clear 2>/dev/null" | Out-Null
        Write-Success "Статические файлы собраны"
    }
    
    # Шаг 6: Fix permissions
    $currentStep++
    Write-Step $currentStep $steps "Исправление прав доступа..."
    
    if (-not $DryRun) {
        ssh $CONFIG.SERVER @"
sudo chown -R www-data:www-data $($CONFIG.REMOTE_DIR)/teaching_panel/staticfiles 2>/dev/null || true
sudo chmod -R 755 $($CONFIG.REMOTE_DIR)/teaching_panel/staticfiles 2>/dev/null || true
sudo chown -R www-data:www-data $($CONFIG.REMOTE_DIR)/teaching_panel/media 2>/dev/null || true
sudo chmod -R 755 $($CONFIG.REMOTE_DIR)/teaching_panel/media 2>/dev/null || true
"@
        Write-Success "Права исправлены"
    }
    
    # Шаг 7: Restart services
    $currentStep++
    Write-Step $currentStep $steps "Перезапуск сервисов..."
    
    if (-not $DryRun) {
        ssh $CONFIG.SERVER "sudo systemctl reload $($CONFIG.SERVICE_NAME) 2>/dev/null || sudo systemctl restart $($CONFIG.SERVICE_NAME)"
        # Celery (только если настроены)
        if ($CONFIG.CELERY_WORKER) {
            ssh $CONFIG.SERVER "sudo systemctl restart $($CONFIG.CELERY_WORKER) 2>/dev/null || true; sudo systemctl restart $($CONFIG.CELERY_BEAT) 2>/dev/null || true"
        }
        
        Start-Sleep -Seconds 5
        
        $status = ssh $CONFIG.SERVER "systemctl is-active $($CONFIG.SERVICE_NAME)"
        if ($status -ne "active") {
            Write-Err "Сервис не запустился!"
            ssh $CONFIG.SERVER "sudo journalctl -u $($CONFIG.SERVICE_NAME) -n 30 --no-pager" | ForEach-Object { Write-Host $_ -ForegroundColor Red }
            Invoke-Rollback -Reason "Сервис не запустился"
            return $false
        }
        Write-Success "Сервис запущен"
    }
    
    # Шаг 8: Health check
    $currentStep++
    Write-Step $currentStep $steps "Smoke tests..."
    
    Start-Sleep -Seconds 3
    
    if (-not (Test-SiteHealth)) {
        Invoke-Rollback -Reason "Health check провален"
        return $false
    }
    
    $duration = if ($script:deployStartTime) { [math]::Round(((Get-Date) - $script:deployStartTime).TotalSeconds) } else { "?" }
    $newCommit = ssh $CONFIG.SERVER "cd $($CONFIG.REMOTE_DIR) && git rev-parse --short HEAD 2>/dev/null"
    
    Write-Success "Backend успешно задеплоен! (${duration}s)"
    Send-TelegramMessage -Message "Backend деплой на $($CONFIG.LABEL) завершён за ${duration}s`nКоммит: $newCommit" -Level success
    return $true
}

function Deploy-Frontend {
    Write-Header "$($CONFIG.EMOJI) ДЕПЛОЙ FRONTEND (АТОМАРНЫЙ) [$($CONFIG.LABEL)]"
    
    $script:deployStartTime = Get-Date
    Send-TelegramMessage -Message "Начинаю деплой frontend на $($CONFIG.LABEL)..." -Level info
    
    # Проверяем что билд существует локально
    $localBuild = Join-Path $PSScriptRoot "frontend\build"
    if (-not (Test-Path "$localBuild\index.html")) {
        Write-Err "Билд не найден! Запустите: cd frontend && npm run build"
        Send-TelegramMessage -Message "Frontend деплой отменён: билд не найден" -Level error
        return $false
    }
    
    Write-Info "Локальный билд найден: $localBuild"
    
    $steps = 8
    $currentStep = 0
    
    # Шаг 1: Проверка билда
    $currentStep++
    Write-Step $currentStep $steps "Проверка билда..."
    
    $indexContent = Get-Content "$localBuild\index.html" -Raw
    if ($indexContent -match 'main\.([a-f0-9]+)\.js') {
        $jsHash = $Matches[1]
        Write-Success "Билд валиден: main.$jsHash.js"
    } else {
        Write-Err "Не могу найти main.*.js в index.html"
        return $false
    }
    
    # Шаг 2: Создание временной директории
    $currentStep++
    Write-Step $currentStep $steps "Создание временной директории на сервере..."
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $tempBuild = "$($CONFIG.FRONTEND_DIR)/build_new_$timestamp"
    
    if (-not $DryRun) {
        ssh $CONFIG.SERVER "mkdir -p $tempBuild"
        Write-Success "Временная директория создана"
    }
    
    # Шаг 3: Копирование файлов
    $currentStep++
    Write-Step $currentStep $steps "Копирование билда на сервер..."
    
    if (-not $DryRun) {
        scp -r "$localBuild\*" "$($CONFIG.SERVER):$tempBuild/" 2>&1 | Out-Null
        
        if ($LASTEXITCODE -ne 0) {
            Write-Err "SCP завершился с ошибкой"
            ssh $CONFIG.SERVER "rm -rf $tempBuild"
            return $false
        }
        Write-Success "Файлы скопированы"
    }
    
    # Шаг 4: Проверка нового билда
    $currentStep++
    Write-Step $currentStep $steps "Проверка нового билда на сервере..."
    
    if (-not $DryRun) {
        $indexCheck = ssh $CONFIG.SERVER "test -f $tempBuild/index.html && echo 'ok' || echo 'fail'"
        $jsCheck = ssh $CONFIG.SERVER "grep -oP 'main\.\w+\.js' $tempBuild/index.html | head -1"
        $jsExists = ssh $CONFIG.SERVER "test -f $tempBuild/static/js/$jsCheck && echo 'ok' || echo 'fail'"
        
        if ($indexCheck -ne "ok" -or $jsExists -ne "ok") {
            Write-Err "Новый билд невалиден! index=$indexCheck js=$jsExists"
            ssh $CONFIG.SERVER "rm -rf $tempBuild"
            return $false
        }
        Write-Success "Новый билд валиден"
    }
    
    # Шаг 5: Исправление прав
    $currentStep++
    Write-Step $currentStep $steps "Исправление прав доступа..."
    
    if (-not $DryRun) {
        ssh $CONFIG.SERVER "sudo chown -R www-data:www-data $tempBuild && sudo chmod -R 755 $tempBuild"
        Write-Success "Права исправлены"
    }
    
    # Шаг 6: АТОМАРНАЯ ЗАМЕНА
    $currentStep++
    Write-Step $currentStep $steps "Атомарная замена билда..."
    
    if (-not $DryRun) {
        $swapResult = ssh $CONFIG.SERVER @"
cd $($CONFIG.FRONTEND_DIR) && \
sudo mv build build_old_$timestamp 2>/dev/null || true && \
sudo mv $tempBuild build && \
sudo nginx -s reload && \
echo 'SWAP_OK'
"@
        
        if ($swapResult -notmatch "SWAP_OK") {
            Write-Err "Замена провалилась!"
            ssh $CONFIG.SERVER "cd $($CONFIG.FRONTEND_DIR) && sudo mv build_old_$timestamp build 2>/dev/null || true"
            Send-TelegramMessage -Message "Frontend деплой провалился: ошибка swap" -Level error
            return $false
        }
        Write-Success "Билд заменён атомарно (~мгновенно)"
    }
    
    # Шаг 7: Health check
    $currentStep++
    Write-Step $currentStep $steps "Проверка работоспособности..."
    
    Start-Sleep -Seconds 2
    
    if (-not (Test-SiteHealth)) {
        Write-Err "Сайт не работает! Откат..."
        Send-TelegramMessage -Message "Frontend деплой: откат (health check fail)" -Level error
        if (-not $DryRun) {
            ssh $CONFIG.SERVER @"
cd $($CONFIG.FRONTEND_DIR) && \
sudo rm -rf build && \
sudo mv build_old_$timestamp build && \
sudo nginx -s reload
"@
        }
        return $false
    }
    
    # Шаг 8: Очистка старых билдов
    $currentStep++
    Write-Step $currentStep $steps "Очистка старых билдов..."
    
    if (-not $DryRun) {
        ssh $CONFIG.SERVER "cd $($CONFIG.FRONTEND_DIR) && ls -dt build_old_* build_new_* 2>/dev/null | tail -n +3 | xargs -r sudo rm -rf"
        Write-Success "Старые билды удалены (оставлены 2 последних)"
    }
    
    $duration = if ($script:deployStartTime) { [math]::Round(((Get-Date) - $script:deployStartTime).TotalSeconds) } else { "?" }
    Write-Success "Frontend успешно задеплоен! (${duration}s)"
    Send-TelegramMessage -Message "Frontend деплой на $($CONFIG.LABEL) завершён за ${duration}s" -Level success
    return $true
}

function Deploy-Full {
    Write-Header "$($CONFIG.EMOJI) ПОЛНЫЙ ДЕПЛОЙ [$($CONFIG.LABEL)]"
    
    if ($Environment -eq "production") {
        Write-Host "  !! ВНИМАНИЕ: Деплой на PRODUCTION !!" -ForegroundColor Red
        Write-Host ""
        if (-not $Force -and -not $DryRun) {
            $confirm = Read-Host "  Продолжить? (y/n)"
            if ($confirm -ne "y") {
                Write-Warn "Отменено"
                return $false
            }
        }
    }
    
    $script:deployStartTime = Get-Date
    Send-TelegramMessage -Message "Начинаю ПОЛНЫЙ деплой на $($CONFIG.LABEL)..." -Level info
    
    # Pre-deployment check
    Write-Info "Проверка $($CONFIG.LABEL) перед началом..."
    if (-not (Test-SiteHealth -Silent)) {
        Write-Warn "$($CONFIG.LABEL) не отвечает до деплоя"
        if ($Environment -eq "production" -and -not $Force) {
            Write-Err "Production УЖЕ не работает! Используй -Force или почини сначала"
            return $false
        }
    } else {
        Write-Success "$($CONFIG.LABEL) работает"
    }
    
    # Backend
    if (-not (Deploy-Backend)) {
        return $false
    }
    
    # Frontend
    $localBuild = Join-Path $PSScriptRoot "frontend\build"
    if (Test-Path "$localBuild\index.html") {
        Write-Host ""
        if ($Force) {
            $deployFrontend = "y"
        } else {
            $deployFrontend = Read-Host "Деплоить также frontend? (y/n)"
        }
        if ($deployFrontend -eq "y") {
            if (-not (Deploy-Frontend)) {
                Write-Warn "Frontend деплой провалился, но backend уже обновлён"
                return $false
            }
        }
    } else {
        Write-Info "Frontend билд не найден, пропускаем"
    }
    
    $totalDuration = [math]::Round(((Get-Date) - $script:deployStartTime).TotalSeconds)
    $newCommit = ssh $CONFIG.SERVER "cd $($CONFIG.REMOTE_DIR) && git rev-parse --short HEAD 2>/dev/null"
    
    Write-Header "[OK] ПОЛНЫЙ ДЕПЛОЙ ЗАВЕРШЁН [$($CONFIG.LABEL)]"
    
    Write-Host "  Бэкап БД:    $($CONFIG.BACKUP_DIR)/$script:backupName.sqlite3" -ForegroundColor Gray
    Write-Host "  Коммит:      $newCommit" -ForegroundColor Gray
    Write-Host "  Время:       ${totalDuration}s" -ForegroundColor Gray
    Write-Host "  URL:         $($CONFIG.SITE_URL)" -ForegroundColor Gray
    Write-Host ""
    
    if ($Environment -eq "production") {
        Write-Host "  Следи за логами первые 15 минут:" -ForegroundColor Yellow
        Write-Host "    ssh tp 'sudo tail -f /var/log/teaching_panel/error.log'" -ForegroundColor White
    }
    Write-Host ""
    
    Send-TelegramMessage -Message "ПОЛНЫЙ деплой на $($CONFIG.LABEL) завершён за ${totalDuration}s`nКоммит: $newCommit`nURL: $($CONFIG.SITE_URL)" -Level success
    
    return $true
}

function Deploy-Quick {
    Write-Header "$($CONFIG.EMOJI) БЫСТРЫЙ ПЕРЕЗАПУСК [$($CONFIG.LABEL)]"
    
    Write-Info "Перезапуск сервисов..."
    Send-TelegramMessage -Message "Перезапуск сервисов на $($CONFIG.LABEL)..." -Level info
    
    if (-not $DryRun) {
        ssh $CONFIG.SERVER "sudo systemctl restart $($CONFIG.SERVICE_NAME) $($CONFIG.NGINX_SERVICE)"
        
        Start-Sleep -Seconds 5
        
        if (Test-SiteHealth) {
            Write-Success "Сервисы перезапущены успешно"
            Send-TelegramMessage -Message "Рестарт $($CONFIG.LABEL) выполнен успешно" -Level success
            return $true
        } else {
            Write-Err "Сервисы не работают после перезапуска"
            Send-TelegramMessage -Message "Рестарт $($CONFIG.LABEL) ПРОВАЛИЛСЯ - сайт не отвечает" -Level error
            return $false
        }
    }
    
    Write-Success "Quick restart завершён"
    return $true
}

# ============================================================
# МЕНЮ
# ============================================================

function Show-Menu {
    Clear-Host
    Write-Host ""
    Write-Host "+=============================================================+" -ForegroundColor Cyan
    Write-Host "|   Teaching Panel - Единый надежный деплой v3.0               |" -ForegroundColor Cyan
    Write-Host "+=============================================================+" -ForegroundColor Cyan
    Write-Host ""
    
    $envColor = if ($Environment -eq "production") { "Red" } else { "Yellow" }
    Write-Host "  Environment: " -NoNewline -ForegroundColor White
    Write-Host "$($CONFIG.LABEL)" -ForegroundColor $envColor
    Write-Host "  URL:         $($CONFIG.SITE_URL)" -ForegroundColor Gray
    Write-Host "  Сервер:      $($CONFIG.SERVER) ($($CONFIG.REMOTE_DIR))" -ForegroundColor Gray
    Write-Host "  Telegram:    $(if ($TELEGRAM.ENABLED) { 'ON' } else { 'OFF' })" -ForegroundColor Gray
    Write-Host ""
    Write-Host "+-------------------------------------------------------------+" -ForegroundColor White
    Write-Host "| ДЕПЛОЙ                                                       |" -ForegroundColor White
    Write-Host "+-------------------------------------------------------------+" -ForegroundColor White
    Write-Host "|  1 - Полный деплой (backend + frontend)                      |" -ForegroundColor White
    Write-Host "|  2 - Только backend (Django)                                 |" -ForegroundColor White
    Write-Host "|  3 - Только frontend (React)                                 |" -ForegroundColor White
    Write-Host "|  4 - Быстрый рестарт (без изменений кода)                    |" -ForegroundColor White
    Write-Host "+-------------------------------------------------------------+" -ForegroundColor White
    Write-Host "| МОНИТОРИНГ                                                   |" -ForegroundColor White
    Write-Host "+-------------------------------------------------------------+" -ForegroundColor White
    Write-Host "|  5 - Health check                                            |" -ForegroundColor White
    Write-Host "|  6 - Статус сервисов                                         |" -ForegroundColor White
    Write-Host "|  7 - Просмотр логов                                          |" -ForegroundColor White
    Write-Host "|  8 - Полный мониторинг (disk/RAM/CPU/DB/Git)                 |" -ForegroundColor White
    Write-Host "+-------------------------------------------------------------+" -ForegroundColor White
    Write-Host "| ПЕРЕКЛЮЧЕНИЕ                                                 |" -ForegroundColor White
    Write-Host "+-------------------------------------------------------------+" -ForegroundColor White
    Write-Host "|  9 - Переключить environment ($Environment -> $(if ($Environment -eq 'production') { 'staging' } else { 'production' }))" -ForegroundColor White
    Write-Host "|  0 - Выход                                                   |" -ForegroundColor White
    Write-Host "+-------------------------------------------------------------+" -ForegroundColor White
    Write-Host ""
}

function Show-Status {
    Write-Header "СТАТУС СЕРВИСОВ [$($CONFIG.LABEL)]"
    
    Write-Info "Проверка сервисов..."
    
    $services = @($CONFIG.SERVICE_NAME, $CONFIG.NGINX_SERVICE)
    if ($CONFIG.CELERY_WORKER) { $services += $CONFIG.CELERY_WORKER }
    if ($CONFIG.CELERY_BEAT) { $services += $CONFIG.CELERY_BEAT }
    
    foreach ($service in $services) {
        $status = ssh $CONFIG.SERVER "systemctl is-active $service 2>/dev/null || echo 'not-found'"
        $color = if ($status -eq "active") { "Green" } elseif ($status -eq "not-found") { "Gray" } else { "Red" }
        Write-Host "  $service : $status" -ForegroundColor $color
    }
    
    Write-Host ""
    Write-Info "Проверка health endpoint..."
    
    if (Test-SiteHealth -Silent) {
        Write-Success "Health endpoint работает"
    } else {
        Write-Err "Health endpoint не отвечает"
    }
    
    Write-Host ""
    Read-Host "Нажмите Enter для продолжения"
}

function Show-Logs {
    Write-Header "ЛОГИ [$($CONFIG.LABEL)]"
    
    Write-Host "Выберите лог:" -ForegroundColor Yellow
    Write-Host "  1 - Django error log" -ForegroundColor White
    Write-Host "  2 - Django access log" -ForegroundColor White
    Write-Host "  3 - Nginx error log" -ForegroundColor White
    Write-Host "  4 - Systemd journal ($($CONFIG.SERVICE_NAME))" -ForegroundColor White
    Write-Host "  5 - Django последние ошибки (ERROR/CRITICAL)" -ForegroundColor White
    Write-Host ""
    
    $choice = Read-Host "Введите номер (1-5)"
    
    switch ($choice) {
        "1" { ssh $CONFIG.SERVER "sudo tail -50 /var/log/teaching_panel/error.log 2>/dev/null || echo 'Файл не найден'" }
        "2" { ssh $CONFIG.SERVER "sudo tail -50 /var/log/teaching_panel/access.log 2>/dev/null || echo 'Файл не найден'" }
        "3" { ssh $CONFIG.SERVER "sudo tail -50 /var/log/nginx/error.log 2>/dev/null || echo 'Файл не найден'" }
        "4" { ssh $CONFIG.SERVER "sudo journalctl -u $($CONFIG.SERVICE_NAME) -n 50 --no-pager" }
        "5" { ssh $CONFIG.SERVER "sudo grep -E 'ERROR|CRITICAL' /var/log/teaching_panel/error.log 2>/dev/null | tail -30 || echo 'Ошибок не найдено'" }
        default { Write-Warn "Неверный выбор" }
    }
    
    Write-Host ""
    Read-Host "Нажмите Enter для продолжения"
}

# ============================================================
# MAIN
# ============================================================

# Проверка SSH
if (-not (Test-SSHConnection)) {
    exit 1
}

# Инициализация Telegram
Initialize-Telegram

# Обработка действия из параметра
if ($Action -ne 'menu') {
    switch ($Action) {
        'full' {
            $success = Deploy-Full
            exit $(if ($success) { 0 } else { 1 })
        }
        'backend' {
            $success = Deploy-Backend
            exit $(if ($success) { 0 } else { 1 })
        }
        'frontend' {
            $success = Deploy-Frontend
            exit $(if ($success) { 0 } else { 1 })
        }
        'quick' {
            $success = Deploy-Quick
            exit $(if ($success) { 0 } else { 1 })
        }
        'status' {
            Show-Status
            exit 0
        }
        'monitor' {
            Show-FullMonitoring
            Read-Host "Нажмите Enter для выхода"
            exit 0
        }
        'rollback' {
            Write-Warn "Rollback доступен только во время деплоя"
            exit 1
        }
    }
}

# Интерактивное меню
while ($true) {
    Show-Menu
    
    $choice = Read-Host "Выберите действие (0-9)"
    
    switch ($choice) {
        "1" { Deploy-Full }
        "2" { Deploy-Backend }
        "3" { Deploy-Frontend }
        "4" { Deploy-Quick }
        "5" {
            Write-Header "HEALTH CHECK [$($CONFIG.LABEL)]"
            if (Test-SiteHealth) {
                Write-Success "Сайт работает нормально"
            } else {
                Write-Err "Сайт недоступен"
            }
            Read-Host "`nНажмите Enter для продолжения"
        }
        "6" { Show-Status }
        "7" { Show-Logs }
        "8" {
            Show-FullMonitoring
            Read-Host "Нажмите Enter для продолжения"
        }
        "9" {
            # Переключение environment
            if ($Environment -eq "production") {
                $Environment = "staging"
            } else {
                $Environment = "production"
            }
            $CONFIG = $ENVIRONMENTS[$Environment]
            $CONFIG.BACKUP_ENABLED = (-not $SkipBackup)
            $CONFIG.BACKUP_DIR = "/tmp"
            $CONFIG.HEALTH_CHECK_RETRIES = 5
            $CONFIG.HEALTH_CHECK_DELAY = 3
            $CONFIG.HEALTH_CHECK_TIMEOUT = 10
            
            # Переинициализируем Telegram
            Initialize-Telegram
            
            Write-Success "Переключено на $($CONFIG.LABEL)"
            Start-Sleep -Seconds 1
        }
        "0" {
            Write-Host "`nДо свидания!`n" -ForegroundColor Cyan
            exit 0
        }
        default {
            Write-Warn "Неверный выбор. Попробуйте снова."
            Start-Sleep -Seconds 1
        }
    }
}
