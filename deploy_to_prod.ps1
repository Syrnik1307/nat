#+#+#+#+#+#+#+#+#+#+#+#+###############################################
# Teaching Panel Production Deployment Script
# Запуск: .\deploy_to_prod.ps1
#
# Цель: воспроизводимый деплой (бек + фронт) без "грязного" git-дерева
# на сервере.
#
# На практике `npm ci` может падать из-за lockfile/peer-deps нюансов.
# Поэтому используем `npm install` для сборки фронта, но обязательно
# откатываем tracked `frontend/package-lock.json` обратно, чтобы
# последующие `git pull/reset` всегда работали с первого раза.
########################################################################

param(
    [string]$SSHAlias = "tp",
    [string]$GitBranch = "main",
    [switch]$SkipFrontend = $false,
    [switch]$SkipMigrations = $false
)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Teaching Panel Production Deployment" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$remoteScript = @'
set -e
set -u
set -o pipefail

echo 'Updating code from Git (force sync)...'
cd /var/www/teaching_panel

# Важно: npm иногда модифицирует tracked package-lock.json.
# Чтобы git pull всегда был предсказуемым — принудительно синхронизируемся с origin.
sudo -u www-data git fetch origin
sudo -u www-data git reset --hard origin/__BRANCH__

# Удаляем известные артефакты, которые не должны жить в репозитории
sudo rm -rf frontend_build || true

echo 'Installing backend dependencies...'
cd teaching_panel
source ../venv/bin/activate
pip install -r requirements.txt --quiet

__MIGRATIONS_BLOCK__

echo 'Collecting static files...'
python manage.py collectstatic --noinput

__FRONTEND_BLOCK__

echo 'Restarting services...'
sudo systemctl restart teaching_panel nginx redis-server celery celery-beat || true

echo 'Deployment completed.'
sleep 2
sudo systemctl status teaching_panel --no-pager || true
echo ''
echo 'Recent logs:'
sudo journalctl -u teaching_panel -n 15 --no-pager || true

echo ''
echo 'Frontend index timestamp:'
ls -la /var/www/teaching_panel/frontend/build/index.html || true
'@

$remoteScript = $remoteScript.Replace('__BRANCH__', $GitBranch)

if ($SkipMigrations) {
    $remoteScript = $remoteScript.Replace('__MIGRATIONS_BLOCK__', "echo 'Skipping migrations'\n")
} else {
    $remoteScript = $remoteScript.Replace('__MIGRATIONS_BLOCK__', @"
echo 'Running database migrations...'
python manage.py migrate
"@)
}

if ($SkipFrontend) {
    $remoteScript = $remoteScript.Replace('__FRONTEND_BLOCK__', "echo 'Skipping frontend build'\n")
} else {
    $remoteScript = $remoteScript.Replace('__FRONTEND_BLOCK__', @'
echo 'Building frontend (npm install + restore lock)...'
cd ../frontend
sudo chown -R www-data:www-data .

build_tmp="build_tmp_$(date +%s)"
build_prev="build_prev_$(date +%s)"

# Важно: npm install может изменить tracked package-lock.json.
# После сборки откатываем lock обратно в состояние git.
sudo -u www-data npm install --quiet --no-audit --no-fund
sudo -u www-data env BUILD_PATH="$build_tmp" npm run build

# Минимизируем окна, когда /frontend/build может быть пустым.
# Собираем в build_tmp_* и делаем быстрый swap директорий.
if [ -d build ]; then
    mv build "$build_prev"
fi
mv "$build_tmp" build
if [ -d "$build_prev" ]; then
    rm -rf "$build_prev" || true
fi

cd ..
sudo -u www-data git checkout -- frontend/package-lock.json || true

cd ../teaching_panel
'@)
}

Write-Host "Running deployment on: $SSHAlias" -ForegroundColor Yellow
Write-Host "Git branch: $GitBranch" -ForegroundColor Yellow
Write-Host "Skipping frontend build: $SkipFrontend" -ForegroundColor Yellow
Write-Host ""

# Execute remote script via stdin (надёжнее, чем длинная строка с ; и quoting)
# Нормализуем CRLF -> LF, иначе bash может увидеть одиночный '\r' как команду.
$remoteScriptLf = $remoteScript.Replace("`r`n", "`n")
$remoteScriptLf | ssh $SSHAlias "bash -s"

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "DEPLOYMENT FINISHED" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
