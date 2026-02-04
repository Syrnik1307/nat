# Deploy для ТРЁХ окружений
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('russia-prod', 'russia-stage', 'africa-prod')]
    [string]$Target
)

$ErrorActionPreference = "Stop"

# Конфигурация окружений
$environments = @{
    'russia-prod' = @{
        Domain = 'lectiospace.ru'
        Branch = 'main'
        Port = '8000'
        Service = 'teaching-panel'
        Path = '/var/www/teaching-panel'
        Description = '🇷🇺 RUSSIA PRODUCTION (БОЕВОЙ!)'
        Color = 'Red'
        Confirm = $true  # требуется подтверждение
    }
    'russia-stage' = @{
        Domain = 'stage.lectiospace.ru'
        Branch = 'staging-russia'
        Port = '8001'
        Service = 'teaching-panel-stage-ru'
        Path = '/var/www/teaching-panel-stage-ru'
        Description = '🧪 RUSSIA STAGING (тестирование)'
        Color = 'Yellow'
        Confirm = $false
    }
    'africa-prod' = @{
        Domain = 'lectiospace.online'
        Branch = 'main-africa'
        Port = '8002'
        Service = 'teaching-panel-africa'
        Path = '/var/www/teaching-panel-africa'
        Description = '🌍 AFRICA PRODUCTION (обкатка фич)'
        Color = 'Green'
        Confirm = $false
    }
}

$env = $environments[$Target]

Write-Host "`n$($env.Description)" -ForegroundColor $env.Color
Write-Host "Domain: $($env.Domain)" -ForegroundColor Gray
Write-Host "Branch: $($env.Branch)" -ForegroundColor Gray
Write-Host "================================================" -ForegroundColor $env.Color

# Подтверждение для прода России
if ($env.Confirm) {
    Write-Host "`n⚠️  WARNING: This is PRODUCTION RUSSIA!" -ForegroundColor Red
    Write-Host "This will affect REAL USERS!" -ForegroundColor Red
    $confirm = Read-Host "`nType 'DEPLOY' to continue"
    if ($confirm -ne 'DEPLOY') {
        Write-Host "❌ Cancelled" -ForegroundColor Red
        exit 0
    }
}

# Проверка git
Write-Host "`n📋 Checking git status..." -ForegroundColor Yellow
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "⚠️ Uncommitted changes found" -ForegroundColor Yellow
    git status --short
    $commit = Read-Host "`nCommit now? (yes/no)"
    if ($commit -eq 'yes') {
        $message = Read-Host "Commit message"
        git add .
        git commit -m $message
    }
}

# Push to git
Write-Host "`n📤 Pushing to $($env.Branch)..." -ForegroundColor Yellow
git checkout $env.Branch
git push origin $env.Branch

# Deploy на сервере
Write-Host "`n🚀 Deploying on server..." -ForegroundColor Green
$sshCommand = @"
    set -e
    echo '========================================='
    echo 'Deploying: $($env.Description)'
    echo 'Domain: $($env.Domain)'
    echo '========================================='
    
    cd $($env.Path)
    
    echo '📥 Pulling latest code...'
    git fetch origin
    git checkout $($env.Branch)
    git pull origin $($env.Branch)
    
    echo '🐍 Updating backend...'
    source venv/bin/activate
    pip install -r requirements.txt --quiet
    
    echo '🗄️ Running migrations...'
    cd teaching_panel
    python manage.py migrate --noinput
    
    echo '📦 Collecting static...'
    python manage.py collectstatic --noinput
    
    echo '🔄 Restarting backend...'
    cd ..
    sudo systemctl restart $($env.Service)
    sleep 3
    
    echo '⚛️ Building frontend...'
    cd frontend
    
    if [ ! -d 'node_modules' ]; then
        echo 'Installing npm dependencies...'
        npm ci
    fi
    
    # Environment-specific build
    if [ '$Target' = 'russia-prod' ]; then
        export REACT_APP_ENV=production_russia
    elif [ '$Target' = 'russia-stage' ]; then
        export REACT_APP_ENV=staging_russia
    else
        export REACT_APP_ENV=production_africa
    fi
    
    npm run build
    
    echo ''
    echo '✅ Deployment completed!'
    echo '========================================='
    echo 'Service status:'
    sudo systemctl status $($env.Service) --no-pager | head -10
    echo ''
    echo 'Recent logs (last 10 lines):'
    sudo tail -10 $($env.Path)/logs/error.log
"@

ssh nat@lectiospace.ru $sshCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ DEPLOY SUCCESS!" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Green
    Write-Host "🌐 URL: https://$($env.Domain)" -ForegroundColor Cyan
    Write-Host "📊 Health: https://$($env.Domain)/api/health/" -ForegroundColor Cyan
    Write-Host "`n📝 View logs:" -ForegroundColor Gray
    Write-Host "   ssh nat@lectiospace.ru 'tail -f $($env.Path)/logs/error.log'" -ForegroundColor Gray
    
    $open = Read-Host "`nOpen in browser? (yes/no)"
    if ($open -eq 'yes') {
        Start-Process "https://$($env.Domain)"
    }
} else {
    Write-Host "`n❌ DEPLOY FAILED!" -ForegroundColor Red
    Write-Host "Check logs: ssh nat@lectiospace.ru 'tail -100 $($env.Path)/logs/error.log'" -ForegroundColor Yellow
    exit 1
}
