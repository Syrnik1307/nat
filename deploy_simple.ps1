# ПРОСТОЙ ДЕПЛОЙ БЕЗ LOCALHOST
# Твой ноутбук используется только для git push!

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('staging', 'production')]
    [string]$Target = 'staging'
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploy to $Target" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 1. Проверка - закоммичены ли изменения
Write-Host "📋 Checking git status..." -ForegroundColor Yellow
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "⚠️ You have uncommitted changes:" -ForegroundColor Yellow
    git status --short
    $commit = Read-Host "`nCommit them now? (yes/no)"
    if ($commit -eq 'yes') {
        $message = Read-Host "Commit message"
        git add .
        git commit -m $message
    } else {
        Write-Host "❌ Commit your changes first!" -ForegroundColor Red
        exit 1
    }
}

# 2. Push to git
if ($Target -eq 'staging') {
    $branch = 'staging'
    $domain = 'lectiospace.online'
    $port = '8001'
    $service = 'teaching-panel-staging'
    $path = '/var/www/teaching-panel-staging'
} else {
    $branch = 'main'
    $domain = 'lectiospace.ru'
    $port = '8000'
    $service = 'teaching-panel'
    $path = '/var/www/teaching-panel'
}

Write-Host "📤 Pushing to git ($branch)..." -ForegroundColor Yellow
git push origin $branch

# 3. Deploy на сервере (ВСЁ происходит на сервере, не на ноутбуке!)
Write-Host ""
Write-Host "🖥️ Deploying on server..." -ForegroundColor Green
Write-Host "Domain: $domain" -ForegroundColor Gray
Write-Host "Branch: $branch" -ForegroundColor Gray
Write-Host ""

# SSH команда - весь деплой на сервере
ssh root@lectiospace.ru @"
    set -e
    echo '========================================='
    echo '🚀 Deploying $Target on server'
    echo '========================================='
    
    # 1. Pull latest code
    echo '📥 Pulling latest code...'
    cd $path
    git fetch origin
    git checkout $branch
    git pull origin $branch
    
    # 2. Backend updates
    echo '🐍 Updating backend...'
    source venv/bin/activate
    pip install -r requirements.txt --quiet
    
    # 3. Migrations
    echo '🗄️ Running migrations...'
    cd teaching_panel
    python manage.py migrate --noinput
    
    # 4. Static files
    echo '📦 Collecting static...'
    python manage.py collectstatic --noinput
    
    # 5. Restart backend
    echo '🔄 Restarting backend service...'
    cd ..
    sudo systemctl restart $service
    sleep 2
    
    # 6. Build frontend НА СЕРВЕРЕ (не на ноутбуке!)
    echo '⚛️ Building frontend on server...'
    cd frontend
    
    # Устанавливаем Node.js если нет
    if ! command -v node &> /dev/null; then
        echo 'Installing Node.js...'
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    
    # Устанавливаем зависимости только если нет node_modules
    if [ ! -d 'node_modules' ]; then
        echo 'Installing npm dependencies...'
        npm ci
    fi
    
    # Build
    echo 'Building React app...'
    if [ '$Target' = 'staging' ]; then
        export REACT_APP_ENV=staging
    else
        export REACT_APP_ENV=production_russia
    fi
    npm run build
    
    # 7. Check status
    echo ''
    echo '✅ Deployment completed!'
    echo '========================================='
    echo 'Service status:'
    sudo systemctl status $service --no-pager -l | head -10
    echo ''
    echo '🌐 Check: https://$domain'
    echo '📝 Logs: tail -f $path/logs/error.log'
"@

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ DEPLOY SUCCESS!" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Green
    Write-Host "🌐 URL: https://$domain" -ForegroundColor Cyan
    Write-Host "📊 Health: https://$domain/api/health/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📝 View logs: ssh root@lectiospace.ru 'tail -f $path/logs/error.log'" -ForegroundColor Gray
    
    # Открыть сайт в браузере
    $open = Read-Host "`nOpen in browser? (yes/no)"
    if ($open -eq 'yes') {
        Start-Process "https://$domain"
    }
} else {
    Write-Host ""
    Write-Host "❌ DEPLOY FAILED!" -ForegroundColor Red
    Write-Host "Check logs: ssh root@lectiospace.ru 'tail -100 $path/logs/error.log'" -ForegroundColor Yellow
    exit 1
}
