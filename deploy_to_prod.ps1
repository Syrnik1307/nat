# Teaching Panel Production Deployment Script
# Запуск: .\deploy_to_prod.ps1

param(
    [string]$SSHAlias = "tp",
    [string]$GitBranch = "main",
    [switch]$SkipFrontend = $false,
    [switch]$SkipMigrations = $false
)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "🚀 Teaching Panel Production Deployment" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$deployCommands = @(
    "echo '📥 Updating code from Git...'",
    "cd /var/www/teaching_panel && sudo -u www-data git pull origin $GitBranch",
    "",
    "echo '📦 Installing dependencies...'",
    "cd teaching_panel && source ../venv/bin/activate && pip install -r requirements.txt --quiet",
    ""
)

if (-not $SkipMigrations) {
    $deployCommands += @(
        "echo '🗄️  Running database migrations...'",
        "python manage.py migrate",
        ""
    )
}

$deployCommands += @(
    "echo '📂 Collecting static files...'",
    "python manage.py collectstatic --noinput",
    ""
)

if (-not $SkipFrontend) {
    $deployCommands += @(
        "echo '🎨 Building frontend...'",
        "cd ../frontend && sudo chown -R www-data:www-data . && sudo -u www-data npm install --quiet && sudo -u www-data npm run build && cd ../teaching_panel",
        ""
    )
}

$deployCommands += @(
    "echo '🔄 Restarting services...'",
    "sudo systemctl restart teaching_panel nginx redis-server celery celery-beat || true",
    "",
    "echo '✅ Deployment completed!'",
    "sleep 3",
    "sudo systemctl status teaching_panel --no-pager",
    "echo ''",
    "echo '📊 Recent logs:'",
    "sudo journalctl -u teaching_panel -n 10"
)

$script = ($deployCommands | Where-Object { $_ -and $_.Trim() -ne "" }) -join "; "

Write-Host "📋 Running deployment on: $SSHAlias" -ForegroundColor Yellow
Write-Host "🌿 Git branch: $GitBranch" -ForegroundColor Yellow
Write-Host "⏭️  Skipping frontend build: $SkipFrontend" -ForegroundColor Yellow
Write-Host ""

# Execute remote commands
ssh $SSHAlias $script

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "✅ DEPLOYMENT FINISHED!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
