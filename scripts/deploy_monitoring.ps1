# ============================================================
# Быстрая синхронизация ВСЕЙ мониторинг-системы на prod
# ============================================================
# Использование: .\scripts\deploy_monitoring.ps1
# Что делает:
#   1. Копирует guardian.sh + install скрипт на prod
#   2. Устанавливает guardian (cron, config, known good)
#   3. Запускает guardian один раз для проверки
#   4. Показывает статус
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  DEPLOYING MONITORING SYSTEM              " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Копируем файлы
Write-Host "[1/4] Копирование файлов..." -ForegroundColor Yellow

$filesToCopy = @(
    "scripts/monitoring/guardian.sh"
    "scripts/monitoring/install_guardian.sh"
)

foreach ($f in $filesToCopy) {
    $local = Join-Path $PSScriptRoot ".." $f
    if (-not (Test-Path $local)) {
        $local = Join-Path (Get-Location) $f
    }
    
    $remotePath = "/opt/lectio-monitor/$(Split-Path $f -Leaf)"
    Write-Host "  $f -> $remotePath" -ForegroundColor Gray
    scp $f "tp:$remotePath"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAIL: не удалось скопировать $f" -ForegroundColor Red
        exit 1
    }
}

ssh tp "sudo chmod +x /opt/lectio-monitor/*.sh"
Write-Host "  OK" -ForegroundColor Green

# 2. Установка
Write-Host ""
Write-Host "[2/4] Установка guardian..." -ForegroundColor Yellow
$installOutput = ssh tp "sudo bash /opt/lectio-monitor/install_guardian.sh 2>&1"
$installOutput | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

# 3. Тестовый запуск
Write-Host ""
Write-Host "[3/4] Тестовый запуск guardian..." -ForegroundColor Yellow
ssh tp "sudo /opt/lectio-monitor/guardian.sh 2>&1" | Out-Null
$lastLog = ssh tp "tail -5 /var/log/lectio-monitor/guardian.log 2>/dev/null"
$lastLog | ForEach-Object {
    if ($_ -match "OK:") {
        Write-Host "  $_" -ForegroundColor Green
    } elseif ($_ -match "RECOVERY|PROBLEMS") {
        Write-Host "  $_" -ForegroundColor Red
    } else {
        Write-Host "  $_" -ForegroundColor Gray
    }
}

# 4. Статус
Write-Host ""
Write-Host "[4/4] Текущий статус..." -ForegroundColor Yellow

$knownGood = ssh tp "cat /var/run/lectio-monitor/last_known_good 2>/dev/null || echo 'NOT SET'"
$cronCheck = ssh tp "crontab -l 2>/dev/null | grep -c guardian.sh || echo 0"
$currentCommit = ssh tp "cd /var/www/teaching_panel && git rev-parse --short HEAD"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  MONITORING DEPLOYED                      " -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Guardian:      /opt/lectio-monitor/guardian.sh" -ForegroundColor White
Write-Host "  Cron entries:  $cronCheck" -ForegroundColor White
Write-Host "  Known good:    $knownGood" -ForegroundColor White
Write-Host "  Current:       $currentCommit" -ForegroundColor White
Write-Host ""
Write-Host "  Лог:    ssh tp 'tail -f /var/log/lectio-monitor/guardian.log'" -ForegroundColor Gray
Write-Host "  Пауза:  ssh tp 'sudo touch /var/run/lectio-monitor/maintenance_mode'" -ForegroundColor Gray
Write-Host "  Резюме: ssh tp 'sudo rm /var/run/lectio-monitor/maintenance_mode'" -ForegroundColor Gray
Write-Host ""
