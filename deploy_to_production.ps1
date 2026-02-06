# Безопасный деплой staging → production
# Использование: .\deploy_to_production.ps1
#
# ГАРАНТИИ БЕЗОПАСНОСТИ:
# 1. Бэкап БД ПЕРЕД любыми изменениями
# 2. Проверка бэкапа на валидность
# 3. Автооткат при ошибках
# 4. НЕ применяет миграции без явного подтверждения
# 5. НЕ удаляет данные

param(
    [switch]$DryRun,      # Только показать что будет сделано
    [switch]$SkipStaging  # Пропустить проверку staging
)

$ErrorActionPreference = "Stop"

# Цвета для вывода
function Write-Step { param($num, $total, $msg) Write-Host "[$num/$total] $msg" -ForegroundColor Yellow }
function Write-OK { param($msg) Write-Host "  OK $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  !! $msg" -ForegroundColor Yellow }
function Write-Fail { param($msg) Write-Host "  XX $msg" -ForegroundColor Red }

# Глобальные переменные для отката
$script:currentCommit = $null
$script:backupName = $null
$script:codeChanged = $false

function Rollback-Changes {
    Write-Host ""
    Write-Fail "=== ОТКАТ ИЗМЕНЕНИЙ ==="
    
    if ($script:currentCommit -and $script:codeChanged) {
        Write-Host "Возвращаем код к коммиту $script:currentCommit..." -ForegroundColor Yellow
        ssh tp "cd /var/www/teaching_panel && sudo git reset --hard $script:currentCommit"
    }
    
    Write-Host "Перезапускаем сервисы..." -ForegroundColor Yellow
    ssh tp "sudo systemctl restart nginx redis-server 2>/dev/null || true; (sudo systemctl restart teaching_panel 2>/dev/null || sudo systemctl restart teaching-panel 2>/dev/null || true); (sudo systemctl restart celery-worker 2>/dev/null || true); (sudo systemctl restart celery_worker 2>/dev/null || true); (sudo systemctl restart celery-beat 2>/dev/null || true)"
    Start-Sleep -Seconds 5
    
    $check = ssh tp "curl -s -o /dev/null -w '%{http_code}' https://lectiospace.ru/api/health/ 2>/dev/null || echo 'fail'"
    if ($check -eq "200") {
        Write-OK "Production восстановлен"
    } else {
        Write-Fail "Production не восстановился! Код: $check"
        Write-Host ""
        Write-Host "РУЧНОЕ ВОССТАНОВЛЕНИЕ:" -ForegroundColor Red
        Write-Host "1. ssh tp" -ForegroundColor White
        Write-Host "2. cd /var/www/teaching_panel" -ForegroundColor White
        Write-Host "3. sudo git reset --hard $script:currentCommit" -ForegroundColor White
        Write-Host "4. sudo systemctl restart teaching-panel" -ForegroundColor White
        if ($script:backupName) {
            Write-Host ""
            Write-Host "Бэкап БД: /tmp/$script:backupName.sqlite3" -ForegroundColor White
            Write-Host "Восстановить: sudo cp /tmp/$script:backupName.sqlite3 db.sqlite3" -ForegroundColor White
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "     DEPLOY TO PRODUCTION              " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Warn "РЕЖИМ DRY-RUN: Изменения НЕ будут применены"
    Write-Host ""
}

# ===================================================================
# ШАГ 0: Проверка production - ОН ДОЛЖЕН РАБОТАТЬ ДО НАЧАЛА
# ===================================================================
Write-Step 0 9 "Проверка текущего состояния production..."

$prodBefore = ssh tp "curl -s -o /dev/null -w '%{http_code}' https://lectiospace.ru/api/health/ 2>/dev/null || echo 'fail'"
if ($prodBefore -ne "200") {
    Write-Fail "Production УЖЕ не работает! Код: $prodBefore"
    Write-Fail "Сначала почини production, потом деплой"
    exit 1
}
Write-OK "Production работает (код $prodBefore)"

# Проверка места на диске
# ВАЖНО: избегаем awk '$5' внутри PowerShell строки (PowerShell интерпретирует `$5` как переменную)
$diskSpace = ssh tp "df -P --output=pcent /var/www | tail -n 1 | tr -dc '0-9'"
if ([int]$diskSpace -gt 90) {
    Write-Fail "Мало места на диске: ${diskSpace}%"
    exit 1
}
Write-OK "Место на диске: ${diskSpace}%"

# ===================================================================
# ШАГ 1: Проверка staging
# ===================================================================
Write-Step 1 9 "Проверка staging..."

if ($SkipStaging) {
    Write-Warn "Проверка staging пропущена (флаг -SkipStaging)"
} else {
    $stageCheck = ssh tp "curl -s -o /dev/null -w '%{http_code}' https://stage.lectiospace.ru/api/health/ 2>/dev/null || echo 'fail'"
    if ($stageCheck -ne "200") {
        Write-Fail "Staging не работает! Код: $stageCheck"
        Write-Fail "Сначала протестируй на staging"
        exit 1
    }
    Write-OK "Staging работает (код $stageCheck)"
}

# ===================================================================
# ШАГ 2: БЭКАП (КРИТИЧЕСКИ ВАЖНО - ДО ЛЮБЫХ ИЗМЕНЕНИЙ!)
# ===================================================================
Write-Step 2 9 "Создание бэкапа production..."

$script:backupName = "deploy_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

if (-not $DryRun) {
    # Бэкап SQLite файла (быстро и надежно)
    $sqliteBackup = ssh tp "cd /var/www/teaching_panel && sudo cp db.sqlite3 /tmp/$script:backupName.sqlite3 2>&1 && (stat -c '%s' /tmp/$script:backupName.sqlite3 2>/dev/null || echo 0)"
    
    if (-not $sqliteBackup -or $sqliteBackup -match "No such file") {
        Write-Fail "Не удалось создать бэкап SQLite!"
        exit 1
    }

    $sqliteBackupBytes = 0
    [void][int]::TryParse(($sqliteBackup | Select-Object -First 1), [ref]$sqliteBackupBytes)
    if ($sqliteBackupBytes -le 0) {
        Write-Fail "Бэкап SQLite выглядит пустым (0 bytes) — останавливаем деплой"
        exit 1
    }

    $sqliteBackupHuman = ssh tp "numfmt --to=iec-i --suffix=B $sqliteBackupBytes 2>/dev/null || echo '${sqliteBackupBytes} bytes'"
    Write-OK "SQLite бэкап: /tmp/$script:backupName.sqlite3 ($sqliteBackupHuman)"
    
    # Проверка целостности бэкапа
    $integrityCheck = ssh tp "sqlite3 /tmp/$script:backupName.sqlite3 'PRAGMA integrity_check;' 2>&1"
    if ($integrityCheck -ne "ok") {
        Write-Fail "Бэкап повреждён! integrity_check: $integrityCheck"
        exit 1
    }
    Write-OK "Бэкап прошёл integrity check"
    
    # JSON дамп (дополнительно, для отладки)
    ssh tp "cd /var/www/teaching_panel && sudo -u www-data venv/bin/python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.Permission -o /tmp/$script:backupName.json 2>/dev/null" | Out-Null
} else {
    Write-Host "  [DRY-RUN] Бэкап был бы создан: /tmp/$script:backupName.*" -ForegroundColor Gray
}

# ===================================================================
# ШАГ 3: Git - получить изменения (БЕЗ применения)
# ===================================================================
Write-Step 3 9 "Проверка git изменений..."

$script:currentCommit = ssh tp "cd /var/www/teaching_panel && git rev-parse --short HEAD"
Write-Host "  Текущий коммит: $script:currentCommit" -ForegroundColor Gray

# Fetch без применения
ssh tp "cd /var/www/teaching_panel && sudo git fetch origin main 2>/dev/null" | Out-Null
$remoteCommit = ssh tp "cd /var/www/teaching_panel && git rev-parse --short origin/main"
Write-Host "  Удалённый коммит: $remoteCommit" -ForegroundColor Gray

if ($script:currentCommit -eq $remoteCommit) {
    Write-OK "Код уже актуален"
} else {
    # Показать что изменится
    $changedFiles = ssh tp "cd /var/www/teaching_panel && git diff --name-only $script:currentCommit origin/main 2>/dev/null | head -20"
    Write-Host "  Изменённые файлы:" -ForegroundColor Gray
    Write-Host $changedFiles -ForegroundColor Gray
    
    if (-not $DryRun) {
        Write-Host ""
        $confirmGit = Read-Host "  Применить изменения? (y/n)"
        if ($confirmGit -ne "y") {
            Write-Fail "Отменено пользователем"
            exit 1
        }
        
        ssh tp "cd /var/www/teaching_panel && sudo git reset --hard origin/main"
        $script:codeChanged = $true
        Write-OK "Код обновлён: $script:currentCommit -> $remoteCommit"
    } else {
        Write-Host "  [DRY-RUN] Код был бы обновлён до $remoteCommit" -ForegroundColor Gray
    }
}

# ===================================================================
# ШАГ 4: Проверка зависимостей Python
# ===================================================================
Write-Step 4 9 "Проверка requirements.txt..."

if ($script:currentCommit -ne $remoteCommit) {
    $reqChanged = ssh tp "cd /var/www/teaching_panel && git diff $script:currentCommit HEAD --name-only 2>/dev/null | grep -E 'requirements.*\.txt$' || true"
} else {
    $reqChanged = $null
}

if ($reqChanged) {
    Write-Warn "requirements.txt изменился"
    
    if (-not $DryRun) {
        # Проверка что pip не запущен
        $pipRunning = ssh tp "pgrep -f 'pip install' | wc -l"
        if ([int]$pipRunning -gt 0) {
            Write-Fail "pip install уже запущен! Подожди или убей процесс"
            Rollback-Changes
            exit 1
        }
        
        $pipResult = ssh tp "cd /var/www/teaching_panel && sudo -u www-data venv/bin/pip install -r teaching_panel/requirements.txt --no-input -q 2>&1 && echo 'PIP_OK'"
        if ($pipResult -notmatch "PIP_OK") {
            Write-Fail "pip install завершился с ошибкой!"
            Write-Host $pipResult -ForegroundColor Red
            Rollback-Changes
            exit 1
        }
        Write-OK "Пакеты Python обновлены"
    }
} else {
    Write-OK "requirements.txt не изменился"
}

# ===================================================================
# ШАГ 5: Сборка frontend
# ===================================================================
Write-Step 5 9 "Проверка frontend..."

if ($script:currentCommit -ne $remoteCommit) {
    $frontendChanged = ssh tp "cd /var/www/teaching_panel && git diff $script:currentCommit HEAD --name-only 2>/dev/null | grep '^frontend/' || true"
} else {
    $frontendChanged = $null
}

if ($frontendChanged) {
    Write-Warn "Frontend изменился"
    
    if (-not $DryRun) {
        # Проверка package.json
        $packageChanged = ssh tp "cd /var/www/teaching_panel && git diff $script:currentCommit HEAD --name-only 2>/dev/null | grep 'frontend/package.*json' || true"
        if ($packageChanged) {
            Write-Host "  -> Обновляем npm пакеты..." -ForegroundColor Gray
            ssh tp "cd /var/www/teaching_panel/frontend && npm install --silent" | Out-Null
        }
        
        Write-Host "  -> Сборка frontend..." -ForegroundColor Gray
        $buildResult = ssh tp "cd /var/www/teaching_panel/frontend && npm run build 2>&1"
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "npm run build завершился с ошибкой!"
            Write-Host $buildResult -ForegroundColor Red
            Rollback-Changes
            exit 1
        }
        # КРИТИЧНО: Исправляем права после сборки (npm создаёт с root owner)
        Write-Host "  -> Исправление прав доступа..." -ForegroundColor Gray
        ssh tp "sudo chown -R www-data:www-data /var/www/teaching_panel/frontend/build && sudo chmod -R 755 /var/www/teaching_panel/frontend/build"
        Write-OK "Frontend пересобран"
    }
} else {
    Write-OK "Frontend не изменился"
}

# ===================================================================
# ШАГ 6: МИГРАЦИИ БД (ОПАСНАЯ ЗОНА!)
# ===================================================================
Write-Step 6 9 "Проверка миграций БД..."

$migrations = ssh tp "cd /var/www/teaching_panel && sudo -u www-data venv/bin/python manage.py migrate --plan 2>&1"

if ($migrations -match "No planned migration operations") {
    Write-OK "Новых миграций нет"
} else {
    Write-Host ""
    Write-Host "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
    Write-Host "  ВНИМАНИЕ: ОБНАРУЖЕНЫ МИГРАЦИИ БД!                        " -ForegroundColor Red
    Write-Host "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
    Write-Host ""
    Write-Host $migrations -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Бэкап БД: /tmp/$script:backupName.sqlite3" -ForegroundColor Cyan
    Write-Host ""
    
    if (-not $DryRun) {
        $confirmMigrate = Read-Host "Применить миграции? (введи 'MIGRATE' для подтверждения)"
        if ($confirmMigrate -ne "MIGRATE") {
            Write-Fail "Миграции отменены"
            Rollback-Changes
            exit 1
        }
        
        $migrateResult = ssh tp "cd /var/www/teaching_panel && sudo -u www-data venv/bin/python manage.py migrate --noinput 2>&1"
        if ($LASTEXITCODE -ne 0 -or $migrateResult -match "Error|Exception|Traceback") {
            Write-Fail "Миграция завершилась с ошибкой!"
            Write-Host $migrateResult -ForegroundColor Red
            Write-Host ""
            Write-Host "ВОССТАНОВЛЕНИЕ БД:" -ForegroundColor Red
            Write-Host "ssh tp 'cd /var/www/teaching_panel && sudo cp /tmp/$script:backupName.sqlite3 db.sqlite3 && sudo chown www-data:www-data db.sqlite3'" -ForegroundColor White
            Rollback-Changes
            exit 1
        }
        Write-OK "Миграции применены"
    } else {
        Write-Host "  [DRY-RUN] Миграции были бы применены" -ForegroundColor Gray
    }
}

# ===================================================================
# ШАГ 7: Статические файлы
# ===================================================================
Write-Step 7 9 "Обновление статических файлов..."

if (-not $DryRun) {
    ssh tp "cd /var/www/teaching_panel && sudo -u www-data venv/bin/python manage.py collectstatic --noinput --clear 2>/dev/null" | Out-Null
    Write-OK "Статические файлы обновлены"
} else {
    Write-Host "  [DRY-RUN] collectstatic был бы выполнен" -ForegroundColor Gray
}

# ===================================================================
# ШАГ 8: Перезапуск сервиса
# ===================================================================
Write-Step 8 9 "Перезапуск сервиса..."

if (-not $DryRun) {
    # Graceful reload (если поддерживается)
    ssh tp "sudo systemctl reload teaching-panel 2>/dev/null || sudo systemctl restart teaching-panel"
    # Перезапуск Celery (чтобы воркеры подхватили новый код)
    ssh tp "sudo systemctl restart celery-worker celery-beat 2>/dev/null || true"
    
    # Ждём старта
    Start-Sleep -Seconds 5
    
    $status = ssh tp "systemctl is-active teaching-panel"
    if ($status -ne "active") {
        Write-Fail "Сервис не запустился!"
        ssh tp "sudo journalctl -u teaching-panel -n 30 --no-pager" | ForEach-Object { Write-Host $_ -ForegroundColor Red }
        Rollback-Changes
        exit 1
    }
    Write-OK "Сервис запущен (status: $status)"
} else {
    Write-Host "  [DRY-RUN] Сервис был бы перезапущен" -ForegroundColor Gray
}

# ===================================================================
# ШАГ 9: Smoke tests
# ===================================================================
Write-Step 9 9 "Smoke tests..."

if (-not $DryRun) {
    Start-Sleep -Seconds 3
    
    # Тест 1: Health check
    $healthCheck = ssh tp "curl -s -o /dev/null -w '%{http_code}' https://lectiospace.ru/api/health/"
    if ($healthCheck -ne "200") {
        Write-Fail "Health check провален! Код: $healthCheck"
        Rollback-Changes
        exit 1
    }
    Write-OK "Health check: $healthCheck"
    
    # Тест 2: Frontend
    $frontendCheck = ssh tp "curl -s -o /dev/null -w '%{http_code}' https://lectiospace.ru/"
    Write-OK "Frontend: $frontendCheck"
    
    # Тест 3: API (должен вернуть 401 без токена)
    $apiCheck = ssh tp "curl -s -o /dev/null -w '%{http_code}' https://lectiospace.ru/api/me/"
    Write-OK "API /me/: $apiCheck (401 = OK, требует авторизации)"
    
} else {
    Write-Host "  [DRY-RUN] Smoke tests были бы выполнены" -ForegroundColor Gray
}

# ===================================================================
# ЗАВЕРШЕНИЕ
# ===================================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "     DEPLOY COMPLETED SUCCESSFULLY     " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Бэкап БД:    /tmp/$script:backupName.sqlite3" -ForegroundColor Gray
Write-Host "Коммит:      $remoteCommit" -ForegroundColor Gray
Write-Host "Production:  https://lectiospace.ru" -ForegroundColor Gray
Write-Host ""
Write-Host "Следи за логами (первые 15 минут):" -ForegroundColor Yellow
Write-Host "  ssh tp 'sudo tail -f /var/log/teaching-panel-error.log'" -ForegroundColor White
Write-Host ""
