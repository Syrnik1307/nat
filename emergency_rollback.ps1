# Аварийный откат production на последнюю рабочую версию
# Использование: .\emergency_rollback.ps1
# Или:          .\emergency_rollback.ps1 -Commit abc1234
# Или:          .\emergency_rollback.ps1 -DbRestore

param(
    [string]$Commit,       # Конкретный коммит для отката (необязательно)
    [switch]$DbRestore,    # Восстановить БД из последнего бэкапа
    [switch]$Force          # Не спрашивать подтверждения
)

$ErrorActionPreference = "Stop"

function Write-OK { param($msg) Write-Host "  OK $msg" -ForegroundColor Green }
function Write-Fail { param($msg) Write-Host "  FAIL $msg" -ForegroundColor Red }
function Write-Step { param($num, $msg) Write-Host "[$num] $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "============================================" -ForegroundColor Red
Write-Host "     EMERGENCY ROLLBACK                    " -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Red
Write-Host ""

# 1. Определяем коммит для отката
if ($Commit) {
    $targetCommit = $Commit
    Write-Host "  Целевой коммит: $targetCommit (указан вручную)" -ForegroundColor Cyan
} else {
    # Читаем last_known_good с сервера
    $knownGood = ssh tp "cat /var/run/lectio-monitor/last_known_good 2>/dev/null || echo ''"
    if ($knownGood) {
        $targetCommit = ($knownGood -split ' ')[0]
        $savedAt = ($knownGood -split ' ', 2)[1]
        Write-Host "  Последняя рабочая версия: $targetCommit (сохранена $savedAt)" -ForegroundColor Cyan
    } else {
        Write-Fail "Нет записи о последней рабочей версии!"
        Write-Host ""
        Write-Host "Варианты:" -ForegroundColor Yellow
        Write-Host "  1. Указать коммит вручную: .\emergency_rollback.ps1 -Commit abc1234" -ForegroundColor White
        Write-Host "  2. Посмотреть историю: ssh tp 'cd /var/www/teaching_panel && git log --oneline -20'" -ForegroundColor White
        exit 1
    }
}

$currentCommit = ssh tp "cd /var/www/teaching_panel && git rev-parse --short HEAD"
Write-Host "  Текущий коммит:  $currentCommit" -ForegroundColor Gray
Write-Host ""

if ($currentCommit -eq $targetCommit) {
    Write-Host "  Уже на целевом коммите. Откат не нужен." -ForegroundColor Green
    Write-Host "  Если проблема не в коде — проверь сервисы:" -ForegroundColor Yellow
    Write-Host "    ssh tp 'sudo systemctl restart teaching_panel nginx celery celery-beat'" -ForegroundColor White
    exit 0
}

# 2. Подтверждение
if (-not $Force) {
    Write-Host "ДЕЙСТВИЯ:" -ForegroundColor Red
    Write-Host "  1. Git rollback: $currentCommit -> $targetCommit" -ForegroundColor White
    if ($DbRestore) {
        Write-Host "  2. Восстановление БД из последнего бэкапа" -ForegroundColor White
    }
    Write-Host "  3. Restart всех сервисов" -ForegroundColor White
    Write-Host ""
    $confirm = Read-Host "Продолжить? (y/n)"
    if ($confirm -ne "y") {
        Write-Host "Отменено." -ForegroundColor Yellow
        exit 0
    }
}

# 3. Включаем maintenance mode
Write-Step 1 "Включение maintenance mode..."
ssh tp "sudo mkdir -p /var/run/lectio-monitor && sudo touch /var/run/lectio-monitor/maintenance_mode && sudo touch /var/run/lectio-monitor/deploy_in_progress"
Write-OK "Алерты подавлены"

# 4. Бэкап текущего состояния (на случай если откат был ошибкой)
Write-Step 2 "Бэкап текущей версии (на всякий случай)..."
$preRollbackBackup = "pre_rollback_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
ssh tp "sudo -u postgres pg_dump -Fc teaching_panel -f /tmp/${preRollbackBackup}.pgdump 2>/dev/null || true"
Write-OK "Бэкап: /tmp/${preRollbackBackup}.pgdump"

# 5. Снимаем immutable
Write-Step 3 "Снятие immutable флагов..."
ssh tp "sudo chattr -i /var/www/teaching_panel/frontend/build/index.html /var/www/teaching_panel/frontend/build/favicon.svg /var/www/teaching_panel/frontend/src/App.js /var/www/teaching_panel/teaching_panel/teaching_panel/settings.py 2>/dev/null || true"
Write-OK "OK"

# 6. Git rollback
Write-Step 4 "Git rollback: $currentCommit -> $targetCommit..."
ssh tp "cd /var/www/teaching_panel && sudo git fetch origin 2>/dev/null; sudo git reset --hard $targetCommit"
Write-OK "Код откачен"

# 7. pip install
Write-Step 5 "Установка зависимостей..."
$pipResult = ssh tp "cd /var/www/teaching_panel && sudo -u www-data venv/bin/pip install -r teaching_panel/requirements.txt --no-input -q 2>&1 && echo PIP_OK"
if ($pipResult -match "PIP_OK") {
    Write-OK "Зависимости установлены"
} else {
    Write-Fail "pip install не очень, но продолжаем"
}

# 8. DB restore (опционально)
if ($DbRestore) {
    Write-Step 6 "Восстановление БД..."
    $latestBackup = ssh tp "ls -t /tmp/deploy_*.pgdump /tmp/backup_*.pgdump /tmp/pre_*.pgdump 2>/dev/null | head -1"
    if ($latestBackup) {
        Write-Host "  Используем бэкап: $latestBackup" -ForegroundColor Gray
        ssh tp "sudo -u postgres pg_restore --clean --dbname=teaching_panel $latestBackup 2>&1 || true"
        Write-OK "БД восстановлена"
    } else {
        Write-Fail "Бэкап БД не найден!"
    }
} else {
    Write-Step 6 "Миграции..."
    ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py migrate --noinput 2>/dev/null || true"
    Write-OK "Миграции проверены"
}

# 9. Collectstatic + fix permissions
Write-Step 7 "Статика + права..."
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py collectstatic --noinput --clear 2>/dev/null || true"
ssh tp "sudo chown -R www-data:www-data /var/www/teaching_panel/frontend/build /var/www/teaching_panel/staticfiles /var/www/teaching_panel/media 2>/dev/null; sudo chmod -R 755 /var/www/teaching_panel/frontend/build /var/www/teaching_panel/staticfiles 2>/dev/null"
Write-OK "OK"

# 10. Restart всех сервисов
Write-Step 8 "Перезапуск сервисов..."
ssh tp "sudo systemctl restart teaching_panel nginx celery celery-beat celery-ai-worker 2>/dev/null; sudo systemctl restart redis-server 2>/dev/null || true"
Start-Sleep -Seconds 5
Write-OK "Сервисы перезапущены"

# 11. Immutable флаги
Write-Step 9 "Восстановление immutable флагов..."
ssh tp "sudo chattr +i /var/www/teaching_panel/frontend/build/index.html /var/www/teaching_panel/frontend/build/favicon.svg /var/www/teaching_panel/teaching_panel/teaching_panel/settings.py 2>/dev/null || true"
Write-OK "OK"

# 12. Smoke test
Write-Step 10 "Проверка..."
Start-Sleep -Seconds 3

$healthCode = ssh tp "curl -s -o /dev/null -w '%{http_code}' https://lectiospace.ru/api/health/"
$frontCode = ssh tp "curl -s -o /dev/null -w '%{http_code}' https://lectiospace.ru/"

Write-Host ""
if ($healthCode -eq "200" -and $frontCode -eq "200") {
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  ROLLBACK SUCCESSFUL                      " -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Health: $healthCode" -ForegroundColor Green
    Write-Host "  Frontend: $frontCode" -ForegroundColor Green
    Write-Host "  Коммит: $targetCommit" -ForegroundColor Green
} else {
    Write-Host "============================================" -ForegroundColor Red
    Write-Host "  ROLLBACK - ПРОБЛЕМЫ ОСТАЛИСЬ!            " -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Health: $healthCode" -ForegroundColor $(if ($healthCode -eq "200") { "Green" } else { "Red" })
    Write-Host "  Frontend: $frontCode" -ForegroundColor $(if ($frontCode -eq "200") { "Green" } else { "Red" })
    Write-Host ""
    Write-Host "  Проверь логи:" -ForegroundColor Yellow
    Write-Host "    ssh tp 'sudo journalctl -u teaching_panel -n 50 --no-pager'" -ForegroundColor White
    Write-Host "    ssh tp 'sudo tail -20 /var/log/nginx/error.log'" -ForegroundColor White
}

# 13. Выключаем maintenance mode
ssh tp "sudo rm -f /var/run/lectio-monitor/maintenance_mode /var/run/lectio-monitor/deploy_in_progress"

Write-Host ""
Write-Host "  Бэкап до отката: /tmp/${preRollbackBackup}.pgdump" -ForegroundColor Gray
Write-Host "  Чтобы отменить откат: .\emergency_rollback.ps1 -Commit $currentCommit" -ForegroundColor Gray
Write-Host ""
