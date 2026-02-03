# ========================================
# Teaching Panel - БЫСТРЫЙ ДЕПЛОЙ
# ========================================
# Оптимизированный скрипт с пропуском лишних шагов
# ========================================

param(
    [string]$SSHAlias = "tp",
    [switch]$FrontendOnly = $false,
    [switch]$BackendOnly = $false,
    [switch]$SkipDeps = $false  # Пропустить npm install/pip install
)

$ErrorActionPreference = "Stop"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  БЫСТРЫЙ ДЕПЛОЙ Teaching Panel" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Определяем что деплоить
$deployFrontend = -not $BackendOnly
$deployBackend = -not $FrontendOnly

if ($deployFrontend -and $deployBackend) {
    Write-Host "Режим: ПОЛНЫЙ ДЕПЛОЙ" -ForegroundColor Yellow
} elseif ($deployFrontend) {
    Write-Host "Режим: ТОЛЬКО ФРОНТЕНД" -ForegroundColor Yellow
} elseif ($deployBackend) {
    Write-Host "Режим: ТОЛЬКО БЭКЕНД" -ForegroundColor Yellow
}

if ($SkipDeps) {
    Write-Host "⚡ TURBO режим: без переустановки зависимостей" -ForegroundColor Magenta
}

Write-Host ""

$remoteScript = @'
set -e
set -u

echo '📥 Git pull...'
cd /var/www/teaching_panel
sudo -u www-data git fetch origin
sudo -u www-data git reset --hard origin/main

__BACKEND_BLOCK__

__FRONTEND_BLOCK__

echo '🔄 Перезапуск сервисов...'
sudo systemctl restart teaching_panel nginx

echo ''
echo '✅ ГОТОВО!'
sudo systemctl status teaching_panel --no-pager | head -5
'@

# Backend блок
if ($deployBackend) {
    if ($SkipDeps) {
        $backendBlock = @'
echo '🐍 Backend: миграции + статика...'
cd teaching_panel
source ../venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
cd ..
'@
    } else {
        $backendBlock = @'
echo '🐍 Backend: зависимости + миграции + статика...'
cd teaching_panel
source ../venv/bin/activate
pip install -r requirements.txt --quiet
python manage.py migrate --noinput
python manage.py collectstatic --noinput
cd ..
'@
    }
} else {
    $backendBlock = "echo '⏩ Backend пропущен'"
}

# Frontend блок
if ($deployFrontend) {
    if ($SkipDeps) {
        $frontendBlock = @'
echo '⚛️ Frontend: только build...'
cd frontend
sudo chown -R www-data:www-data .
sudo -u www-data npm run build
cd ..
'@
    } else {
        $frontendBlock = @'
echo '⚛️ Frontend: зависимости + build...'
cd frontend
sudo chown -R www-data:www-data .

# Проверяем изменения в package-lock.json
LOCK_CHANGED=$(git diff HEAD@{1} HEAD -- package-lock.json | wc -l)

if [ "$LOCK_CHANGED" -gt 0 ]; then
    echo '  📦 package-lock изменился, npm ci...'
    sudo -u www-data npm ci --quiet --no-audit
else
    echo '  ⚡ package-lock не менялся, пропускаем npm ci'
fi

sudo -u www-data npm run build
cd ..
'@
    }
} else {
    $frontendBlock = "echo '⏩ Frontend пропущен'"
}

$remoteScript = $remoteScript.Replace('__BACKEND_BLOCK__', $backendBlock)
$remoteScript = $remoteScript.Replace('__FRONTEND_BLOCK__', $frontendBlock)

# Нормализация переносов строк для bash
$remoteScriptLf = $remoteScript.Replace("`r`n", "`n")

Write-Host "🚀 Запуск деплоя..." -ForegroundColor Cyan
Write-Host ""

try {
    $remoteScriptLf | ssh $SSHAlias "bash -s"
    
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "  ✅ ДЕПЛОЙ ЗАВЕРШЁН" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Сайт: https://lectiospace.ru" -ForegroundColor Cyan
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "  ❌ ОШИБКА ДЕПЛОЯ" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
